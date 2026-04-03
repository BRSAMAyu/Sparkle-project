"""
InterventionEventConsumer - delivers InterventionRecords to user-facing channels.

Breakpoint 4 goal:
  behavior/plan signals should not stop at record creation. They need a minimal
  delivery pipeline that renders low-defense intervention content, sends it via
  the chosen channel, and only then marks the record as delivered.
"""
from __future__ import annotations

import asyncio
import hashlib
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from app.core.metrics import (
    INTERVENTION_DELIVERY_TOTAL,
    INTERVENTION_PARAMETER_COMPILATION_TOTAL,
    INTERVENTION_PUSH_HISTORY_TOTAL,
)
from app.core.event_bus import EventBus
from app.db.session import AsyncSessionLocal
from app.models.card_protocol import (
    Card,
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionRecord,
    InterventionTriggerType,
)
from app.models.notification import PushHistory
from app.models.user import PushPreference
from app.schemas.notification import NotificationCreate
from app.services.intervention_record_service import InterventionRecordService
from app.services.notification_service import NotificationService
from app.services.plan_adjustment_applier import PlanAdjustmentApplier
from app.services.card_protocol.parameter_compiler import ParameterCompiler
from app.services.template_registry import TemplateRegistry
from app.services.template_service import TemplateService


_INTENT_BY_TRIGGER: dict[InterventionTriggerType, str] = {
    InterventionTriggerType.PLAN_RISK: "plan_path_soft_replan",
    InterventionTriggerType.CONCEPT_GAP: "concept_gap_focus",
    InterventionTriggerType.STALL_PATTERN: "micro_restart",
    InterventionTriggerType.OVERLOAD: "overload_lighten_path",
    InterventionTriggerType.MISALIGNMENT: "recover_self_efficacy",
}


