"""Behavioral outcome tracking for adaptive interventions."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intervention_adaptive import BehavioralOutcome


class BehavioralOutcomeTracker:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        user_id: UUID,
        intervention_id: UUID,
        outcome_type: str,
        time_to_outcome: int,
        success: bool,
        context: Optional[Dict[str, Any]] = None,
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
        return outcome
