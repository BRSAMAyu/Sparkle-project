from app.signals.intervention_episode import ContextSignature
from app.signals.safe_experiment_platform import SafeBanditController
from app.signals.safe_experiment_promotion_gate import evaluate_safe_experiment_promotion


class _ExperimentRecord:
    experiment_key = "spexp_test"
    status = "canary"
    current_episodes = 50
    min_episodes = 50
    distinct_users = [f"user-{i}" for i in range(15)]
    min_distinct_users = 15
    outcome_history = [
        {
            "trust": {"explicit_negative_feedback": False, "receipt_dismissed": False},
            "load": {"cognitive_load_after": "low", "affective_pressure_after": "calm"},
            "agency": {"user_corrected_system": False},
        }
    ]


def test_safe_bandit_blocks_d0_exam_day_to_primary_action():
    bandit = SafeBanditController()
    result = bandit.select_arm(
        ["primary", "experimental"],
        context=ContextSignature(deadline_phase="D-0"),
        risk_level="low",
    )

    assert result["selected_action"] == "primary"
    assert result["reason"] == "D0_exam_day"
    assert result["exploration_allowed"] is False
    assert result["blocked"] is True


def test_safe_bandit_blocks_user_opt_out_before_exploration():
    bandit = SafeBanditController()
    result = bandit.select_arm(
        ["primary", "experimental"],
        context=ContextSignature(),
        risk_level="low",
        user_opted_out=True,
    )

    assert result["selected_action"] == "primary"
    assert result["reason"] == "user_opted_out_experiments"
    assert result["exploration_allowed"] is False


def test_promotion_gate_emits_release_approval_candidate_for_clean_canary():
    result = evaluate_safe_experiment_promotion(_ExperimentRecord())

    assert result.eligible is True
    assert result.target_status == "safe_live"
    assert result.candidate_payload is not None
    assert result.candidate_payload["requires_release_approval"] is True
