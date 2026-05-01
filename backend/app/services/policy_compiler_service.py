from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from prometheus_client import Counter, Histogram
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.metrics import get_or_create_metric
from app.models.accountability_policy import AccountabilityPolicy
from app.models.memory import EpisodicMemory
from app.services.aurora_stage24_policy_kill_switch_service import AuroraStage24PolicyKillSwitchService
from app.services.policy_ir import (
    POLICY_IR_VERSION,
    PolicyAction,
    PolicyActionType,
    PolicyConstraints,
    PolicyContext,
    PolicyRule,
    PolicyTrigger,
    PolicyTriggerType,
)

POLICY_COMPILED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_policy_compiled_total",
    "Total policy compilation results",
    ["result"],
)

POLICY_COMPILE_LATENCY = get_or_create_metric(
    Histogram,
    "sparkle_policy_compile_seconds",
    "Policy compiler latency in seconds",
    buckets=[0.001, 0.003, 0.005, 0.008, 0.01, 0.02, 0.05],
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class CommitmentPolicyContext:
    partner_id: UUID | None = None
    partnership_id: UUID | None = None
    partner_consent_granted: bool = False
    tags: tuple[str, ...] = ()


class PolicyCompilerService:
    TEMPLATE_IDS = (
        "due_reminder_3d",
        "due_reminder_1d",
        "due_reminder_0d",
        "peer_missed_3d_partner_notify",
        "overdue_priority_2d",
        "overdue_difficulty_5d",
        "success_streak_7d_positive_feedback",
        "retro_request_overdue_1d",
    )

    def __init__(self, db: AsyncSession):
        self.db = db
        self.kill_switch = AuroraStage24PolicyKillSwitchService()

    async def compile_for_commitment(
        self,
        commitment: EpisodicMemory,
        *,
        persist: bool = False,
        now: datetime | None = None,
    ) -> list[PolicyRule]:
        started = time.perf_counter()
        reference_time = now or _utcnow()
        try:
            mode = await self.kill_switch.get_mode()
            if mode == "off":
                POLICY_COMPILED_TOTAL.labels(result="skipped_off").inc()
                return []

            rules = self._compile_rules(commitment, reference_time=reference_time)
            if persist:
                await self._persist_rules(
                    commitment=commitment,
                    rules=rules,
                    is_shadow=(mode == "shadow"),
                )
            POLICY_COMPILED_TOTAL.labels(result="ok").inc()
            return rules
        finally:
            POLICY_COMPILE_LATENCY.observe(max(0.0, time.perf_counter() - started))

    async def ensure_policies_for_user(
        self,
        *,
        user_id: UUID,
        now: datetime | None = None,
    ) -> list[PolicyRule]:
        mode = await self.kill_switch.get_mode()
        if mode == "off":
            return []

        reference_time = now or _utcnow()
        result = await self.db.execute(
            select(EpisodicMemory).where(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.subject_type == "commitment",
                EpisodicMemory.due_at.is_not(None),
                EpisodicMemory.resolved_at.is_(None),
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.archived_at.is_(None),
                EpisodicMemory.retracted_at.is_(None),
                EpisodicMemory.revoked_at.is_(None),
            )
        )
        rules: list[PolicyRule] = []
        for commitment in result.scalars().all():
            rules.extend(
                await self.compile_for_commitment(
                    commitment,
                    persist=True,
                    now=reference_time,
                )
            )
        return rules

    async def revoke_for_commitment(self, *, commitment_id: UUID, user_id: UUID) -> int:
        result = await self.db.execute(
            select(AccountabilityPolicy).where(
                AccountabilityPolicy.commitment_id == commitment_id,
                AccountabilityPolicy.user_id == user_id,
            )
        )
        updated = 0
        for row in result.scalars().all():
            row.is_enabled = False
            row.revoked_at = _utcnow()
            row.next_trigger_at = None
            updated += 1
        if updated:
            await self.db.commit()
        return updated

    def _compile_rules(
        self,
        commitment: EpisodicMemory,
        *,
        reference_time: datetime,
    ) -> list[PolicyRule]:
        if commitment.due_at is None:
            return []

        policy_context = self._extract_context(commitment)
        shared_context = PolicyContext(
            commitment_summary=commitment.summary,
            commitment_due_at=commitment.due_at,
            commitment_created_at=commitment.created_at,
            evidence_token=commitment.evidence_token,
            partnership_id=policy_context.partnership_id,
            partner_id=policy_context.partner_id,
            partner_consent_granted=policy_context.partner_consent_granted,
            tags=policy_context.tags,
            metadata={"source_type": commitment.source_type},
        )
        daily_budget = int(settings.AURORA_POLICY_DAILY_BUDGET)
        cooldown_hours = int(settings.AURORA_POLICY_COOLDOWN_HOURS)

        def rule(
            template_id: str,
            *,
            trigger_type: PolicyTriggerType,
            trigger_params: dict[str, object],
            action_type: PolicyActionType,
            action_params: dict[str, object],
            partner_consent_required: bool = False,
        ) -> PolicyRule:
            return PolicyRule(
                policy_id=f"{template_id}:{commitment.id}",
                commitment_id=commitment.id,
                user_id=commitment.user_id,
                trigger=PolicyTrigger(type=trigger_type, params=trigger_params),
                action=PolicyAction(type=action_type, params=action_params),
                constraints=PolicyConstraints(
                    daily_budget=daily_budget if action_type in {PolicyActionType.NOTIFY_USER, PolicyActionType.NOTIFY_PARTNER} else None,
                    cooldown_hours=cooldown_hours,
                    partner_consent_required=partner_consent_required,
                ),
                context=shared_context,
                version=POLICY_IR_VERSION,
            )

        rules = [
            rule(
                "due_reminder_3d",
                trigger_type=PolicyTriggerType.TIME_BEFORE_DUE,
                trigger_params={"offset_days": 3},
                action_type=PolicyActionType.NOTIFY_USER,
                action_params={"channel": "in_app", "template_id": "policy_due_reminder_3d"},
            ),
            rule(
                "due_reminder_1d",
                trigger_type=PolicyTriggerType.TIME_BEFORE_DUE,
                trigger_params={"offset_days": 1},
                action_type=PolicyActionType.NOTIFY_USER,
                action_params={"channel": "in_app", "template_id": "policy_due_reminder_1d"},
            ),
            rule(
                "due_reminder_0d",
                trigger_type=PolicyTriggerType.TIME_BEFORE_DUE,
                trigger_params={"offset_days": 0},
                action_type=PolicyActionType.NOTIFY_USER,
                action_params={"channel": "in_app", "template_id": "policy_due_reminder_due_today"},
            ),
            rule(
                "peer_missed_3d_partner_notify",
                trigger_type=PolicyTriggerType.PEER_MISSED,
                trigger_params={"threshold_days": 3},
                action_type=PolicyActionType.NOTIFY_PARTNER,
                action_params={"channel": "in_app", "template_id": "policy_peer_missed_3d"},
                partner_consent_required=True,
            ),
            rule(
                "overdue_priority_2d",
                trigger_type=PolicyTriggerType.OVERDUE_BY,
                trigger_params={"threshold_days": 2},
                action_type=PolicyActionType.DOWNGRADE_PRIORITY,
                action_params={"tag": "policy:priority:downgraded"},
            ),
            rule(
                "overdue_difficulty_5d",
                trigger_type=PolicyTriggerType.OVERDUE_BY,
                trigger_params={"threshold_days": 5},
                action_type=PolicyActionType.LOWER_DIFFICULTY,
                action_params={"tag": "policy:difficulty:lowered"},
            ),
            rule(
                "success_streak_7d_positive_feedback",
                trigger_type=PolicyTriggerType.SUCCESS_STREAK,
                trigger_params={"threshold_days": 7},
                action_type=PolicyActionType.NOTIFY_USER,
                action_params={"channel": "in_app", "template_id": "policy_success_streak_7d"},
            ),
            rule(
                "retro_request_overdue_1d",
                trigger_type=PolicyTriggerType.OVERDUE_BY,
                trigger_params={"threshold_days": 1, "requires_missing_outcome": True},
                action_type=PolicyActionType.NOTIFY_USER,
                action_params={"channel": "in_app", "template_id": "policy_retro_request_due_without_outcome"},
            ),
        ]
        return rules

    async def _persist_rules(
        self,
        *,
        commitment: EpisodicMemory,
        rules: list[PolicyRule],
        is_shadow: bool,
    ) -> None:
        existing_result = await self.db.execute(
            select(AccountabilityPolicy).where(AccountabilityPolicy.commitment_id == commitment.id)
        )
        existing_by_policy_id = {row.policy_id: row for row in existing_result.scalars().all()}
        active_policy_ids = {rule.policy_id for rule in rules}

        for stale_id, stale_row in existing_by_policy_id.items():
            if stale_id in active_policy_ids:
                continue
            stale_row.is_enabled = False
            stale_row.revoked_at = _utcnow()
            stale_row.next_trigger_at = None

        for rule in rules:
            payload = rule.model_dump(mode="json")
            ir_hash = self._hash_payload(payload)
            row = existing_by_policy_id.get(rule.policy_id)
            if row is None:
                row = AccountabilityPolicy(
                    policy_id=rule.policy_id,
                    user_id=rule.user_id,
                    commitment_id=rule.commitment_id,
                    policy_version=rule.version,
                    policy_type=rule.action.params.get("template_id") or rule.action.type.value,
                    trigger_type=rule.trigger.type.value,
                    action_type=rule.action.type.value,
                    ir_payload=payload,
                    ir_hash=ir_hash,
                    is_shadow=is_shadow,
                )
                self.db.add(row)
            else:
                row.policy_version = rule.version
                row.policy_type = str(rule.action.params.get("template_id") or rule.action.type.value)
                row.trigger_type = rule.trigger.type.value
                row.action_type = rule.action.type.value
                row.ir_payload = payload
                row.ir_hash = ir_hash
                row.is_enabled = True
                row.is_shadow = is_shadow
                row.revoked_at = None

        await self.db.commit()

    @staticmethod
    def _hash_payload(payload: dict[str, object]) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _extract_context(commitment: EpisodicMemory) -> CommitmentPolicyContext:
        tags = tuple(str(item) for item in (commitment.tags or []))
        partner_id: UUID | None = None
        partnership_id: UUID | None = None
        partner_consent_granted = False
        for tag in tags:
            if tag in {"accountability:partner_consent", "accountability:partner_consent:true"}:
                partner_consent_granted = True
            elif tag.startswith("accountability:partner_id:"):
                raw = tag.split("accountability:partner_id:", 1)[1].strip()
                if raw:
                    partner_id = UUID(raw)
            elif tag.startswith("accountability:partnership_id:"):
                raw = tag.split("accountability:partnership_id:", 1)[1].strip()
                if raw:
                    partnership_id = UUID(raw)
        return CommitmentPolicyContext(
            partner_id=partner_id,
            partnership_id=partnership_id,
            partner_consent_granted=partner_consent_granted,
            tags=tags,
        )
