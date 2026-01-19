from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_service
from app.models.intervention import (
    InterventionRequest,
    InterventionAuditLog,
    InterventionFeedback,
    UserInterventionSettings,
)
from app.schemas.intervention import (
    InterventionLevel,
    InterventionRequestCreate,
    InterventionFeedbackType,
)
from app.scaffolding.intent_generator import IntentGenerator
from app.scaffolding.scaffolding_fsm import ScaffoldingFSM
from app.services.template_registry import TemplateRegistry
from app.services.template_service import TemplateService
from app.learning.prompt_bandit import PromptBandit


_NON_SILENT_LEVELS = {
    InterventionLevel.TOAST.value,
    InterventionLevel.CARD.value,
    InterventionLevel.FULL_SCREEN_MODAL.value,
}


@dataclass
class GuardrailDecision:
    action: str
    final_level: str
    reasons: List[str]


@dataclass
class DeliveryResult:
    delivered: bool
    method: str
    error: Optional[str] = None


class InterventionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_settings(self, user_id: UUID, timezone_name: Optional[str]) -> UserInterventionSettings:
        result = await self.db.execute(
            select(UserInterventionSettings).where(UserInterventionSettings.user_id == user_id)
        )
        settings_row = result.scalar_one_or_none()
        if settings_row:
            return settings_row

        quiet_hours = {
            "start": settings.INTERVENTION_QUIET_HOURS_START,
            "end": settings.INTERVENTION_QUIET_HOURS_END,
            "timezone": timezone_name,
        }
        settings_row = UserInterventionSettings(
            user_id=user_id,
            interrupt_threshold=settings.INTERVENTION_DEFAULT_INTERRUPT_THRESHOLD,
            daily_interrupt_budget=settings.INTERVENTION_DEFAULT_DAILY_BUDGET,
            cooldown_minutes=settings.INTERVENTION_DEFAULT_COOLDOWN_MINUTES,
            quiet_hours=quiet_hours,
            topic_allowlist=None,
            topic_blocklist=None,
            do_not_disturb=False,
        )
        self.db.add(settings_row)
        await self.db.commit()
        await self.db.refresh(settings_row)
        return settings_row

    async def update_settings(
        self,
        settings_row: UserInterventionSettings,
        updates: Dict[str, Any],
    ) -> UserInterventionSettings:
        for field, value in updates.items():
            if value is None:
                continue
            setattr(settings_row, field, value)
        await self.db.commit()
        await self.db.refresh(settings_row)
        return settings_row

    def validate_contract(self, payload: InterventionRequestCreate) -> List[str]:
        errors: List[str] = []
        if settings.INTERVENTION_REQUIRE_EVIDENCE and not payload.reason.evidence_refs:
            errors.append("missing_evidence")
        if payload.reason.confidence < settings.INTERVENTION_MIN_CONFIDENCE:
            errors.append("low_confidence")
        if not payload.reason.explanation_text:
            errors.append("missing_explanation")
        if payload.expires_at and payload.expires_at <= datetime.utcnow():
            errors.append("expired_request")
        return errors

    async def create_request(
        self,
        actor_id: UUID,
        actor_is_admin: bool,
        payload: InterventionRequestCreate,
        default_timezone: Optional[str],
    ) -> InterventionRequest:
        target_user_id = payload.user_id or actor_id
        if payload.user_id and payload.user_id != actor_id and not actor_is_admin:
            raise PermissionError("Insufficient privileges to create intervention for other user")

        settings_row = await self.get_or_create_settings(target_user_id, default_timezone)
        errors = self.validate_contract(payload)
        now = datetime.utcnow()

        if errors:
            decision = GuardrailDecision(action="block", final_level=payload.level.value, reasons=errors)
            status = "blocked"
        else:
            decision = await self._evaluate_guardrails(payload, settings_row, now)
            status = "delivered"
            if decision.action == "degrade":
                status = "degraded"
            elif decision.action == "block":
                status = "blocked"

        request = InterventionRequest(
            user_id=target_user_id,
            dedupe_key=payload.dedupe_key,
            topic=payload.topic,
            requested_level=payload.level.value,
            final_level=decision.final_level,
            status=status,
            reason=payload.reason.model_dump(),
            content=payload.content,
            cooldown_policy=payload.cooldown_policy.model_dump() if payload.cooldown_policy else None,
            delivery_method=payload.delivery_method,
            template_id=payload.template_id,
            template_variant_id=payload.template_variant_id,
            scaffolding_level=payload.scaffolding_level,
            intent_type=payload.intent_type,
            schema_version=payload.schema_version,
            policy_version=payload.policy_version,
            model_version=payload.model_version,
            expires_at=payload.expires_at,
            is_retractable=payload.is_retractable,
            supersedes_id=payload.supersedes_id,
        )
        self.db.add(request)
        await self.db.flush()

        audit = InterventionAuditLog(
            request_id=request.id,
            user_id=target_user_id,
            action=decision.action,
            guardrail_result={"reasons": decision.reasons},
            decision_trace=payload.reason.decision_trace,
            evidence_refs=[ref.model_dump() for ref in payload.reason.evidence_refs],
            requested_level=payload.level.value,
            final_level=decision.final_level,
            policy_version=payload.policy_version,
            model_version=payload.model_version,
            schema_version=payload.schema_version,
            occurred_at=now,
        )
        self.db.add(audit)

        if status in ("delivered", "degraded"):
            await self._record_budget_if_needed(target_user_id, decision.final_level, now)

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def list_recent(self, user_id: UUID, limit: int = 20) -> List[InterventionRequest]:
        result = await self.db.execute(
            select(InterventionRequest)
            .where(InterventionRequest.user_id == user_id)
            .order_by(InterventionRequest.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def record_feedback(
        self,
        request: InterventionRequest,
        user_id: UUID,
        feedback_type: InterventionFeedbackType,
        extra_data: Optional[Dict[str, Any]],
    ) -> InterventionFeedback:
        feedback = InterventionFeedback(
            request_id=request.id,
            user_id=user_id,
            feedback_type=feedback_type.value,
            extra_data=self._sanitize_extra_data(extra_data),
        )
        self.db.add(feedback)

        await self._apply_feedback_policy(request, feedback_type)
        await self._apply_scaffolding_feedback(request, user_id, feedback_type, extra_data)
        await self._update_template_bandit(request, feedback_type)

        await self.db.commit()
        await self.db.refresh(feedback)
        return feedback

    async def create_adaptive_intervention(
        self,
        user_id: UUID,
        trigger_event: str,
        urgency: float,
        context: Dict[str, Any],
        edge_state: Optional[Dict[str, Any]] = None,
    ) -> tuple[InterventionRequest, DeliveryResult]:
        fsm = ScaffoldingFSM(self.db)
        scaffolding_state = await fsm.get_state(user_id)
        generator = IntentGenerator()
        intent = generator.generate_intent(
            trigger_event=trigger_event,
            urgency=urgency,
            context=context,
            edge_state=edge_state or {},
            scaffolding_state=fsm.snapshot(scaffolding_state),
        )

        registry = TemplateRegistry()
        bandit = PromptBandit(redis_client=cache_service.redis)
        template_service = TemplateService(registry, bandit)
        selected = await template_service.select_variant(
            intent_type=intent.intent_type,
            support_level=scaffolding_state.support_level,
            user_id=str(user_id),
        )
        rendered_message = template_service.render(selected, intent.context_variables)

        level = self._map_delivery_level(intent.urgency)
        reason = {
            "explanation_text": context.get("explanation") or "triggered intervention",
            "confidence": intent.urgency,
            "evidence_refs": [
                {
                    "type": "edge_state",
                    "id": context.get("edge_state_id", "local"),
                    "schema_version": "edge_state.v1",
                    "user_deleted": False,
                }
            ],
            "decision_trace": [trigger_event],
        }
        payload = InterventionRequestCreate(
            user_id=user_id,
            topic=context.get("topic"),
            reason=reason,
            level=level,
            content={
                "rendered_message": rendered_message,
                "intent_type": intent.intent_type,
                "template_id": selected.template_id,
                "scaffolding_level": scaffolding_state.support_level,
                "context_variables": intent.context_variables,
            },
            context=None,
            schema_version="intervention.v2",
            delivery_method="websocket",
            template_id=selected.template_id,
            template_variant_id=selected.variant_id,
            scaffolding_level=scaffolding_state.support_level,
            intent_type=intent.intent_type,
        )

        request = await self.create_request(
            actor_id=user_id,
            actor_is_admin=False,
            payload=payload,
            default_timezone=None,
        )

        await fsm.register_intervention(
            user_id=user_id,
            intervention_id=request.id,
            intent_type=intent.intent_type,
            template_variant_id=selected.variant_id,
        )

        delivery = await self.deliver_intervention_realtime(user_id, request, rendered_message)
        return request, delivery

    async def deliver_intervention_realtime(
        self,
        user_id: UUID,
        request: InterventionRequest,
        rendered_message: str,
    ) -> DeliveryResult:
        if not settings.INTERNAL_API_KEY or not getattr(settings, "GATEWAY_INTERNAL_URL", ""):
            return DeliveryResult(delivered=False, method="websocket", error="gateway_not_configured")

        payload = {
            "user_id": str(user_id),
            "intervention": {
                "intervention_id": str(request.id),
                "level": (request.final_level or request.requested_level).lower(),
                "content": {
                    "rendered_message": rendered_message,
                    "intent_type": request.intent_type or "",
                    "template_id": request.template_id or "",
                    "scaffolding_level": request.scaffolding_level or 0,
                    "context_variables": request.content.get("context_variables", {})
                    if isinstance(request.content, dict)
                    else {},
                },
                "actions": self._default_actions(request.intent_type),
                "expires_at": int(request.expires_at.timestamp() * 1000) if request.expires_at else 0,
            },
        }

        headers = {"X-Internal-API-Key": settings.INTERNAL_API_KEY}
        url = f"{settings.GATEWAY_INTERNAL_URL.rstrip('/')}/internal/interventions/push"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    return DeliveryResult(delivered=True, method="websocket")
                return DeliveryResult(
                    delivered=False,
                    method="websocket",
                    error=f"gateway_status_{response.status_code}",
                )
        except Exception as exc:
            return DeliveryResult(delivered=False, method="websocket", error=str(exc))

    async def _evaluate_guardrails(
        self,
        payload: InterventionRequestCreate,
        settings_row: UserInterventionSettings,
        now: datetime,
    ) -> GuardrailDecision:
        reasons: List[str] = []
        final_level = payload.level.value

        if settings_row.do_not_disturb:
            return GuardrailDecision(action="block", final_level=final_level, reasons=["do_not_disturb"])

        if payload.topic and settings_row.topic_blocklist and payload.topic in settings_row.topic_blocklist:
            return GuardrailDecision(action="block", final_level=final_level, reasons=["topic_blocked"])

        if payload.topic and await self._is_cooldown_active(payload.topic, settings_row.user_id):
            return GuardrailDecision(action="block", final_level=final_level, reasons=["cooldown_active"])

        if self._is_quiet_hours(now, settings_row.quiet_hours):
            reasons.append("quiet_hours")
            final_level = InterventionLevel.SILENT_MARKER.value

        if payload.context and payload.context.interruptibility is not None:
            if payload.context.interruptibility < settings_row.interrupt_threshold:
                reasons.append("low_interruptibility")
                final_level = InterventionLevel.SILENT_MARKER.value

        if await self._is_budget_exceeded(settings_row.user_id, settings_row.daily_interrupt_budget, now):
            reasons.append("budget_exceeded")
            final_level = InterventionLevel.SILENT_MARKER.value

        action = "deliver"
        if final_level != payload.level.value:
            action = "degrade"

        return GuardrailDecision(action=action, final_level=final_level, reasons=reasons)

    def _is_quiet_hours(self, now: datetime, quiet_hours: Optional[Dict[str, Any]]) -> bool:
        if not quiet_hours:
            return False

        start_str = quiet_hours.get("start")
        end_str = quiet_hours.get("end")
        timezone_name = quiet_hours.get("timezone")
        if not start_str or not end_str:
            return False

        try:
            tz = ZoneInfo(timezone_name) if timezone_name else timezone.utc
        except Exception:
            tz = timezone.utc

        local_time = now.astimezone(tz).time()
        start = self._parse_time(start_str)
        end = self._parse_time(end_str)
        if start is None or end is None:
            return False

        if start <= end:
            return start <= local_time <= end
        return local_time >= start or local_time <= end

    def _parse_time(self, time_str: str) -> Optional[time]:
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except Exception:
            return None

    async def _is_budget_exceeded(self, user_id: UUID, budget: int, now: datetime) -> bool:
        if budget <= 0:
            return True
        key = self._budget_key(user_id, now)
        current = await cache_service.get(key)
        try:
            current_value = int(current) if current is not None else 0
        except (TypeError, ValueError):
            current_value = 0
        return current_value >= budget

    async def _record_budget_if_needed(self, user_id: UUID, final_level: str, now: datetime) -> None:
        if final_level not in _NON_SILENT_LEVELS:
            return
        key = self._budget_key(user_id, now)
        updated = await cache_service.incr(key, 1)
        if updated == 1:
            ttl = self._seconds_until_end_of_day(now)
            await cache_service.expire(key, ttl)

    def _budget_key(self, user_id: UUID, now: datetime) -> str:
        day_key = now.strftime("%Y%m%d")
        return f"intervention:budget:{user_id}:{day_key}"

    def _seconds_until_end_of_day(self, now: datetime) -> int:
        end_of_day = datetime.combine(now.date(), time(23, 59, 59))
        delta = end_of_day - now
        return max(60, int(delta.total_seconds()))

    async def _is_cooldown_active(self, topic: str, user_id: UUID) -> bool:
        global_key = f"intervention:cooldown:{user_id}"
        topic_key = f"intervention:cooldown:{user_id}:{topic}"
        if await cache_service.get(global_key):
            return True
        if await cache_service.get(topic_key):
            return True
        return False

    async def _apply_feedback_policy(
        self,
        request: InterventionRequest,
        feedback_type: InterventionFeedbackType,
    ) -> None:
        if feedback_type not in (InterventionFeedbackType.REJECT, InterventionFeedbackType.MUTE_TOPIC):
            return

        policy = request.cooldown_policy or {}
        until_ms = policy.get("until_ms")
        policy_name = policy.get("policy", "")

        if until_ms:
            until_dt = datetime.utcfromtimestamp(until_ms / 1000.0)
        else:
            until_dt = datetime.utcnow() + timedelta(minutes=settings.INTERVENTION_DEFAULT_COOLDOWN_MINUTES)

        ttl_seconds = max(60, int((until_dt - datetime.utcnow()).total_seconds()))
        if feedback_type == InterventionFeedbackType.MUTE_TOPIC:
            topic_key = f"intervention:cooldown:{request.user_id}:{request.topic or 'global'}"
            await cache_service.set(topic_key, policy_name or "mute_topic", ttl=ttl_seconds)
        else:
            global_key = f"intervention:cooldown:{request.user_id}"
            await cache_service.set(global_key, policy_name or "mute_all", ttl=ttl_seconds)

    async def _apply_scaffolding_feedback(
        self,
        request: InterventionRequest,
        user_id: UUID,
        feedback_type: InterventionFeedbackType,
        extra_data: Optional[Dict[str, Any]],
    ) -> None:
        success_actions = {
            InterventionFeedbackType.ACCEPT,
            InterventionFeedbackType.OPEN_DETAIL,
        }
        success = feedback_type in success_actions
        fsm = ScaffoldingFSM(self.db)
        await fsm.apply_feedback(
            user_id=user_id,
            success=success,
            feedback=feedback_type.value,
            weight=1.0,
        )

    async def _update_template_bandit(
        self,
        request: InterventionRequest,
        feedback_type: InterventionFeedbackType,
    ) -> None:
        if not request.template_variant_id or not request.intent_type or not cache_service.redis:
            return
        reward = 1 if feedback_type in (InterventionFeedbackType.ACCEPT, InterventionFeedbackType.OPEN_DETAIL) else 0
        workflow_id = f"intervention:{request.intent_type}:{request.scaffolding_level or 3}"
        bandit = PromptBandit(redis_client=cache_service.redis)
        await bandit.update(workflow_id, request.template_variant_id, reward)

    def _map_delivery_level(self, urgency: float) -> InterventionLevel:
        if urgency >= 0.7:
            return InterventionLevel.FULL_SCREEN_MODAL
        if urgency >= 0.4:
            return InterventionLevel.CARD
        if urgency >= 0.2:
            return InterventionLevel.TOAST
        return InterventionLevel.SILENT_MARKER

    def _default_actions(self, intent_type: Optional[str]) -> List[Dict[str, str]]:
        if intent_type == "suggest_break":
            return [
                {"id": "start_now", "label": "开始", "type": "primary"},
                {"id": "snooze", "label": "稍后", "type": "secondary"},
            ]
        return [
            {"id": "start_now", "label": "开始", "type": "primary"},
            {"id": "dismiss", "label": "关闭", "type": "secondary"},
        ]

    def _sanitize_extra_data(self, extra_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not extra_data:
            return extra_data
        sanitized: Dict[str, Any] = {}
        for key, value in extra_data.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                sanitized[key] = value
            else:
                sanitized[key] = str(value)
        return sanitized
