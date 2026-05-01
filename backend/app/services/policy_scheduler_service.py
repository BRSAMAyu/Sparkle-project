from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from prometheus_client import Counter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_service
from app.core.event_bus import event_bus
from app.core.metrics import get_or_create_metric
from app.models.accountability_policy import AccountabilityPolicy
from app.models.memory import EpisodicMemory
from app.services.accountability_notification_service import accountability_notification_service
from app.services.aurora_stage24_policy_kill_switch_service import AuroraStage24PolicyKillSwitchService
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.policy_ir import PolicyActionType, PolicyRule, PolicyTriggerType

POLICY_SCHEDULED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_policy_scheduled_total",
    "Total policy scheduler outcomes",
    ["result"],
)
POLICY_TRIGGERED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_policy_triggered_total",
    "Total triggered policy actions",
    ["action_type"],
)
POLICY_SKIPPED_BUDGET = get_or_create_metric(
    Counter,
    "sparkle_policy_skipped_budget_total",
    "Total policy actions skipped by daily budget",
)
POLICY_SKIPPED_COOLDOWN = get_or_create_metric(
    Counter,
    "sparkle_policy_skipped_cooldown_total",
    "Total policy actions skipped by cooldown",
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PolicySchedulerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.compiler = PolicyCompilerService(db)
        self.kill_switch = AuroraStage24PolicyKillSwitchService()

    async def ensure_policies_for_user(self, *, user_id: UUID, now: datetime | None = None) -> list[AccountabilityPolicy]:
        reference_time = now or _utcnow()
        await self.compiler.ensure_policies_for_user(user_id=user_id, now=reference_time)
        return await self._recompute_schedule_state(user_id=user_id, now=reference_time)

    async def revoke_policy(self, policy_id: str) -> bool:
        result = await self.db.execute(select(AccountabilityPolicy).where(AccountabilityPolicy.policy_id == policy_id))
        row = result.scalar_one_or_none()
        if row is None:
            return False
        row.is_enabled = False
        row.revoked_at = _utcnow()
        row.next_trigger_at = None
        await self.db.commit()
        return True

    async def process_due_policies(self, *, now: datetime | None = None) -> dict[str, int]:
        reference_time = now or _utcnow()
        mode = await self.kill_switch.get_mode()
        if mode == "off":
            POLICY_SCHEDULED_TOTAL.labels(result="skipped_off").inc()
            return {"due_count": 0, "triggered_count": 0}

        result = await self.db.execute(
            select(AccountabilityPolicy).where(
                AccountabilityPolicy.is_enabled.is_(True),
                AccountabilityPolicy.revoked_at.is_(None),
                AccountabilityPolicy.next_trigger_at.is_not(None),
                AccountabilityPolicy.next_trigger_at <= reference_time,
            )
        )
        rows = result.scalars().all()
        triggered = 0
        for row in rows:
            outcome = await self._evaluate_policy_row(row, now=reference_time, event_type="time")
            if outcome == "triggered":
                triggered += 1
        return {"due_count": len(rows), "triggered_count": triggered}

    async def handle_event(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
        now: datetime | None = None,
    ) -> dict[str, int]:
        reference_time = now or _utcnow()
        mode = await self.kill_switch.get_mode()
        if mode == "off":
            POLICY_SCHEDULED_TOTAL.labels(result="skipped_off").inc()
            return {"matched_count": 0, "triggered_count": 0}

        commitment_id = payload.get("commitment_id")
        stmt = select(AccountabilityPolicy).where(
            AccountabilityPolicy.is_enabled.is_(True),
            AccountabilityPolicy.revoked_at.is_(None),
        )
        if commitment_id:
            stmt = stmt.where(AccountabilityPolicy.commitment_id == UUID(str(commitment_id)))
        elif payload.get("user_id"):
            stmt = stmt.where(AccountabilityPolicy.user_id == UUID(str(payload["user_id"])))
        else:
            return {"matched_count": 0, "triggered_count": 0}

        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        matched = 0
        triggered = 0
        for row in rows:
            rule = PolicyRule.model_validate(row.ir_payload)
            if not self._matches_event(rule, event_type=event_type, payload=payload):
                continue
            matched += 1
            outcome = await self._evaluate_policy_row(
                row,
                now=reference_time,
                event_type=event_type,
                event_payload=payload,
            )
            if outcome == "triggered":
                triggered += 1
        return {"matched_count": matched, "triggered_count": triggered}

    async def _recompute_schedule_state(
        self,
        *,
        user_id: UUID,
        now: datetime,
    ) -> list[AccountabilityPolicy]:
        result = await self.db.execute(
            select(AccountabilityPolicy).where(
                AccountabilityPolicy.user_id == user_id,
                AccountabilityPolicy.is_enabled.is_(True),
                AccountabilityPolicy.revoked_at.is_(None),
            )
        )
        rows = result.scalars().all()
        for row in rows:
            rule = PolicyRule.model_validate(row.ir_payload)
            row.next_trigger_at = self._next_trigger_at(rule)
        await self.db.commit()
        return rows

    def _next_trigger_at(self, rule: PolicyRule) -> datetime | None:
        due_at = rule.context.commitment_due_at
        if due_at is None:
            return None
        if rule.trigger.type == PolicyTriggerType.TIME_BEFORE_DUE:
            offset_days = int(rule.trigger.params.get("offset_days") or 0)
            return due_at - timedelta(days=offset_days)
        if rule.trigger.type == PolicyTriggerType.OVERDUE_BY:
            threshold_days = int(rule.trigger.params.get("threshold_days") or 0)
            return due_at + timedelta(days=threshold_days)
        return None

    def _matches_event(self, rule: PolicyRule, *, event_type: str, payload: dict[str, Any]) -> bool:
        partnership_id = payload.get("partnership_id")
        if partnership_id and str(rule.context.partnership_id or "") not in {"", str(partnership_id)}:
            return False
        if rule.trigger.type == PolicyTriggerType.PEER_MISSED:
            threshold = int(rule.trigger.params.get("threshold_days") or 0)
            return event_type == "peer_missed" and int(payload.get("missed_days") or 0) >= threshold
        if rule.trigger.type == PolicyTriggerType.STREAK_BREAK:
            threshold = int(rule.trigger.params.get("threshold_days") or 0)
            return event_type == "streak_break" and int(payload.get("missed_days") or 0) >= threshold
        if rule.trigger.type == PolicyTriggerType.SUCCESS_STREAK:
            threshold = int(rule.trigger.params.get("threshold_days") or 0)
            return event_type == "success_streak" and int(payload.get("success_days") or 0) >= threshold
        if rule.trigger.type == PolicyTriggerType.OVERDUE_BY:
            if event_type != "overdue_detected":
                return False
            threshold = int(rule.trigger.params.get("threshold_days") or 0)
            return int(payload.get("overdue_days") or 0) >= threshold
        return False

    async def _evaluate_policy_row(
        self,
        row: AccountabilityPolicy,
        *,
        now: datetime,
        event_type: str,
        event_payload: dict[str, Any] | None = None,
    ) -> str:
        rule = PolicyRule.model_validate(row.ir_payload)
        mode = await self.kill_switch.get_mode()
        if row.cooldown_until is not None and row.cooldown_until > now:
            row.last_skip_reason = "cooldown"
            POLICY_SKIPPED_COOLDOWN.inc()
            await self._emit_policy_event("policy_skipped_cooldown", row, now)
            await self.db.commit()
            return "cooldown"

        if rule.action.type in {PolicyActionType.NOTIFY_USER, PolicyActionType.NOTIFY_PARTNER}:
            if await self._budget_exhausted(rule.user_id, now):
                row.last_skip_reason = "budget"
                POLICY_SKIPPED_BUDGET.inc()
                await self._emit_policy_event("policy_skipped_budget", row, now)
                await self.db.commit()
                return "budget"

        if rule.constraints.partner_consent_required and (
            not rule.context.partner_consent_granted or rule.context.partner_id is None
        ):
            row.last_skip_reason = "partner_consent"
            await self.db.commit()
            return "partner_consent"

        if mode == "shadow":
            row.last_skip_reason = "shadow"
            row.last_triggered_at = now
            row.cooldown_until = now + timedelta(hours=int(rule.constraints.cooldown_hours or 24))
            row.next_trigger_at = None if row.next_trigger_at is not None else row.next_trigger_at
            row.is_shadow = True
            await self.db.commit()
            POLICY_SCHEDULED_TOTAL.labels(result="shadow").inc()
            return "shadow"

        await self._execute_action(rule, now=now, payload=event_payload or {})
        if rule.action.type in {PolicyActionType.NOTIFY_USER, PolicyActionType.NOTIFY_PARTNER}:
            await self._consume_budget(rule.user_id, now)
        row.last_skip_reason = None
        row.last_triggered_at = now
        row.cooldown_until = now + timedelta(hours=int(rule.constraints.cooldown_hours or 24))
        row.execution_count = int(row.execution_count or 0) + 1
        if row.next_trigger_at is not None:
            row.next_trigger_at = None
        await self.db.commit()
        POLICY_TRIGGERED_TOTAL.labels(action_type=rule.action.type.value).inc()
        POLICY_SCHEDULED_TOTAL.labels(result="triggered").inc()
        await self._emit_policy_event("policy_triggered", row, now)
        return "triggered"

    async def _execute_action(
        self,
        rule: PolicyRule,
        *,
        now: datetime,
        payload: dict[str, Any],
    ) -> None:
        if rule.action.type == PolicyActionType.NOTIFY_USER:
            await accountability_notification_service.send_policy_notification(
                self.db,
                user_id=rule.user_id,
                partnership_id=rule.context.partnership_id,
                policy_id=rule.policy_id,
                template_id=str(rule.action.params.get("template_id") or "policy_notification"),
                commitment_summary=rule.context.commitment_summary,
                due_at=rule.context.commitment_due_at,
            )
            return

        if rule.action.type == PolicyActionType.NOTIFY_PARTNER and rule.context.partner_id is not None:
            await accountability_notification_service.send_policy_notification(
                self.db,
                user_id=rule.context.partner_id,
                partnership_id=rule.context.partnership_id,
                policy_id=rule.policy_id,
                template_id=str(rule.action.params.get("template_id") or "policy_partner_notification"),
                commitment_summary=rule.context.commitment_summary,
                due_at=rule.context.commitment_due_at,
                actor_user_id=rule.user_id,
            )
            return

        if rule.action.type in {PolicyActionType.DOWNGRADE_PRIORITY, PolicyActionType.LOWER_DIFFICULTY}:
            result = await self.db.execute(select(EpisodicMemory).where(EpisodicMemory.id == rule.commitment_id))
            commitment = result.scalar_one_or_none()
            if commitment is None:
                return
            tags = [str(tag) for tag in (commitment.tags or [])]
            tag = str(rule.action.params.get("tag") or "")
            if tag and tag not in tags:
                tags.append(tag)
            if rule.action.type == PolicyActionType.LOWER_DIFFICULTY and "policy:next_step:smallest_viable" not in tags:
                tags.append("policy:next_step:smallest_viable")
            commitment.tags = tags

    async def _budget_exhausted(self, user_id: UUID, now: datetime) -> bool:
        key = self._budget_key(user_id, now)
        current = await cache_service.get(key)
        return int(current or 0) >= int(settings.AURORA_POLICY_DAILY_BUDGET or 2)

    async def _consume_budget(self, user_id: UUID, now: datetime) -> None:
        key = self._budget_key(user_id, now)
        current = int(await cache_service.get(key) or 0) + 1
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        ttl = max(1, int((tomorrow - now).total_seconds()))
        await cache_service.set(key, current, ttl=ttl)

    @staticmethod
    def _budget_key(user_id: UUID, now: datetime) -> str:
        return f"accountability:policy:budget:{user_id}:{now.date().isoformat()}"

    async def _emit_policy_event(
        self,
        event_name: str,
        row: AccountabilityPolicy,
        now: datetime,
    ) -> None:
        await event_bus.publish(
            event_name,
            {
                "event_type": event_name,
                "policy_id": row.policy_id,
                "user_id": str(row.user_id),
                "commitment_id": str(row.commitment_id),
                "timestamp": now.isoformat(),
            },
        )
