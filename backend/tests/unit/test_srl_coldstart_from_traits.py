from __future__ import annotations

from uuid import uuid4

from app.core.user_insight_state import BigFiveDimension, BigFiveTraits
from app.services.srl_phase_traits import (
    derive_coldstart_phase_from_traits,
    derive_initial_support_level,
    derive_reflection_prompt_style,
)
from app.services.srl_phase_types import SRLPhase


def test_coldstart_high_conscientiousness_prefers_forethought() -> None:
    traits = BigFiveTraits(
        conscientiousness=BigFiveDimension(value=0.7, confidence=0.2, source="merged"),
    )
    state = derive_coldstart_phase_from_traits(user_id=uuid4(), traits_prior=traits)
    assert state.current_phase == SRLPhase.FORETHOUGHT
    assert state.source == "trait_primed"
    assert state.confidence <= 0.3


def test_coldstart_missing_traits_falls_back_to_unknown() -> None:
    state = derive_coldstart_phase_from_traits(user_id=uuid4(), traits_prior=BigFiveTraits())
    assert state.current_phase == SRLPhase.UNKNOWN
    assert state.source == "default"


def test_traits_map_into_support_and_reflection_style() -> None:
    traits = BigFiveTraits(
        conscientiousness=BigFiveDimension(value=-0.4, confidence=0.2, source="merged"),
        openness=BigFiveDimension(value=0.5, confidence=0.2, source="merged"),
    )
    assert derive_initial_support_level(traits) == 4
    assert derive_reflection_prompt_style(traits) == "alternative_exploration"
