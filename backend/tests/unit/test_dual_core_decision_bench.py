from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from app.services.analytics.dual_core_decision_bench import (
    EVIDENCE_BEHAVIORAL_SIGNAL,
    EVIDENCE_EXPLICIT_FEEDBACK,
    FAILURE_LABEL,
    SUCCESS_LABEL,
    classify_route_history_truth,
    conservative_shadow_mode,
)


def _record(**overrides):
    base = {
        "decision_id": uuid4(),
        "decision_type": "execution_first",
        "decision_payload": {"mode": "execution_first", "signal_scores": {"goal_clarity": 0.9}},
        "decided_at": datetime(2026, 5, 15, 12, 0, 0),
        "outcome": None,
        "outcome_type": None,
        "outcome_timestamp": None,
        "outcome_collected_at": None,
        "source_state_v2": {},
        "source_state_v2_key": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_truth_matrix_marks_user_correction_as_explicit_failure() -> None:
    truth = classify_route_history_truth(
        _record(
            outcome="user_correction",
            outcome_type="user_correction",
            outcome_timestamp=datetime(2026, 5, 15, 12, 3, 0),
        )
    )

    assert truth.label == FAILURE_LABEL
    assert truth.evidence_level == EVIDENCE_EXPLICIT_FEEDBACK
    assert truth.latency_seconds == 180


def test_truth_matrix_marks_task_completion_as_behavioral_success() -> None:
    truth = classify_route_history_truth(
        _record(
            decision_type="cognitive_first",
            decision_payload={"mode": "cognitive_first"},
            outcome="task_completion",
            outcome_type="task_completion",
            outcome_timestamp=datetime(2026, 5, 15, 12, 10, 0),
        )
    )

    assert truth.label == SUCCESS_LABEL
    assert truth.evidence_level == EVIDENCE_BEHAVIORAL_SIGNAL
    assert "cognitive_first_eventual_progress" in truth.reason


def test_truth_matrix_uses_collected_at_when_timestamp_missing() -> None:
    truth = classify_route_history_truth(
        _record(
            outcome="plan_success",
            outcome_type="plan_success",
            outcome_collected_at=datetime(2026, 5, 15, 12, 1, 30),
        )
    )

    assert truth.label == SUCCESS_LABEL
    assert truth.latency_seconds == 90


def test_conservative_shadow_downgrades_accumulated_weak_risk_only() -> None:
    shadow_mode, meta = conservative_shadow_mode(
        "execution_first",
        {
            "goal_clarity": 0.9,
            "emotional_block": 0.49,
            "procrastination": 0.54,
            "cognitive_load": 0.54,
        },
    )

    assert shadow_mode == "balanced"
    assert meta["shadow_reason"] == "accumulated_weak_support_pressure"


def test_conservative_shadow_preserves_cognitive_first_hard_guard() -> None:
    shadow_mode, meta = conservative_shadow_mode(
        "cognitive_first",
        {
            "goal_clarity": 0.9,
            "emotional_block": 0.0,
            "procrastination": 0.0,
            "cognitive_load": 0.0,
        },
    )

    assert shadow_mode == "cognitive_first"
    assert meta["shadow_reason"] == "preserve_current_cognitive_hard_guard"
