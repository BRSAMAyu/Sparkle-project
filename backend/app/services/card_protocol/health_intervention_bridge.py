"""
Plan Health → Intervention Record Bridge.

This fixes breakpoint 3 from the product consensus:
  "plan_health = critical does not reliably become action"

Currently: PlanHealthSignalService emits events, but no consumer creates
InterventionRecords from them. The plan_health_event_consumer only generates
silent system updates.

This bridge:
  1. Consumes plan health signals (critical/warning)
  2. Creates InterventionRecords with appropriate trigger_type and delivery_strategy
  3. Links to the plan card in the card protocol

Integration: This should be called from the plan_health_event_consumer after
the existing lightweight system update, or as a dedicated event consumer.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import (
    Card,
    CardType,
    InterventionTriggerType,
    DeliveryStrategy,
    DeliveryChannel,
    InterventionRecord,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
)
from app.services.intervention_record_service import InterventionRecordService
from app.services.card_service import CardService
from app.core.event_bus import EventBus


class PlanHealthInterventionBridge:
    """Converts plan health signals into tracked intervention records.

    Usage:
        bridge = PlanHealthInterventionBridge(db, event_bus)
        await bridge.on_plan_health_signal(
            user_id=user_id,
            plan_id=plan_id,
            severity="critical",
            reasons=["stall_detected", "low_completion_rate"],
            action_taken="adjustment_cooldown_active",
        )
    """

    # Minimum severity levels that warrant an intervention record
    INTERVENTION_THRESHOLDS = {
        "critical": DeliveryStrategy.SUPPORTIVE,
        "warning": DeliveryStrategy.CURIOUS,
    }

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.record_service = InterventionRecordService(db, event_bus)
        self.card_service = CardService(db, event_bus)

    async def on_plan_health_signal(
        self,
        *,
        user_id: uuid.UUID,
        plan_id: uuid.UUID,
        severity: str,
        reasons: list[str],
        action_taken: str,
        context: dict | None = None,
    ) -> InterventionRecord | None:
        """Create an InterventionRecord from a plan health signal.

        Only creates a record if:
          1. Severity meets the threshold (critical or warning)
          2. The user doesn't already have a recent PENDING intervention for this plan
          3. A plan card exists in the card protocol

        Returns the created record, or None if conditions not met.
        """
        # 1. Check severity threshold
        if severity not in self.INTERVENTION_THRESHOLDS:
            return None

        # 2. Find the plan card
        plan_card = await self._find_plan_card(plan_id)
        if not plan_card:
            logger.debug(
                "PlanHealthInterventionBridge: no plan card for legacy plan {}, "
                "skipping intervention record",
                plan_id,
            )
            return None

        # 3. Check for recent pending intervention for this plan
        has_pending = await self._has_recent_pending(user_id, plan_card.id)
        if has_pending:
            logger.debug(
                "PlanHealthInterventionBridge: user {} already has pending intervention "
                "for plan card {}, skipping",
                user_id,
                plan_card.id,
            )
            return None

        # 4. Determine trigger type from reasons
        trigger_type = self._classify_trigger(severity, reasons)

        # 5. Select delivery strategy
        delivery_strategy = self.INTERVENTION_THRESHOLDS[severity]

        # 6. Determine delivery channel
        delivery_channel = self._select_channel(action_taken)

        # 7. Build diagnosis payload
        diagnosis = {
            "plan_health_severity": severity,
            "reasons": reasons,
            "action_taken": action_taken,
            "plan_card_id": str(plan_card.id),
            "context": context or {},
            "detected_at": datetime.utcnow().isoformat(),
        }

        # 8. Create the record
        record = await self.record_service.create_record(
            user_id=user_id,
            trigger_type=trigger_type,
            delivery_strategy=delivery_strategy,
            delivery_channel=delivery_channel,
            plan_card_id=plan_card.id,
            trigger_source_ref=f"plan_health:{plan_id}:{severity}",
            diagnosis_payload=diagnosis,
            outcome_window_days=7,
        )

        logger.info(
            "PlanHealthInterventionBridge: created intervention record {} for plan {} "
            "severity={}, trigger={}, channel={}",
            record.id,
            plan_id,
            severity,
            trigger_type.value,
            delivery_channel.value,
        )
        return record

    def _classify_trigger(
        self, severity: str, reasons: list[str]
    ) -> InterventionTriggerType:
        """Map plan health reasons to intervention trigger types."""
        reason_str = " ".join(reasons).lower()

        if any(kw in reason_str for kw in ("stall", "inactive", "no_progress", "deferral")):
            return InterventionTriggerType.STALL_PATTERN

        if any(kw in reason_str for kw in ("overload", "too_many", "time_overrun", "overtime")):
            return InterventionTriggerType.OVERLOAD

        if any(kw in reason_str for kw in ("concept_gap", "knowledge", "mastery")):
            return InterventionTriggerType.CONCEPT_GAP

        if any(kw in reason_str for kw in ("misalign", "drift", "deviation")):
            return InterventionTriggerType.MISALIGNMENT

        # Default for plan health issues
        return InterventionTriggerType.PLAN_RISK

    def _select_channel(self, action_taken: str) -> DeliveryChannel:
        """Select delivery channel based on what action was already taken."""
        if action_taken in ("full_replan_triggered", "incremental_adjustment_applied"):
            # System already acted — use chat to inform, not push to pressure
            return DeliveryChannel.CHAT

        if action_taken in ("replan_cooldown_active", "adjustment_cooldown_active"):
            # System wanted to act but was on cooldown — use in-app banner
            return DeliveryChannel.IN_APP

        # Default to chat for gentle delivery
        return DeliveryChannel.CHAT

    async def _find_plan_card(self, legacy_plan_id: uuid.UUID) -> Card | None:
        stmt = (
            select(Card)
            .where(
                Card.card_type == CardType.PLAN,
                Card.metadata_["legacy_plan_id"].as_string() == str(legacy_plan_id),
                Card.not_deleted_filter(),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _has_recent_pending(
        self, user_id: uuid.UUID, plan_card_id: uuid.UUID
    ) -> bool:
        """Check if user has a recent unresolved intervention for this plan."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=24)
        stmt = (
            select(InterventionRecord)
            .where(
                InterventionRecord.user_id == user_id,
                InterventionRecord.plan_card_id == plan_card_id,
                InterventionRecord.acceptance_status.in_([
                    InterventionAcceptanceStatus.CREATED,
                    InterventionAcceptanceStatus.DELIVERED,
                    InterventionAcceptanceStatus.SEEN,
                    InterventionAcceptanceStatus.SNOOZED,
                    InterventionAcceptanceStatus.ACCEPTED,
                ]),
                InterventionRecord.outcome_status == InterventionOutcomeStatus.PENDING,
                InterventionRecord.created_at >= cutoff,
                InterventionRecord.not_deleted_filter(),
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
