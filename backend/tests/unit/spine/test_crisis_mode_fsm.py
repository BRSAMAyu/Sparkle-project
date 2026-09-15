"""FV-19 crisis mode FSM coverage."""

from __future__ import annotations

import pytest

from app.signals.crisis_mode_fsm import CrisisModeFSM, CrisisSignals, CrisisState
from app.signals.exam_rescue_detector import ExamRescueDetector
from app.signals.policy_engine import PolicyEngine


def test_crisis_mode_fsm_transitions_through_all_states():
    fsm = CrisisModeFSM()

    warning = fsm.transition(
        current_state=CrisisState.NORMAL,
        signals=CrisisSignals(deadline_pressure="critical"),
    )
    assert warning.previous_state == CrisisState.NORMAL
    assert warning.state == CrisisState.WARNING

    crisis = fsm.transition(
        current_state=warning.state,
        signals=CrisisSignals(deadline_pressure="critical", knowledge_gap="major"),
    )
    assert crisis.previous_state == CrisisState.WARNING
    assert crisis.state == CrisisState.CRISIS
    assert crisis.policy_constraints["max_task_duration_min"] == 15
    assert crisis.policy_constraints["aurora_l3_proactive_allowed"] is False

    recovery = fsm.transition(
        current_state=crisis.state,
        signals=CrisisSignals(
            deadline_pressure="critical",
            knowledge_gap="major",
            user_declared_recovered=True,
        ),
    )
    assert recovery.previous_state == CrisisState.CRISIS
    assert recovery.state == CrisisState.RECOVERY
    assert recovery.exit_reason == "user_recovered"

    normal = fsm.transition(
        current_state=recovery.state,
        signals=CrisisSignals(deadline_pressure="high"),
    )
    assert normal.previous_state == CrisisState.RECOVERY
    assert normal.state == CrisisState.NORMAL


def test_crisis_mode_trigger_requires_deadline_and_one_secondary_signal():
    assert CrisisModeFSM.is_crisis_trigger(
        CrisisSignals(deadline_pressure="critical", knowledge_gap="major")
    )
    assert CrisisModeFSM.is_crisis_trigger(
        CrisisSignals(deadline_pressure="critical", fatigue="critical")
    )
    assert CrisisModeFSM.is_crisis_trigger(
        CrisisSignals(deadline_pressure="critical", stress="high")
    )
    assert not CrisisModeFSM.is_crisis_trigger(
        CrisisSignals(deadline_pressure="high", knowledge_gap="major")
    )
    assert not CrisisModeFSM.is_crisis_trigger(
        CrisisSignals(deadline_pressure="critical", knowledge_gap="moderate")
    )


def test_exam_rescue_detector_attaches_crisis_snapshot_and_signal():
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message(
        "3 天后计网考试，我零基础，压力大到崩溃了",
        user_id="u1",
    )

    assert snapshot is not None
    assert snapshot.detected_mode == "exam_rescue"
    assert snapshot.crisis_mode is not None
    assert snapshot.crisis_mode.state == CrisisState.CRISIS
    assert snapshot.crisis_mode.status_band_label == "危机模式中"

    signal = detector.to_crisis_actionable_signal(snapshot, user_id="u1", message_id="m1")
    assert signal is not None
    assert signal.state_key == "crisis_mode"
    assert signal.claim == "crisis_mode_active"
    assert "minimal_pass_retrieval" in signal.possible_effects

    default_signal = detector.to_actionable_signal(snapshot, user_id="u1", message_id="m1")
    assert default_signal is not None
    assert default_signal.state_key == "crisis_mode"
    assert default_signal.claim == "crisis_mode_active"


@pytest.mark.asyncio
async def test_policy_engine_enforces_crisis_mode_constraints():
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("明天期末，我零基础，救命", user_id="u1")
    assert snapshot is not None
    signal = detector.to_crisis_actionable_signal(snapshot, user_id="u1")
    assert signal is not None

    engine = PolicyEngine()
    result = await engine.evaluate(signal)
    assert result is not None
    decision, directive = result

    assert decision.primary_strategy == "enforce_crisis_mode"
    assert decision.risk_level == "critical"
    assert directive.hard_constraints["max_task_duration_min"] == 15
    assert directive.hard_constraints["avoid_new_chapter"] is True
    assert directive.hard_constraints["retrieval_mode"] == "minimal_pass"
    assert directive.hard_constraints["suppress_challenge_achievement_notifications"] is True
    assert directive.hard_constraints["aurora_l3_proactive_allowed"] is False

    retrieval = engine.build_retrieval_directive(decision, signal)
    assert retrieval is not None
    assert retrieval.retrieval_mode == "minimal_pass"
    assert retrieval.source_scope == "task_bound"

    plan = engine.build_plan_directive(decision, signal)
    assert plan is not None
    assert plan.constraints["max_task_duration_min"] == 15
    assert plan.constraints["disable_challenge_achievements"] is True

    ux = engine.build_ux_directive(decision, signal)
    assert ux is not None
    assert ux.status_band_state == "crisis_mode_active"
    assert ux.show_strategy_receipt is True
    assert ux.allow_full_aurora_wake is False
