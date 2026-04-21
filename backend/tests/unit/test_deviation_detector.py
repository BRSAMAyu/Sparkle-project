from __future__ import annotations

from datetime import datetime

from app.schemas.foresight import AttractorState
from app.services.foresight_deviation_service import DeviationDetector


def _state(
    *,
    dim: str = "study_pace",
    baseline: float = 1.0,
    variability: float = 0.2,
    recovery_rate: float = 0.1,
    confidence: float = 0.8,
) -> AttractorState:
    return AttractorState(
        dim=dim,
        baseline=baseline,
        variability=variability,
        recovery_rate=recovery_rate,
        confidence=confidence,
        updated_at=datetime(2026, 4, 21, 9, 0, 0),
    )


def test_deviation_detector_flags_above_threshold() -> None:
    deviations = DeviationDetector().detect(
        attractors={"study_pace": _state()},
        current_observations={"study_pace": 1.5},
    )

    assert len(deviations) == 1
    assert deviations[0].direction == "above"


def test_deviation_detector_flags_below_threshold() -> None:
    deviations = DeviationDetector().detect(
        attractors={"study_pace": _state()},
        current_observations={"study_pace": 0.6},
    )

    assert len(deviations) == 1
    assert deviations[0].direction == "below"


def test_deviation_detector_ignores_small_z_score() -> None:
    deviations = DeviationDetector().detect(
        attractors={"study_pace": _state()},
        current_observations={"study_pace": 1.2},
    )

    assert deviations == ()


def test_deviation_detector_uses_minimum_variability_guard() -> None:
    deviations = DeviationDetector().detect(
        attractors={"study_pace": _state(variability=0.0)},
        current_observations={"study_pace": 1.2},
    )

    assert len(deviations) == 1
    assert deviations[0].z_score >= 3.9


def test_deviation_detector_projects_toward_baseline_from_above() -> None:
    deviations = DeviationDetector().detect(
        attractors={"study_pace": _state(recovery_rate=0.15)},
        current_observations={"study_pace": 1.8},
    )

    assert len(deviations) == 1
    assert deviations[0].projected_3d == 1.35


def test_deviation_detector_preserves_attractor_confidence() -> None:
    deviations = DeviationDetector().detect(
        attractors={"study_pace": _state(confidence=0.62)},
        current_observations={"study_pace": 1.5},
    )

    assert len(deviations) == 1
    assert deviations[0].confidence == 0.62
