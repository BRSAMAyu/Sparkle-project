"""Scaffolding state machine for adaptive interventions."""

from __future__ import annotations

from datetime import timezone, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import SRL_SCAFFOLDING_ADJUSTED_TOTAL
from app.models.intervention_adaptive import ScaffoldingState
from app.models.user_preferences import UserPreferencesCenter
from app.scaffolding.capability_tracker import CapabilityTracker
from app.services.srl_phase_traits import derive_initial_support_level, derive_reflection_prompt_style
from app.services.srl_phase_types import SRLPhase


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

        traits_prior = await self._load_traits_prior(user_id)

        state = ScaffoldingState(
            user_id=user_id,
            capability_level=0.5,
            support_level=derive_initial_support_level(traits_prior),
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
        srl_phase: str | None = None,
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
        history = list(state.history or [])
        history.append(
            {
                "type": "feedback",
                "success": success,
                "feedback": feedback,
                "weight": weight,
                "srl_phase": srl_phase,
                "timestamp": _utcnow().isoformat(),
            }
        )
        state.history = history[-10:]
        await self.db.flush()
        return state

    async def get_trait_scaffolding_preferences(self, user_id: UUID) -> dict[str, Any]:
        traits_prior = await self._load_traits_prior(user_id)
        return {
            "initial_support_level": derive_initial_support_level(traits_prior),
            "reflection_prompt_style": derive_reflection_prompt_style(traits_prior),
        }

    def get_srl_phase_hint(self, phase_value: SRLPhase | str | None) -> SRLPhase:
        if isinstance(phase_value, SRLPhase):
            return phase_value
        if phase_value is None:
            return SRLPhase.UNKNOWN
        try:
            return SRLPhase(str(phase_value).strip().upper())
        except ValueError:
            return SRLPhase.UNKNOWN

    def resolve_support_level(
        self,
        state: ScaffoldingState,
        *,
        phase_value: SRLPhase | str | None = None,
        consume_mode: str = "live",
    ) -> dict[str, Any]:
        phase = self.get_srl_phase_hint(phase_value)
        mode = str(consume_mode or "off").strip().lower()
        delta = 1 if phase in {SRLPhase.FORETHOUGHT, SRLPhase.SELF_REFLECTION} else 0
        applied = delta > 0 and mode == "live"
        effective_level = min(4, state.support_level + delta) if applied else state.support_level
        if delta > 0:
            SRL_SCAFFOLDING_ADJUSTED_TOTAL.labels(
                phase=phase.value,
                mode=mode,
                applied="true" if applied else "false",
            ).inc()
        return {
            "phase": phase,
            "base_support_level": state.support_level,
            "support_delta": delta,
            "support_level": effective_level,
            "adjustment_applied": applied,
        }

    def snapshot(
        self,
        state: ScaffoldingState,
        *,
        phase_value: SRLPhase | str | None = None,
        consume_mode: str = "off",
        reflection_prompt_style: str = "default",
    ) -> dict[str, Any]:
        support = self.resolve_support_level(
            state,
            phase_value=phase_value,
            consume_mode=consume_mode,
        )
        return {
            "capability_level": state.capability_level,
            "support_level": support["support_level"],
            "base_support_level": support["base_support_level"],
            "current_zone": state.current_zone,
            "consecutive_successes": state.consecutive_successes,
            "consecutive_failures": state.consecutive_failures,
            "template_variant_id": state.template_variant_id,
            "srl_phase": support["phase"].value,
            "srl_adjustment_applied": support["adjustment_applied"],
            "srl_support_delta": support["support_delta"],
            "reflection_prompt_style": reflection_prompt_style,
            "last_intervention_timestamp": state.last_intervention_timestamp.isoformat()
            if state.last_intervention_timestamp
            else None,
        }

    async def _load_traits_prior(self, user_id: UUID) -> dict[str, Any]:
        result = await self.db.execute(
            select(UserPreferencesCenter.traits_prior).where(UserPreferencesCenter.user_id == user_id)
        )
        traits_prior = result.scalar_one_or_none()
        return dict(traits_prior or {})
