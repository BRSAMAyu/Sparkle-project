"""Scaffolding state machine for adaptive interventions."""

from __future__ import annotations

from datetime import timezone, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intervention_adaptive import ScaffoldingState
from app.scaffolding.capability_tracker import CapabilityTracker


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ScaffoldingFSM:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_state(self, user_id: UUID) -> ScaffoldingState:
        result = await self.db.execute(
            select(ScaffoldingState).where(ScaffoldingState.user_id == user_id)
        )
        state = result.scalar_one_or_none()
        if state:
            return state

        state = ScaffoldingState(
            user_id=user_id,
            capability_level=0.5,
            support_level=3,
            current_zone="flow",
            consecutive_successes=0,
            consecutive_failures=0,
            history=[],
        )
        self.db.add(state)
        await self.db.flush()
        return state

    async def register_intervention(
        self,
        user_id: UUID,
        intervention_id: UUID,
        intent_type: str,
        template_variant_id: str | None,
    ) -> ScaffoldingState:
        state = await self.get_state(user_id)
        history = list(state.history or [])
        history.append(
            {
                "intervention_id": str(intervention_id),
                "intent_type": intent_type,
                "template_variant_id": template_variant_id,
                "timestamp": _utcnow().isoformat(),
            }
        )
        state.history = history[-10:]
        state.template_variant_id = template_variant_id
        state.last_intervention_timestamp = _utcnow()
        await self.db.flush()
        return state

    async def apply_feedback(
        self,
        user_id: UUID,
        success: bool,
        feedback: str | None = None,
        weight: float = 1.0,
    ) -> ScaffoldingState:
        state = await self.get_state(user_id)
        tracker = CapabilityTracker(state.capability_level)
        state.capability_level = tracker.update(success=success, weight=weight)
        state.current_zone = tracker.zone()

        if success:
            state.consecutive_successes += 1
            state.consecutive_failures = 0
        else:
            state.consecutive_failures += 1
            state.consecutive_successes = 0

        if state.consecutive_successes >= 3:
            state.support_level = max(1, state.support_level - 1)
            state.consecutive_successes = 0
        if state.consecutive_failures >= 2:
            state.support_level = min(4, state.support_level + 1)
            state.consecutive_failures = 0

        state.updated_at = _utcnow()
        await self.db.flush()
        return state

    def snapshot(self, state: ScaffoldingState) -> dict[str, Any]:
        return {
            "capability_level": state.capability_level,
            "support_level": state.support_level,
            "current_zone": state.current_zone,
            "consecutive_successes": state.consecutive_successes,
            "consecutive_failures": state.consecutive_failures,
            "template_variant_id": state.template_variant_id,
            "last_intervention_timestamp": state.last_intervention_timestamp.isoformat()
            if state.last_intervention_timestamp
            else None,
        }
