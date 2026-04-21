from __future__ import annotations

import pytest

from app.services.srl_phase_types import SRLPhase, get_transition_rule


@pytest.mark.parametrize(
    ("from_phase", "trigger", "expected"),
    [
        (SRLPhase.FORETHOUGHT, "task.started", SRLPhase.PERFORMANCE),
        (SRLPhase.FORETHOUGHT, "plan.created", SRLPhase.FORETHOUGHT),
        (SRLPhase.PERFORMANCE, "task.completed", SRLPhase.SELF_REFLECTION),
        (SRLPhase.PERFORMANCE, "task.abandoned", SRLPhase.SELF_REFLECTION),
        (SRLPhase.PERFORMANCE, "reflection.completed", SRLPhase.SELF_REFLECTION),
        (SRLPhase.PERFORMANCE, "plan_stall_detected", SRLPhase.SELF_REFLECTION),
        (SRLPhase.SELF_REFLECTION, "next_plan_draft", SRLPhase.FORETHOUGHT),
        (SRLPhase.SELF_REFLECTION, "user_start_new", SRLPhase.FORETHOUGHT),
        (SRLPhase.UNKNOWN, "inactive_timeout", SRLPhase.UNKNOWN),
    ],
)
def test_transition_matrix_accepts_registered_paths(from_phase, trigger, expected) -> None:
    rule = get_transition_rule(from_phase, trigger)
    assert rule is not None
    assert rule.allowed is True
    assert rule.to_phase == expected


@pytest.mark.parametrize(
    ("from_phase", "trigger"),
    [
        (SRLPhase.FORETHOUGHT, "task.feedback_submitted"),
        (SRLPhase.SELF_REFLECTION, "task.started"),
        (SRLPhase.PERFORMANCE, "user_start_new"),
    ],
)
def test_transition_matrix_rejects_illegal_paths(from_phase, trigger) -> None:
    rule = get_transition_rule(from_phase, trigger)
    assert rule is not None
    assert rule.allowed is False
