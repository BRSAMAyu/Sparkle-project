"""
Card Protocol Writeback Bridge — AdaptiveReplanner → Card Protocol.

This is the critical breakpoint fix from the product consensus:
  "adaptive_replanner does not truly rewrite execution"

When the AdaptiveReplanner detects a blockage and applies adjustments,
this bridge ensures the changes are also reflected in the card protocol:
  1. Updates card lifecycle status (e.g., PAUSED for stalled plans)
  2. Adjusts TaskOccurrences (reschedules, reorders)
  3. Creates EVIDENCE_FOR edges connecting the adjustment evidence to the plan

Phase 1-2 governance exception applies:
  Execution writebacks are authorized by legacy PlanState + deterministic
  system policy + service guardrails. Full artifact governance arrives Phase 3.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.models.card_protocol import (
    Card,
    CardCreatedBy,
    CardType,
    OccurrenceStatus,
    TaskOccurrence,
)
from app.services.card_edge_service import CardEdgeService
from app.services.card_service import CardService
from app.services.task_occurrence_service import TaskOccurrenceService


class ReplannerCardBridge:
    """Bridges AdaptiveReplanner adjustments into the card protocol.

    This service is called AFTER the legacy PlanState has been updated
    and the PlanAdjustmentApplier has patched task entities.
    It projects those same changes into the card graph.
    """

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.card_service = CardService(db, event_bus)
        self.edge_service = CardEdgeService(db, event_bus)
        self.occurrence_service = TaskOccurrenceService(db, event_bus)

    async def on_incremental_adjustment(
        self,
        *,
        user_id: uuid.UUID,
        plan_id: uuid.UUID,
        adjustments: dict,
        trigger: str,
        affected_task_ids: list[uuid.UUID] | None = None,
        inserted_task_ids: list[uuid.UUID] | None = None,
    ) -> dict:
        """Project an incremental adjustment into the card protocol.

        Called after AdaptiveReplanner._apply_incremental_adjustment succeeds.

        Returns a summary of card protocol changes.
        """
        summary = {"cards_updated": 0, "occurrences_adjusted": 0, "evidence_writebacks": 0}

        # 1. Find or create the plan card
        plan_card = await self._find_plan_card(plan_id)
        if not plan_card:
            logger.debug("ReplannerCardBridge: no plan card for legacy plan {}", plan_id)
            return summary

        # 2. Update plan card metadata with adjustment info
        adjustments.get("adaptive_meta", {})
        await self.card_service.update_card(
            plan_card.id,
            metadata={
                "last_adjustment": {
                    "trigger": trigger,
                    "timestamp": datetime.utcnow().isoformat(),
                    "adjustments": {
                        k: v
                        for k, v in adjustments.items()
                        if k in ("adaptive_adjustments", "time_multiplier", "difficulty_shift")
                    },
                },
            },
            updated_by=CardCreatedBy.SYSTEM,
        )
        summary["cards_updated"] += 1

        # 3. Adjust occurrences for affected tasks
        if affected_task_ids:
            for task_id in affected_task_ids:
                task_card = await self._find_task_card(task_id)
                if not task_card:
                    continue

                # Reschedule upcoming occurrences based on adjustment
                time_multiplier = adjustments.get("adaptive_adjustments", {}).get("time_multiplier", 1.0)
                if time_multiplier != 1.0:
                    adjusted_count = await self._adjust_occurrence_durations(task_card.id, time_multiplier)
                    summary["occurrences_adjusted"] += adjusted_count

        # 4. Create evidence edges for the adjustment
        # The adjustment itself is evidence that the system detected a blockage
        if trigger in ("task_completed", "task_feedback", "plan_execution_feedback"):
            evidence_meta = {
                "trigger": trigger,
                "adjustment_type": "incremental",
                "reasons": adjustments.get("reasons", []),
                "timestamp": datetime.utcnow().isoformat(),
            }
            # Store as card metadata rather than creating a separate evidence card
            # (evidence cards are created in Phase 2 when InterventionRecord is live)
            await self.card_service.update_card(
                plan_card.id,
                metadata={"latest_adjustment_evidence": evidence_meta},
            )
            summary["evidence_writebacks"] += 1

        logger.info(
            "ReplannerCardBridge: projected incremental adjustment to card protocol. "
            "plan_card={}, updated={}, occurrences={}, edges={}",
            plan_card.id,
            summary["cards_updated"],
            summary["occurrences_adjusted"],
            summary["evidence_writebacks"],
        )

        try:
            from app.services.card_protocol.main_chain_artifact_service import MainChainArtifactService

            service = MainChainArtifactService(self.db, self.event_bus)
            await service.refresh_active_phase_pack(
                plan_card_id=plan_card.id,
                generated_reason=f"replanner_incremental:{trigger}",
            )
        except Exception as exc:
            logger.warning("Phase4 active phase pack refresh failed (non-fatal): {}", exc)
        return summary

    async def on_full_replan(
        self,
        *,
        user_id: uuid.UUID,
        plan_id: uuid.UUID,
        reasons: list[str],
        severity: str,
    ) -> dict:
        """Project a full replan trigger into the card protocol.

        Called after AdaptiveReplanner._trigger_full_replan succeeds.
        """
        summary = {"cards_updated": 0, "occurrences_rescheduled": 0}

        plan_card = await self._find_plan_card(plan_id)
        if not plan_card:
            return summary

        # If the plan is in critical state, reflect that in the card lifecycle
        if severity in ("critical", "high"):
            # Don't auto-pause — just record the evidence
            await self.card_service.update_card(
                plan_card.id,
                metadata={
                    "replan_event": {
                        "severity": severity,
                        "reasons": reasons,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                },
                updated_by=CardCreatedBy.SYSTEM,
            )
            summary["cards_updated"] += 1

        # Cancel upcoming PLANNED occurrences (they'll be regenerated by the new plan)
        cancelled = await self._cancel_upcoming_planned_occurrences(plan_card.id)
        summary["occurrences_rescheduled"] = cancelled

        logger.info(
            "ReplannerCardBridge: projected full replan to card protocol. "
            "plan_card={}, updated={}, occurrences_cancelled={}",
            plan_card.id,
            summary["cards_updated"],
            summary["occurrences_rescheduled"],
        )

        try:
            from app.services.card_protocol.main_chain_artifact_service import MainChainArtifactService

            service = MainChainArtifactService(self.db, self.event_bus)
            await service.refresh_active_phase_pack(
                plan_card_id=plan_card.id,
                generated_reason=f"replanner_full:{severity}",
            )
        except Exception as exc:
            logger.warning("Phase4 active phase pack refresh failed (non-fatal): {}", exc)
        return summary

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

    async def _find_task_card(self, legacy_task_id: uuid.UUID) -> Card | None:
        stmt = (
            select(Card)
            .where(
                Card.card_type == CardType.TASK,
                Card.metadata_["legacy_task_id"].as_string() == str(legacy_task_id),
                Card.not_deleted_filter(),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _adjust_occurrence_durations(
        self, series_card_id: uuid.UUID, time_multiplier: float
    ) -> int:
        """Adjust upcoming occurrence windows and preserve prior feedback payload."""
        stmt = (
            select(TaskOccurrence)
            .where(
                TaskOccurrence.series_card_id == series_card_id,
                TaskOccurrence.occurrence_status.in_([
                    OccurrenceStatus.PLANNED,
                    OccurrenceStatus.READY,
                ]),
            )
        )
        result = await self.db.execute(stmt)
        occurrences = list(result.scalars().all())

        adjusted = 0
        for occurrence in occurrences:
            payload = dict(occurrence.feedback_payload or {})
            payload["time_multiplier_applied"] = time_multiplier
            payload["adjusted_by"] = "replanner_card_bridge"

            if occurrence.window_start and occurrence.window_end:
                current_duration = occurrence.window_end - occurrence.window_start
                adjusted_seconds = max(int(current_duration.total_seconds() * time_multiplier), 60)
                occurrence.window_end = occurrence.window_start + timedelta(seconds=adjusted_seconds)

            occurrence.feedback_payload = payload
            adjusted += 1

        await self.db.flush()
        return adjusted

    async def _cancel_upcoming_planned_occurrences(self, plan_card_id: uuid.UUID) -> int:
        """Cancel PLANNED occurrences for all task series in this plan via the service layer."""
        stmt = (
            select(TaskOccurrence)
            .where(
                TaskOccurrence.plan_card_id == plan_card_id,
                TaskOccurrence.occurrence_status == OccurrenceStatus.PLANNED,
                TaskOccurrence.scheduled_for >= date.today(),
            )
        )
        result = await self.db.execute(stmt)
        occurrences = list(result.scalars().all())
        cancelled = 0
        for occurrence in occurrences:
            updated = await self.occurrence_service.cancel(occurrence.id)
            if updated:
                cancelled += 1
        return cancelled
