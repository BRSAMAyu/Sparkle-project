from __future__ import annotations

from pathlib import Path

import pytest

from app.learning.persistent_bayesian_sqam import (
    SQAM_DISCRIMINATIVE_POWER_THRESHOLD,
    SQAM_INFORMATION_DENSITY_THRESHOLD,
    SQAM_SAFETY_MARGIN_THRESHOLD,
    SQAM_STABILITY_THRESHOLD,
    load_sqam_fixture,
    run_sqam_fixture,
)


_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "persistent_bayesian_stage14_scale_fixture.json"


@pytest.mark.asyncio
async def test_stage14_scale_fixture_meets_size_floor_and_stays_wire_ready() -> None:
    fixture = load_sqam_fixture(_FIXTURE_PATH)
    scorecard = await run_sqam_fixture(fixture)

    assert scorecard.total_observations == 220
    assert scorecard.observed_pairs == 22
    assert scorecard.supported_pairs == 22
    assert scorecard.labeled_source_states == 11

    assert scorecard.information_density >= SQAM_INFORMATION_DENSITY_THRESHOLD
    assert scorecard.stability >= SQAM_STABILITY_THRESHOLD
    assert scorecard.discriminative_power >= SQAM_DISCRIMINATIVE_POWER_THRESHOLD
    assert scorecard.safety_margin >= SQAM_SAFETY_MARGIN_THRESHOLD
    assert scorecard.is_wire_ready() is True

    assert {decision.source for decision in scorecard.top_decisions} == {
        "state_plan",
        "state_task",
        "state_focus",
        "state_growth",
        "state_query",
        "state_knowledge",
        "state_review",
        "state_research",
        "state_memory",
        "state_cognitive",
        "state_general",
    }


@pytest.mark.asyncio
async def test_stage14_scale_fixture_keeps_false_confident_rate_at_zero() -> None:
    fixture = load_sqam_fixture(_FIXTURE_PATH)
    scorecard = await run_sqam_fixture(fixture)

    assert scorecard.high_confidence_decisions == 11
    assert scorecard.false_confident_decisions == 0
    assert all(decision.probability >= 0.8 for decision in scorecard.top_decisions)
    assert all(decision.effective_outcome is True for decision in scorecard.top_decisions)
