from __future__ import annotations

from app.services.analytics.active_probe_policy import ActiveProbePolicy
from app.services.evidence.belief_state import BeliefState
from app.services.evidence.unified_evidence import EvidenceTarget


def _set_all_variances(state: BeliefState, variance: float) -> None:
    for target in (
        EvidenceTarget.EMOTIONAL_BLOCK,
        EvidenceTarget.TASK_AVERSION,
        EvidenceTarget.COGNITIVE_LOAD,
        EvidenceTarget.GOAL_CLARITY,
        EvidenceTarget.EXECUTION_CAPACITY,
        EvidenceTarget.METACOGNITION_ACCURACY,
        EvidenceTarget.SYSTEM_DISSATISFACTION,
    ):
        variable = state.get_variable(target)
        variable.variance = variance


def test_active_probe_policy_recommends_probe_for_high_uncertainty_low_margin() -> None:
    state = BeliefState(user_id="u1")
    _set_all_variances(state, 0.02)
    emotional = state.get_variable(EvidenceTarget.EMOTIONAL_BLOCK)
    emotional.mean = 0.55
    emotional.variance = 0.25

    decision = ActiveProbePolicy().decide(
        state,
        router_projection={
            "shadow_mode": "balanced",
            "support_pressure_score": 0.51,
            "execution_readiness_score": 0.49,
        },
    )

    assert decision.should_probe is True
    assert decision.target == "emotional_block"
    assert "positive_value_of_information" in decision.reasons


def test_active_probe_policy_declines_when_uncertainty_is_low_and_margin_is_high() -> None:
    state = BeliefState(user_id="u1")
    _set_all_variances(state, 0.02)
    emotional = state.get_variable(EvidenceTarget.EMOTIONAL_BLOCK)
    emotional.mean = 0.2
    emotional.variance = 0.02

    decision = ActiveProbePolicy().decide(
        state,
        router_projection={
            "shadow_mode": "execution_first",
            "support_pressure_score": 0.18,
            "execution_readiness_score": 0.82,
        },
    )

    assert decision.should_probe is False
    assert decision.target is None
