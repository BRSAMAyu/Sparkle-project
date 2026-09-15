"""Behavioral outcome tracking for adaptive interventions."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intervention_adaptive import BehavioralOutcome
from app.services.outcome_promotion_governor import OutcomePromotionGovernor
from app.services.plan_outcome_service import EVIDENCE_LEVEL_BEHAVIORAL_SIGNAL, PlanOutcomeService


class BehavioralOutcomeTracker:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.plan_outcome_service = PlanOutcomeService(db)
        self.outcome_promotion_governor = OutcomePromotionGovernor(db)

    async def record(
        self,
        user_id: UUID,
        intervention_id: UUID,
        outcome_type: str,
        time_to_outcome: int,
        success: bool,
        context: dict[str, Any] | None = None,
    ) -> BehavioralOutcome:
        outcome = BehavioralOutcome(
            user_id=user_id,
            intervention_id=intervention_id,
            outcome_type=outcome_type,
            time_to_outcome=time_to_outcome,
            success=success,
            context=context,
        )
        self.db.add(outcome)
        await self.db.commit()
        await self.db.refresh(outcome)
        outcome_record = await self.plan_outcome_service.record_outcome(
            user_id,
            source_family="behavioral_outcome",
            source_id=str(outcome.id),
            evidence_level=EVIDENCE_LEVEL_BEHAVIORAL_SIGNAL,
            target_type="intervention",
            target_layer="session",
            target_object=str(intervention_id),
            target_hypothesis=outcome_type,
            observed_outcome="success" if success else "failure",
            outcome_signal={"outcome_type": outcome_type, "time_to_outcome": time_to_outcome, **(context or {})},
            time_horizon="short_horizon_behavior",
            confidence=0.74 if success else 0.7,
            evidence_strength="strong" if success else "medium",
            evidence_sources=["behavioral_outcome_tracker"],
            planning_implications=(
                {"preserve_success_pattern": bool(success)}
                if success
                else {"lighter_first_step": True, "scaffold_level": "high"}
            ),
            intervention_id=intervention_id,
            persist_profile_ledger=True,
        )
        if "profile_ledger" in list(outcome_record.get("persisted_layers") or []):
            try:
                await self.outcome_promotion_governor.synthesize_profile_ledger_learning(
                    user_id,
                    trigger_source="behavioral_outcome_tracker",
                )
            except Exception as exc:
                logger.warning(
                    "BehavioralOutcomeTracker: profile-ledger synthesis failed for user {}: {}",
                    user_id,
                    exc,
                )
        return outcome
