"""Scaffolding state machine for adaptive interventions."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import (
    METACOG_SCAFFOLDING_COMBINE_TOTAL,
    SRL_SCAFFOLDING_ADJUSTED_TOTAL,
)
from app.models.intervention_adaptive import ScaffoldingState
from app.models.user_preferences import UserPreferencesCenter
from app.scaffolding.capability_tracker import CapabilityTracker
from app.services.srl_phase_traits import (
    derive_initial_support_level,
    derive_reflection_prompt_style,
)
from app.services.srl_phase_types import SRLPhase
from app.state_aggregator.schema import MetacognitionProfileSummaryValue


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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
        metacognition_profile: (
            MetacognitionProfileSummaryValue | dict[str, Any] | None
        ) = None,
        consume_mode: str = "live",
    ) -> dict[str, Any]:
        phase = self.get_srl_phase_hint(phase_value)
        mode = str(consume_mode or "off").strip().lower()
        srl_delta = (
            1.0 if phase in {SRLPhase.FORETHOUGHT, SRLPhase.SELF_REFLECTION} else 0.0
        )
        metacog_delta = self.get_metacognition_delta(metacognition_profile)
        final_delta = self.combine_support_delta(srl_delta, metacog_delta)
        applied = final_delta != 0 and mode == "live"
        effective_level = (
            max(1.0, min(4.0, float(state.support_level) + final_delta))
            if applied
            else float(state.support_level)
        )
        template_support_level = max(1, min(4, int(round(effective_level))))
        if srl_delta > 0:
            SRL_SCAFFOLDING_ADJUSTED_TOTAL.labels(
                phase=phase.value,
                mode=mode,
                applied="true" if applied else "false",
            ).inc()
        combine_state = self._combine_state(srl_delta, metacog_delta)
        METACOG_SCAFFOLDING_COMBINE_TOTAL.labels(combine_state=combine_state).inc()
        return {
            "phase": phase,
            "base_support_level": float(state.support_level),
            "support_delta": final_delta,
            "support_level": effective_level,
            "template_support_level": template_support_level,
            "adjustment_applied": applied,
            "srl_support_delta": srl_delta,
            "metacognition_support_delta": metacog_delta,
            "combine_state": combine_state,
        }

    def snapshot(
        self,
        state: ScaffoldingState,
        *,
        phase_value: SRLPhase | str | None = None,
        metacognition_profile: (
            MetacognitionProfileSummaryValue | dict[str, Any] | None
        ) = None,
        consume_mode: str = "off",
        reflection_prompt_style: str = "default",
    ) -> dict[str, Any]:
        support = self.resolve_support_level(
            state,
            phase_value=phase_value,
            metacognition_profile=metacognition_profile,
            consume_mode=consume_mode,
        )
        return {
            "capability_level": state.capability_level,
            "support_level": support["support_level"],
            "base_support_level": support["base_support_level"],
            "template_support_level": support["template_support_level"],
            "current_zone": state.current_zone,
            "consecutive_successes": state.consecutive_successes,
            "consecutive_failures": state.consecutive_failures,
            "template_variant_id": state.template_variant_id,
            "srl_phase": support["phase"].value,
            "srl_adjustment_applied": support["adjustment_applied"],
            "srl_support_delta": support["srl_support_delta"],
            "metacognition_support_delta": support["metacognition_support_delta"],
            "combined_support_delta": support["support_delta"],
            "combine_state": support["combine_state"],
            "reflection_prompt_style": reflection_prompt_style,
            "last_intervention_timestamp": (
                state.last_intervention_timestamp.isoformat()
                if state.last_intervention_timestamp
                else None
            ),
        }

    @staticmethod
    def combine_support_delta(srl_delta: float, metacog_delta: float) -> float:
        if srl_delta >= 1.0:
            return 1.0
        if srl_delta <= -1.0:
            return -1.0
        if metacog_delta >= 0.5:
            return 0.5
        if metacog_delta <= -0.5:
            return -0.5
        return 0.0

    def get_metacognition_delta(
        self,
        metacognition_profile: MetacognitionProfileSummaryValue | dict[str, Any] | None,
    ) -> float:
        if metacognition_profile is None:
            return 0.0

        items: list[dict[str, Any]] = []
        if isinstance(metacognition_profile, MetacognitionProfileSummaryValue):
            items = [
                {
                    "dim": item.dim,
                    "bias_mean": item.bias_mean,
                    "sample_size": item.sample_size,
                }
                for item in metacognition_profile.items
            ]
        elif isinstance(metacognition_profile, dict):
            items = list(metacognition_profile.get("items") or [])

        candidates: list[tuple[float, float]] = []
        for item in items:
            dim = str(item.get("dim") or "")
            bias_mean = float(item.get("bias_mean") or 0.0)
            if abs(bias_mean) < 0.5:
                continue
            if dim == "time_estimation_bias":
                candidates.append((0.5 if bias_mean > 0 else -0.5, abs(bias_mean)))
            elif dim in {"completion_bias", "mastery_bias"}:
                candidates.append((0.5 if bias_mean < 0 else -0.5, abs(bias_mean)))
        if not candidates:
            return 0.0

        candidates.sort(key=lambda item: (item[1], item[0]), reverse=True)
        return candidates[0][0]

    @staticmethod
    def _combine_state(srl_delta: float, metacog_delta: float) -> str:
        if srl_delta != 0:
            return "srl_only"
        if metacog_delta != 0:
            return "metacog_only"
        return "both_zero"

    async def _load_traits_prior(self, user_id: UUID) -> dict[str, Any]:
        result = await self.db.execute(
            select(UserPreferencesCenter.traits_prior).where(
                UserPreferencesCenter.user_id == user_id
            )
        )
        traits_prior = result.scalar_one_or_none()
        return dict(traits_prior or {})
