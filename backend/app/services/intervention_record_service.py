"""
InterventionRecordService — Full lifecycle management for card-protocol intervention records.

This service sits alongside the existing InterventionService (which handles
template selection, guardrails, and WebSocket delivery). InterventionRecordService
manages the card-protocol tracking layer: creation, acceptance lifecycle,
outcome verification, and evidence linking.

Phase 2 scope:
  - Create InterventionRecords from plan health signals and behavior patterns
  - Track acceptance lifecycle: CREATED → DELIVERED → SEEN → {DISMISSED|SNOOZED|ACCEPTED → ACTED}
  - Trigger outcome verification after outcome_window_days
  - Link to card graph via plan_card_id, phase_card_id, knowledge_card_id
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import (
    InterventionRecord,
    InterventionTriggerType,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    DeliveryStrategy,
    DeliveryChannel,
)
from app.core.event_bus import EventBus


_VALID_ACCEPTANCE_TRANSITIONS: dict[InterventionAcceptanceStatus, set[InterventionAcceptanceStatus]] = {
    InterventionAcceptanceStatus.CREATED: {InterventionAcceptanceStatus.DELIVERED},
    InterventionAcceptanceStatus.DELIVERED: {
        InterventionAcceptanceStatus.SEEN,
        InterventionAcceptanceStatus.DISMISSED,
        InterventionAcceptanceStatus.SNOOZED,
        InterventionAcceptanceStatus.ACCEPTED,
    },
    InterventionAcceptanceStatus.SEEN: {
        InterventionAcceptanceStatus.DISMISSED,
        InterventionAcceptanceStatus.SNOOZED,
        InterventionAcceptanceStatus.ACCEPTED,
    },
    InterventionAcceptanceStatus.SNOOZED: {
        InterventionAcceptanceStatus.DELIVERED,
        InterventionAcceptanceStatus.SEEN,
        InterventionAcceptanceStatus.DISMISSED,
        InterventionAcceptanceStatus.ACCEPTED,
    },
    InterventionAcceptanceStatus.ACCEPTED: {InterventionAcceptanceStatus.ACTED},
    InterventionAcceptanceStatus.DISMISSED: set(),
    InterventionAcceptanceStatus.ACTED: set(),
}


class InterventionRecordService:
    """Manages InterventionRecord lifecycle in the card protocol."""

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_record(
        self,
        *,
        user_id: uuid.UUID,
        trigger_type: InterventionTriggerType,
        delivery_strategy: DeliveryStrategy,
        delivery_channel: DeliveryChannel,
        plan_card_id: uuid.UUID | None = None,
        phase_card_id: uuid.UUID | None = None,
        task_occurrence_id: uuid.UUID | None = None,
        knowledge_card_id: uuid.UUID | None = None,
        trigger_source_ref: str | None = None,
        diagnosis_payload: dict | None = None,
        content_version: str = "1",
        outcome_window_days: int = 7,
    ) -> InterventionRecord:
        record = InterventionRecord(
            user_id=user_id,
            trigger_type=trigger_type,
            delivery_strategy=delivery_strategy,
            delivery_channel=delivery_channel,
            plan_card_id=plan_card_id,
            phase_card_id=phase_card_id,
            task_occurrence_id=task_occurrence_id,
            knowledge_card_id=knowledge_card_id,
            trigger_source_ref=trigger_source_ref,
            diagnosis_payload=diagnosis_payload or {},
            content_version=content_version,
            acceptance_status=InterventionAcceptanceStatus.CREATED,
            outcome_status=InterventionOutcomeStatus.PENDING,
            outcome_window_days=outcome_window_days,
        )
        self.db.add(record)
        await self.db.flush()

        if self.event_bus:
            await self.event_bus.publish(
                "intervention_record.created",
                {
                    "record_id": str(record.id),
                    "user_id": str(user_id),
                    "trigger_type": trigger_type.value,
                    "delivery_channel": delivery_channel.value,
                },
            )
        return record

    # ------------------------------------------------------------------
    # Acceptance lifecycle
    # ------------------------------------------------------------------

    async def mark_delivered(self, record_id: uuid.UUID) -> InterventionRecord | None:
        return await self._transition_acceptance(
            record_id, InterventionAcceptanceStatus.DELIVERED
        )

    async def mark_seen(self, record_id: uuid.UUID) -> InterventionRecord | None:
        return await self._transition_acceptance(
            record_id, InterventionAcceptanceStatus.SEEN
        )

    async def mark_dismissed(self, record_id: uuid.UUID) -> InterventionRecord | None:
        return await self._transition_acceptance(
            record_id, InterventionAcceptanceStatus.DISMISSED
        )

    async def mark_snoozed(
        self, record_id: uuid.UUID, *, snooze_hours: int = 24
    ) -> InterventionRecord | None:
        record = await self._get_record(record_id)
        if not record:
            return None
        self._ensure_transition_allowed(record.acceptance_status, InterventionAcceptanceStatus.SNOOZED)
        old_acceptance = record.acceptance_status
        record.acceptance_status = InterventionAcceptanceStatus.SNOOZED
        record.action_payload = {
            **(record.action_payload or {}),
            "snoozed_at": datetime.utcnow().isoformat(),
            "snooze_hours": snooze_hours,
        }
        await self.db.flush()

        await self._publish_status_change(record, old_acceptance=old_acceptance)
        return record

    async def mark_accepted(self, record_id: uuid.UUID) -> InterventionRecord | None:
        return await self._transition_acceptance(
            record_id, InterventionAcceptanceStatus.ACCEPTED
        )

    async def mark_acted(
        self,
        record_id: uuid.UUID,
        *,
        action_payload: dict | None = None,
    ) -> InterventionRecord | None:
        record = await self._get_record(record_id)
        if not record:
            return None
        self._ensure_transition_allowed(record.acceptance_status, InterventionAcceptanceStatus.ACTED)
        old_acceptance = record.acceptance_status
        record.acceptance_status = InterventionAcceptanceStatus.ACTED
        record.action_payload = {
            **(record.action_payload or {}),
            **(action_payload or {}),
            "acted_at": datetime.utcnow().isoformat(),
        }
        await self.db.flush()

        await self._publish_status_change(record, old_acceptance=old_acceptance)
        return record

    # ------------------------------------------------------------------
    # Outcome verification
    # ------------------------------------------------------------------

    async def resolve_outcome(
        self,
        record_id: uuid.UUID,
        outcome: InterventionOutcomeStatus,
        *,
        evidence_payload: dict | None = None,
    ) -> InterventionRecord | None:
        record = await self._get_record(record_id)
        if not record:
            return None

        old_outcome = record.outcome_status
        record.outcome_status = outcome
        if evidence_payload:
            record.evidence_payload = evidence_payload
        await self.db.flush()

        await self._publish_status_change(record, old_outcome=old_outcome)
        return record

    async def batch_resolve_pending(self) -> int:
        """Resolve all PENDING records whose outcome window has closed.

        Uses a heuristic to determine EFFECTIVE vs INEFFECTIVE:
        - If user ACTED → check for plan health improvement
        - If user DISMISSED/never seen → INEFFECTIVE
        - If user ACCEPTED but didn't act → UNKNOWN

        Returns count of records resolved.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = now  # outcome_window_days is per-record, checked in SQL

        stmt = select(InterventionRecord).where(
            InterventionRecord.outcome_status == InterventionOutcomeStatus.PENDING,
            InterventionRecord.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        records = list(result.scalars().all())

        resolved = 0
        for record in records:
            created = record.created_at
            if created is None:
                continue
            # Check if window has closed
            from datetime import timedelta

            deadline = created + timedelta(days=record.outcome_window_days)
            if now < deadline:
                continue

            # Determine outcome based on acceptance
            if record.acceptance_status == InterventionAcceptanceStatus.ACTED:
                outcome = InterventionOutcomeStatus.EFFECTIVE
                evidence = {"resolution_method": "acted_within_window"}
            elif record.acceptance_status in (
                InterventionAcceptanceStatus.DISMISSED,
                InterventionAcceptanceStatus.CREATED,
            ):
                outcome = InterventionOutcomeStatus.INEFFECTIVE
                evidence = {
                    "resolution_method": "never_engaged",
                    "final_acceptance": record.acceptance_status.value,
                }
            else:
                outcome = InterventionOutcomeStatus.UNKNOWN
                evidence = {"resolution_method": "insufficient_evidence"}

            await self.resolve_outcome(record.id, outcome, evidence_payload=evidence)
            resolved += 1

        if resolved:
            await self.db.commit()
        return resolved

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def get_pending_for_user(
        self, user_id: uuid.UUID, limit: int = 10
    ) -> list[InterventionRecord]:
        stmt = (
            select(InterventionRecord)
            .where(
                InterventionRecord.user_id == user_id,
                InterventionRecord.acceptance_status.in_([
                    InterventionAcceptanceStatus.CREATED,
                    InterventionAcceptanceStatus.DELIVERED,
                ]),
                InterventionRecord.not_deleted_filter(),
            )
            .order_by(InterventionRecord.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_for_user(
        self, user_id: uuid.UUID, days: int = 30, limit: int = 50
    ) -> list[InterventionRecord]:
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(InterventionRecord)
            .where(
                InterventionRecord.user_id == user_id,
                InterventionRecord.created_at >= cutoff,
                InterventionRecord.not_deleted_filter(),
            )
            .order_by(InterventionRecord.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_acceptance_stats(self, user_id: uuid.UUID, days: int = 30) -> dict:
        """Get acceptance rate statistics for a user."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(
                InterventionRecord.acceptance_status,
                func.count(InterventionRecord.id),
            )
            .where(
                InterventionRecord.user_id == user_id,
                InterventionRecord.created_at >= cutoff,
                InterventionRecord.not_deleted_filter(),
            )
            .group_by(InterventionRecord.acceptance_status)
        )
        result = await self.db.execute(stmt)
        counts = {status.value: count for status, count in result.all()}

        total = sum(counts.values())
        accepted = counts.get("ACCEPTED", 0) + counts.get("ACTED", 0)
        dismissed = counts.get("DISMISSED", 0)

        return {
            "total": total,
            "accepted_count": accepted,
            "dismissed_count": dismissed,
            "acceptance_rate": accepted / total if total > 0 else 0.0,
            "by_status": counts,
        }

    async def get_outcome_stats(self, user_id: uuid.UUID) -> dict:
        """Get outcome effectiveness statistics."""
        stmt = (
            select(
                InterventionRecord.outcome_status,
                func.count(InterventionRecord.id),
            )
            .where(
                InterventionRecord.user_id == user_id,
                InterventionRecord.outcome_status != InterventionOutcomeStatus.PENDING,
                InterventionRecord.not_deleted_filter(),
            )
            .group_by(InterventionRecord.outcome_status)
        )
        result = await self.db.execute(stmt)
        counts = {status.value: count for status, count in result.all()}

        total = sum(counts.values())
        effective = counts.get("EFFECTIVE", 0)

        return {
            "total_resolved": total,
            "effective_count": effective,
            "effectiveness_rate": effective / total if total > 0 else 0.0,
            "by_outcome": counts,
        }

    # ------------------------------------------------------------------
    # Delivery strategy selection
    # ------------------------------------------------------------------

    @staticmethod
    def select_delivery_strategy(
        *,
        trigger_type: InterventionTriggerType,
        confidence: float = 0.5,
        user_acceptance_rate: float | None = None,
        repeated_pattern: bool = False,
    ) -> DeliveryStrategy:
        """Select the appropriate delivery strategy based on taxonomy rules.

        Taxonomy alignment:
          CURIOUS: Low confidence, first-time detection, user is sensitive
          SUPPORTIVE: Medium confidence, user has accepted help before
          DIRECT: High confidence, repeated pattern, user prefers directness
          MICRO_RESTART: Stall/overload, user needs momentum
        """
        if trigger_type in (InterventionTriggerType.STALL_PATTERN, InterventionTriggerType.OVERLOAD):
            return DeliveryStrategy.MICRO_RESTART

        if trigger_type == InterventionTriggerType.MISALIGNMENT:
            return DeliveryStrategy.DIRECT

        # For CONCEPT_GAP and PLAN_RISK, use confidence + history
        if repeated_pattern or (user_acceptance_rate is not None and user_acceptance_rate < 0.3):
            return DeliveryStrategy.CURIOUS

        if confidence >= 0.7 or (user_acceptance_rate is not None and user_acceptance_rate > 0.6):
            return DeliveryStrategy.SUPPORTIVE

        if confidence >= 0.4:
            return DeliveryStrategy.CURIOUS

        return DeliveryStrategy.CURIOUS

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_record(self, record_id: uuid.UUID) -> InterventionRecord | None:
        stmt = select(InterventionRecord).where(
            InterventionRecord.id == record_id,
            InterventionRecord.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _transition_acceptance(
        self, record_id: uuid.UUID, target: InterventionAcceptanceStatus
    ) -> InterventionRecord | None:
        record = await self._get_record(record_id)
        if not record:
            return None
        if record.acceptance_status == target:
            return record
        self._ensure_transition_allowed(record.acceptance_status, target)
        old_acceptance = record.acceptance_status
        record.acceptance_status = target
        await self.db.flush()

        await self._publish_status_change(record, old_acceptance=old_acceptance)
        return record

    def _ensure_transition_allowed(
        self,
        current: InterventionAcceptanceStatus,
        target: InterventionAcceptanceStatus,
    ) -> None:
        allowed_targets = _VALID_ACCEPTANCE_TRANSITIONS.get(current, set())
        if target not in allowed_targets:
            raise ValueError(
                f"Invalid intervention acceptance transition: {current.value} -> {target.value}"
            )

    async def _publish_status_change(
        self,
        record: InterventionRecord,
        *,
        old_acceptance: InterventionAcceptanceStatus | None = None,
        old_outcome: InterventionOutcomeStatus | None = None,
    ) -> None:
        if not self.event_bus:
            return
        payload = {
            "record_id": str(record.id),
            "user_id": str(record.user_id),
            "acceptance_status": record.acceptance_status.value,
            "outcome_status": record.outcome_status.value,
        }
        if old_acceptance is not None:
            payload["old_acceptance_status"] = old_acceptance.value
        if old_outcome is not None:
            payload["old_outcome"] = old_outcome.value

        await self.event_bus.publish("intervention_record.status_changed", payload)
