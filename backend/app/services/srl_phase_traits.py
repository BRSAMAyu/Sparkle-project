from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.user_insight_state import BigFiveDimension, BigFiveTraits
from app.services.srl_phase_types import SRLPhase, SRLPhaseState


def _coerce_traits(traits_prior: BigFiveTraits | dict[str, Any] | None) -> BigFiveTraits:
    if isinstance(traits_prior, BigFiveTraits):
        return traits_prior
    if isinstance(traits_prior, dict):
        return BigFiveTraits.model_validate(traits_prior)
    return BigFiveTraits()


def _dimension(
    traits_prior: BigFiveTraits | dict[str, Any] | None,
    dim: str,
) -> BigFiveDimension | None:
    traits = _coerce_traits(traits_prior)
    return getattr(traits, dim, None)


def derive_coldstart_phase_from_traits(
    *,
    user_id: UUID,
    traits_prior: BigFiveTraits | dict[str, Any] | None,
) -> SRLPhaseState:
    conscientiousness = _dimension(traits_prior, "conscientiousness")
    if conscientiousness is not None and conscientiousness.confidence >= 0.1 and conscientiousness.value >= 0.6:
        return SRLPhaseState(
            user_id=user_id,
            current_phase=SRLPhase.FORETHOUGHT,
            previous_phase=None,
            transition_evidence_ids=["traits:conscientiousness"],
            confidence=min(0.3, round(0.12 + float(conscientiousness.confidence), 4)),
            source="trait_primed",
        )
    return SRLPhaseState(
        user_id=user_id,
        current_phase=SRLPhase.UNKNOWN,
        previous_phase=None,
        transition_evidence_ids=[],
        confidence=0.0,
        source="default",
    )


def derive_initial_support_level(traits_prior: BigFiveTraits | dict[str, Any] | None) -> int:
    conscientiousness = _dimension(traits_prior, "conscientiousness")
    if conscientiousness is None or conscientiousness.confidence < 0.1:
        return 3
    if conscientiousness.value >= 0.6:
        return 2
    if conscientiousness.value <= -0.2:
        return 4
    return 3


def derive_reflection_prompt_style(traits_prior: BigFiveTraits | dict[str, Any] | None) -> str:
    openness = _dimension(traits_prior, "openness")
    if openness is None or openness.confidence < 0.1:
        return "default"
    if openness.value >= 0.4:
        return "alternative_exploration"
    if openness.value <= -0.2:
        return "single_path_deepening"
    return "default"
