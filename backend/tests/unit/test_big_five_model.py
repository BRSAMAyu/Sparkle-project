from __future__ import annotations

import pytest

from app.core.user_insight_state import BigFiveDimension, BigFiveTraits, UserInsightState


def test_big_five_dimension_accepts_boundary_values() -> None:
    dim = BigFiveDimension(value=-1.0, confidence=0.3, evidence_count=2, source="coldstart")
    assert dim.value == -1.0
    assert dim.confidence == 0.3


def test_big_five_dimension_rejects_confidence_above_cap() -> None:
    with pytest.raises(ValueError, match="trait confidence"):
        BigFiveDimension(value=0.1, confidence=0.31, evidence_count=1, source="merged")


def test_big_five_dimension_rejects_value_out_of_range() -> None:
    with pytest.raises(ValueError, match="trait value"):
        BigFiveDimension(value=1.2, confidence=0.1, evidence_count=1, source="coldstart")


def test_big_five_dimension_rejects_negative_evidence_count() -> None:
    with pytest.raises(ValueError, match="evidence_count"):
        BigFiveDimension(value=0.1, confidence=0.1, evidence_count=-1, source="coldstart")


def test_big_five_traits_summary_filters_by_confidence() -> None:
    traits = BigFiveTraits(
        openness=BigFiveDimension(value=0.3, confidence=0.09, evidence_count=1, source="coldstart"),
        conscientiousness=BigFiveDimension(value=0.4, confidence=0.12, evidence_count=2, source="merged"),
    )

    assert traits.summary(min_confidence=0.1) == [
        {
            "dim": "conscientiousness",
            "value": 0.4,
            "confidence": 0.12,
            "source": "merged",
        }
    ]


def test_user_insight_state_includes_traits_prior_in_legacy_projection() -> None:
    state = UserInsightState(
        traits_prior=BigFiveTraits(
            agreeableness=BigFiveDimension(value=0.2, confidence=0.15, evidence_count=3, source="merged")
        ),
        traits_coldstart_completed_at="2026-04-21T10:00:00",
    )

    projection = state.to_legacy_projection()

    assert projection["traits_prior"]["agreeableness"]["confidence"] == 0.15
    assert projection["traits_coldstart_completed_at"] == "2026-04-21T10:00:00"