class InterventionEventConsumer:
    """Consumes intervention_record.created and performs actual delivery."""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "intervention_event_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False
        self._template_service = TemplateService(TemplateRegistry())

    async def start(self):
        await self.event_bus.connect()
        self._running = True
        logger.info("InterventionEventConsumer started")

        while self._running:
            try:
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"intervention-{id(self)}",
                    callback=self._handle_event,
                )
                break
            except Exception as exc:
                logger.error(f"InterventionEventConsumer error: {exc}")
                await asyncio.sleep(1)

    async def stop(self):
        self._running = False

    async def _handle_event(self, event: dict):
        if event.get("event_type") != "intervention_record.created":
            return
        await self._handle_record_created(event)

    async def _handle_record_created(self, event: dict):
        record_id = event.get("record_id")
        if not record_id:
            return

        try:
            async with AsyncSessionLocal() as db:
                record = await db.get(InterventionRecord, UUID(str(record_id)))
                if not record:
                    return
                if record.acceptance_status != InterventionAcceptanceStatus.CREATED:
                    return

                delivery_result = await self._deliver_record(db, record)
                if not delivery_result.get("delivered"):
                    await db.rollback()
                    return

                parameter_result = await self._apply_parameter_strategy(db, record)
                record.action_payload = {
                    **(record.action_payload or {}),
                    "delivery_metrics": delivery_result,
                    "parameter_compilation": parameter_result,
                }
                await db.flush()

                record_service = InterventionRecordService(db, self.event_bus)
                await record_service.mark_delivered(record.id)
                await db.commit()
        except Exception as exc:
            logger.error(f"InterventionEventConsumer failed: {exc}")

    async def _deliver_record(self, db, record: InterventionRecord) -> dict[str, Any]:
        intent_type = _INTENT_BY_TRIGGER.get(record.trigger_type, "recover_self_efficacy")
        support_level = self._support_level_for(record.delivery_strategy, intent_type)
        template = await self._template_service.select_variant(
            intent_type=intent_type,
            support_level=support_level,
            user_id=str(record.user_id),
            preferred_tone=record.delivery_strategy.value,
        )
        variables = self._build_variables(record)
        context_ids = await self._resolve_context_ids(db, record)
        rendered_message = self._template_service.render(template, variables)
        title = self._build_title(record.trigger_type, record.delivery_strategy)

        payload = {
            "record_id": str(record.id),
            "intervention_id": str(record.id),
            "intent_type": intent_type,
            "template_id": template.template_id,
            "template_variant_id": template.variant_id,
            "template_tone": template.tone or record.delivery_strategy.value,
            "delivery_channel": record.delivery_channel.value,
            "delivery_strategy": record.delivery_strategy.value,
            "context_variables": variables,
            "rendered_message": rendered_message,
            **context_ids,
        }

        record.action_payload = {
            **(record.action_payload or {}),
            **payload,
        }

        if record.delivery_channel == DeliveryChannel.PUSH:
            return await self._deliver_push(db, record, title, rendered_message, payload)

        return await self._deliver_notification(db, record, title, rendered_message, payload)

    async def _deliver_notification(
        self,
        db,
        record: InterventionRecord,
        title: str,
        body: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        should_push, suppression_reason = await NotificationService._should_push_notification(
            db,
            user_id=record.user_id,
        )
        notif = NotificationCreate(
            title=title,
            content=body,
            type="intervention",
            data=payload,
        )
        created = await NotificationService.create(
            db,
            record.user_id,
            notif,
            push_via_websocket=True,
        )
        result = {
            "delivered": True,
            "notification_id": str(created.id),
            "channel": record.delivery_channel.value,
            "result": "suppressed" if not should_push else "success",
            "suppressed_reason": suppression_reason,
            "push_history_recorded": False,
        }
        INTERVENTION_DELIVERY_TOTAL.labels(
            channel=record.delivery_channel.value.lower(),
            result=result["result"],
        ).inc()
        return result

    async def _deliver_push(
        self,
        db,
        record: InterventionRecord,
        title: str,
        body: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        should_push, suppression_reason = await NotificationService._should_push_notification(
            db,
            user_id=record.user_id,
        )
        notif = NotificationCreate(
            title=title,
            content=body,
            type="intervention_push",
            data=payload,
        )
        created = await NotificationService.create(
            db,
            record.user_id,
            notif,
            push_via_websocket=True,
        )

        content_hash = hashlib.md5(f"{title}:{body}".encode("utf-8")).hexdigest()
        db.add(
            PushHistory(
                user_id=record.user_id,
                trigger_type="behavior_intervention",
                content_hash=content_hash,
                status="sent",
            )
        )
        INTERVENTION_PUSH_HISTORY_TOTAL.labels(status="recorded").inc()

        pref_result = await db.execute(
            select(PushPreference).where(PushPreference.user_id == record.user_id)
        )
        prefs = pref_result.scalar_one_or_none()
        if prefs:
            from datetime import datetime, timezone

            prefs.last_push_time = datetime.now(timezone.utc)
        result = {
            "delivered": True,
            "notification_id": str(created.id),
            "channel": record.delivery_channel.value,
            "result": "suppressed" if not should_push else "success",
            "suppressed_reason": suppression_reason,
            "push_history_recorded": True,
        }
        INTERVENTION_DELIVERY_TOTAL.labels(
            channel=record.delivery_channel.value.lower(),
            result=result["result"],
        ).inc()
        return result

    async def _resolve_context_ids(
        self,
        db,
        record: InterventionRecord,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if record.plan_card_id:
            payload["plan_card_id"] = str(record.plan_card_id)
            plan_card = await db.get(Card, record.plan_card_id)
            if plan_card and plan_card.metadata_:
                legacy_plan_id = plan_card.metadata_.get("legacy_plan_id")
                if legacy_plan_id:
                    payload["plan_id"] = str(legacy_plan_id)
                    payload["entity_id"] = str(legacy_plan_id)
                    payload["destination_route"] = f"/plans/{legacy_plan_id}"
                    payload["deep_link"] = f"sparkle://plan/{legacy_plan_id}"
        if record.phase_card_id:
            payload["phase_card_id"] = str(record.phase_card_id)
        if record.knowledge_card_id:
            payload["knowledge_card_id"] = str(record.knowledge_card_id)
        if "destination_route" not in payload:
            if record.task_occurrence_id:
                payload["entity_id"] = str(record.task_occurrence_id)
                payload["destination_route"] = (
                    f"/tasks/{record.task_occurrence_id}/execute"
                    f"?origin=notification&intervention_id={record.id}"
                )
                payload["deep_link"] = f"sparkle://task/{record.task_occurrence_id}"
            elif record.delivery_channel == DeliveryChannel.FOCUS_MODE:
                payload["destination_route"] = f"/focus?intervention_id={record.id}"
            else:
                payload["destination_route"] = f"/notification-center?intervention_id={record.id}"
        return payload

    async def _apply_parameter_strategy(
        self,
        db,
        record: InterventionRecord,
    ) -> dict[str, Any]:
        if not record.plan_card_id:
            INTERVENTION_PARAMETER_COMPILATION_TOTAL.labels(result="skipped_no_plan").inc()
            return {"applied": False, "result": "skipped_no_plan"}

        plan_card = await db.get(Card, record.plan_card_id)
        if not plan_card or not plan_card.metadata_:
            INTERVENTION_PARAMETER_COMPILATION_TOTAL.labels(result="skipped_no_plan").inc()
            return {"applied": False, "result": "skipped_no_plan"}

        legacy_plan_id = plan_card.metadata_.get("legacy_plan_id")
        if not legacy_plan_id:
            INTERVENTION_PARAMETER_COMPILATION_TOTAL.labels(result="skipped_no_plan").inc()
            return {"applied": False, "result": "skipped_no_plan"}

        compiler = ParameterCompiler(db, self.event_bus)
        context = self._build_compilation_context(record)
        if not await compiler.can_compile(record.plan_card_id):
            INTERVENTION_PARAMETER_COMPILATION_TOTAL.labels(result="skipped_no_artifacts").inc()
            return {
                "applied": False,
                "result": "skipped_no_artifacts",
                "plan_id": str(legacy_plan_id),
            }

        try:
            plan_id = UUID(str(legacy_plan_id))
            compilation = await compiler.compile(
                user_id=record.user_id,
                plan_card_id=record.plan_card_id,
                plan_id=plan_id,
                trigger=self._compiler_trigger_for(record),
                context=context,
            )
            if not compilation.success:
                INTERVENTION_PARAMETER_COMPILATION_TOTAL.labels(result="failed").inc()
                return {
                    "applied": False,
                    "result": "failed",
                    "error": compilation.error,
                    "plan_id": str(plan_id),
                }

            patcher = PlanAdjustmentApplier(db)
            patch_result = await patcher.apply_incremental_changes(
                user_id=record.user_id,
                plan_id=plan_id,
                trigger=f"intervention:{record.trigger_type.value.lower()}",
            )
            result_label = "patched" if patch_result.applied and (
                patch_result.affected_task_ids
                or patch_result.inserted_task_ids
                or patch_result.hidden_task_ids
            ) else "compiled_only"
            INTERVENTION_PARAMETER_COMPILATION_TOTAL.labels(result=result_label).inc()
            return {
                "applied": True,
                "result": result_label,
                "plan_id": str(plan_id),
                "adaptive_adjustments": compilation.adaptive_adjustments,
                "compilation_meta": compilation.compilation_meta,
                "decision_log_entry_id": compilation.decision_log_entry_id,
                "task_patch_summary": patch_result.patch_summary,
                "affected_task_count": len(patch_result.affected_task_ids),
                "inserted_task_count": len(patch_result.inserted_task_ids),
                "hidden_task_count": len(patch_result.hidden_task_ids),
            }
        except Exception as exc:
            logger.warning("Intervention parameter compilation failed (non-fatal): {}", exc)
            INTERVENTION_PARAMETER_COMPILATION_TOTAL.labels(result="failed").inc()
            return {
                "applied": False,
                "result": "failed",
                "error": str(exc),
                "plan_id": str(legacy_plan_id),
            }

    @staticmethod
    def _compiler_trigger_for(record: InterventionRecord) -> str:
        mapping = {
            InterventionTriggerType.STALL_PATTERN: "stall",
            InterventionTriggerType.OVERLOAD: "overload",
            InterventionTriggerType.CONCEPT_GAP: "difficulty_resistance",
            InterventionTriggerType.PLAN_RISK: "plan_risk",
            InterventionTriggerType.MISALIGNMENT: "misalignment",
        }
        return mapping.get(record.trigger_type, "plan_risk")

    @staticmethod
    def _build_compilation_context(record: InterventionRecord) -> dict[str, Any]:
        diagnosis = dict(record.diagnosis_payload or {})
        reasons = list(diagnosis.get("reasons") or [])
        return {
            "pattern_name": diagnosis.get("pattern_name"),
            "health_reasons": reasons,
            "intervention_id": str(record.id),
            "delivery_strategy": record.delivery_strategy.value,
            "trigger_type": record.trigger_type.value,
        }

    @staticmethod
    def _support_level_for(strategy: DeliveryStrategy, intent_type: str) -> int:
        if intent_type in {"concept_gap_focus", "micro_restart", "overload_lighten_path"}:
            return 4
        if strategy == DeliveryStrategy.MICRO_RESTART:
            return 4
        return 3

    @staticmethod
    def _build_title(trigger_type: InterventionTriggerType, strategy: DeliveryStrategy) -> str:
        if trigger_type == InterventionTriggerType.CONCEPT_GAP:
            return "补一个关键概念"
        if trigger_type == InterventionTriggerType.OVERLOAD:
            return "先把节奏放轻一点"
        if strategy == DeliveryStrategy.MICRO_RESTART:
            return "先从很小的一步开始"
        if trigger_type == InterventionTriggerType.PLAN_RISK:
            return "把接下来几步排顺一点"
        return "把这一步走稳"

    @staticmethod
    def _build_variables(record: InterventionRecord) -> dict[str, Any]:
        diagnosis = dict(record.diagnosis_payload or {})
        context = dict(diagnosis.get("context") or {})
        reasons = list(diagnosis.get("reasons") or [])
        solution_text = str(diagnosis.get("solution_text") or "").strip()
        weak_concept = (
            diagnosis.get("weak_concept")
            or context.get("weak_concept")
            or diagnosis.get("pattern_name")
            or "这个小概念"
        )

        return {
            "concept_a": diagnosis.get("concept_a") or weak_concept,
            "concept_b": diagnosis.get("concept_b") or context.get("concept_b") or "相关概念",
            "weak_concept": weak_concept,
            "estimated_minutes": diagnosis.get("estimated_minutes") or context.get("estimated_minutes") or 10,
            "suggested_step": solution_text or context.get("suggested_step") or "先做 5 分钟的最小入口",
            "completed_count": context.get("completed_count") or diagnosis.get("completed_count") or 0,
            "reason_summary": " / ".join(reasons[:2]) if reasons else "",
        }
