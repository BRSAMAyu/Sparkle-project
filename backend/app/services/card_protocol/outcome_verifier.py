"""
Intervention Outcome Verifier — Checks whether interventions were effective.

This implements the verification pipeline for the growth loop:
  After outcome_window_days, examine plan health recovery, knowledge mastery
  improvement, or behavioral change to determine EFFECTIVE vs INEFFECTIVE.

Phase 2 provides the basic pipeline. Phase 3 deepens it with parameter compiler
and more sophisticated evidence analysis.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import (
    InterventionRecord,
    InterventionOutcomeStatus,
    InterventionAcceptanceStatus,
    InterventionTriggerType,
    Card,
    CardType,
)
from app.services.intervention_record_service import InterventionRecordService
from app.services.card_service import CardService
from app.core.event_bus import EventBus


class InterventionOutcomeVerifier:
    """Verifies intervention outcomes by examining post-intervention evidence.

    Runs as a periodic job (or on-demand) to resolve PENDING outcomes whose
    outcome_window has closed.
    """

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.record_service = InterventionRecordService(db, event_bus)
        self.card_service = CardService(db, event_bus)

    async def verify_all_pending(self) -> dict:
        """Verify all pending interventions whose outcome window has closed.

        Returns summary: {"resolved": N, "effective": N, "ineffective": N, "unknown": N}
        """
        now = datetime.utcnow()
        summary = {"resolved": 0, "effective": 0, "ineffective": 0, "unknown": 0}

        stmt = select(InterventionRecord).where(
            InterventionRecord.outcome_status == InterventionOutcomeStatus.PENDING,
            InterventionRecord.acceptance_status != InterventionAcceptanceStatus.CREATED,
            InterventionRecord.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        records = list(result.scalars().all())

        for record in records:
            # Check if outcome window has closed
            if record.created_at is None:
                continue
            deadline = record.created_at + timedelta(days=record.outcome_window_days)
            if now < deadline:
                continue

            outcome, evidence = await self._evaluate_outcome(record)
            if outcome is None:
                continue

            await self.record_service.resolve_outcome(
                record.id, outcome, evidence_payload=evidence
            )

            summary["resolved"] += 1
            if outcome == InterventionOutcomeStatus.EFFECTIVE:
                summary["effective"] += 1
            elif outcome == InterventionOutcomeStatus.INEFFECTIVE:
                summary["ineffective"] += 1
            else:
                summary["unknown"] += 1

        if summary["resolved"] > 0:
            await self.db.commit()

        if summary["resolved"] > 0:
            logger.info(
                "InterventionOutcomeVerifier: resolved {} interventions "
                "(effective={}, ineffective={}, unknown={})",
                summary["resolved"],
                summary["effective"],
                summary["ineffective"],
                summary["unknown"],
            )
        return summary

    async def _evaluate_outcome(
        self, record: InterventionRecord
    ) -> tuple[InterventionOutcomeStatus | None, dict]:
        """Evaluate a single intervention's outcome.

        Returns (outcome, evidence) or (None, {}) if insufficient data.
        """
        evidence: dict = {"record_id": str(record.id), "evaluation_method": ""}

        # 1. If user never engaged → INEFFECTIVE
        if record.acceptance_status in (
            InterventionAcceptanceStatus.CREATED,
            InterventionAcceptanceStatus.DELIVERED,
            InterventionAcceptanceStatus.DISMISSED,
        ):
            evidence["evaluation_method"] = "no_engagement"
            evidence["final_acceptance"] = record.acceptance_status.value
            return InterventionOutcomeStatus.INEFFECTIVE, evidence

        # 2. If user ACTED → check for improvement
        if record.acceptance_status == InterventionAcceptanceStatus.ACTED:
            improvement = await self._check_improvement(record)
            evidence["evaluation_method"] = "acted_and_measured"
            evidence["improvement"] = improvement

            if improvement.get("plan_health_recovered") or improvement.get("mastery_improved"):
                return InterventionOutcomeStatus.EFFECTIVE, evidence
            if improvement.get("has_sufficient_data"):
                return InterventionOutcomeStatus.INEFFECTIVE, evidence
            return InterventionOutcomeStatus.UNKNOWN, evidence

        # 3. If user ACCEPTED but didn't act → UNKNOWN
        if record.acceptance_status == InterventionAcceptanceStatus.ACCEPTED:
            evidence["evaluation_method"] = "accepted_no_action"
            return InterventionOutcomeStatus.UNKNOWN, evidence

        # 4. SEEN or SNOOZED → check passive improvement
        if record.acceptance_status in (
            InterventionAcceptanceStatus.SEEN,
            InterventionAcceptanceStatus.SNOOZED,
        ):
            improvement = await self._check_improvement(record)
            evidence["evaluation_method"] = "passive_improvement_check"
            evidence["improvement"] = improvement

            if improvement.get("plan_health_recovered"):
                return InterventionOutcomeStatus.EFFECTIVE, evidence
            return InterventionOutcomeStatus.UNKNOWN, evidence

        return None, {}

    async def _check_improvement(self, record: InterventionRecord) -> dict:
        """Check whether the condition that triggered the intervention improved.

        This is Phase 2's basic implementation. Phase 3 deepens this with:
          - Parameter compiler tracking
          - Decision log verification
          - Mastery trend analysis
        """
        improvement: dict = {"has_sufficient_data": False}

        # For PLAN_RISK / OVERLOAD / STALL: check plan card health
        if record.trigger_type in (
            InterventionTriggerType.PLAN_RISK,
            InterventionTriggerType.OVERLOAD,
            InterventionTriggerType.STALL_PATTERN,
        ):
            if record.plan_card_id:
                plan_card = await self.card_service.get_card(record.plan_card_id)
                if plan_card:
                    meta = plan_card.metadata_ or {}
                    # Check if plan has been replanned or adjusted since intervention
                    last_adjustment = meta.get("latest_adjustment_evidence", {})
                    last_replan = meta.get("replan_event", {})
                    if self._event_is_newer_than_record(last_adjustment, record):
                        improvement["plan_health_recovered"] = True
                        improvement["recovery_detail"] = last_adjustment
                    elif self._event_is_newer_than_record(last_replan, record):
                        improvement["plan_health_recovered"] = True
                        improvement["recovery_detail"] = last_replan
                    improvement["has_sufficient_data"] = True

        # For CONCEPT_GAP: check knowledge card mastery state
        if record.trigger_type == InterventionTriggerType.CONCEPT_GAP:
            if record.knowledge_card_id:
                knowledge_card = await self.card_service.get_card(record.knowledge_card_id)
                if knowledge_card:
                    meta = knowledge_card.metadata_ or {}
                    mastery_state = meta.get("mastery_state", "unknown")
                    if mastery_state not in ("at_risk", "unknown"):
                        improvement["mastery_improved"] = True
                        improvement["new_mastery_state"] = mastery_state
                    improvement["has_sufficient_data"] = True

        return improvement

    @staticmethod
    def _event_is_newer_than_record(event_payload: dict | None, record: InterventionRecord) -> bool:
        if not event_payload or not record.created_at:
            return False

        timestamp_value = event_payload.get("timestamp")
        if not timestamp_value:
            return False

        try:
            event_time = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return False

        if event_time.tzinfo is not None:
            event_time = event_time.replace(tzinfo=None)

        created_at = record.created_at
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)
        return event_time >= created_at
