from __future__ import annotations

import pytest

from app.core.user_insight_state import BigFiveDimension


def test_confidence_cap_allows_exact_point_three() -> None:
    dim = BigFiveDimension(value=0.1, confidence=0.3, evidence_count=1, source="merged")
    assert dim.confidence == 0.3


def test_confidence_cap_rejects_point_three_one() -> None:
    with pytest.raises(ValueError):
        BigFiveDimension(value=0.1, confidence=0.31, evidence_count=1, source="merged")


def test_confidence_cap_allows_zero() -> None:
    dim = BigFiveDimension(value=0.0, confidence=0.0, evidence_count=0, source="coldstart")
    assert dim.confidence == 0.0


def test_confidence_cap_rejects_negative_confidence() -> None:
    with pytest.raises(ValueError):
        BigFiveDimension(value=0.1, confidence=-0.01, evidence_count=1, source="merged")
