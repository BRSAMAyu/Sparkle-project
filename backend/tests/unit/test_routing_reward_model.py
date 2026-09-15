from __future__ import annotations

from app.services.evidence import RewardCategory, RewardHorizon, RewardSignalType, RoutingRewardModel


def test_reward_model_task_completion_is_strong_positive_label() -> None:
    reward = RoutingRewardModel.from_task_outcome(
        {
            "event_type": "task.completed",
            "task_id": "t1",
            "completion_rate": 1.0,
            "estimated_minutes": 30,
            "actual_minutes": 25,
        },
        completed=True,
    )

    assert reward.signal_type == RewardSignalType.TASK_COMPLETED
    assert reward.reward_category == RewardCategory.TASK_OUTCOME
    assert reward.outcome_label == "task_completion"
    assert reward.total_reward > 0.9
    assert reward.to_trace_payload()["reward_category"] == "task_outcome"
    assert reward.to_trace_payload()["normalized_reward"] <= 1.0
    assert reward.to_trace_payload()["reward_scale"] == "category_local_v1"
    assert reward.evidence_strength == "strong"
    assert reward.horizon == RewardHorizon.SHORT


def test_reward_model_task_abandonment_is_strong_negative_label() -> None:
    reward = RoutingRewardModel.from_task_outcome(
        {"event_type": "task.abandoned", "task_id": "t1", "reason": "too_difficult"},
        completed=False,
    )

    assert reward.signal_type == RewardSignalType.TASK_ABANDONED
    assert reward.reward_category == RewardCategory.TASK_OUTCOME
    assert reward.outcome_label == "task_abandonment"
    assert reward.total_reward == -1.0
    assert reward.sustainability_cost < 0.0


def test_reward_model_chat_complaint_and_gratitude_are_weak_immediate_labels() -> None:
    complaint = RoutingRewardModel.from_chat_turn(gratitude=False, dissatisfaction=True)
    gratitude = RoutingRewardModel.from_chat_turn(gratitude=True, dissatisfaction=False)

    assert complaint is not None
    assert complaint.signal_type == RewardSignalType.EXPLICIT_COMPLAINT
    assert complaint.reward_category == RewardCategory.CHAT_FEEDBACK
    assert complaint.total_reward < 0
    assert gratitude is not None
    assert gratitude.signal_type == RewardSignalType.EXPLICIT_GRATITUDE
    assert gratitude.reward_category == RewardCategory.CHAT_FEEDBACK
    assert gratitude.total_reward > 0


def test_reward_model_unknown_is_censored_not_zero_success() -> None:
    reward = RoutingRewardModel.unknown()

    assert reward.is_censored is True
    assert reward.reward_category == RewardCategory.UNKNOWN
    assert reward.confidence == 0.0
    assert reward.horizon == RewardHorizon.CENSORED


def test_reward_model_weights_completion_by_intrinsic_difficulty() -> None:
    micro = RoutingRewardModel.from_task_outcome(
        {"event_type": "task.completed", "task_id": "micro", "completion_rate": 1.0, "intrinsic_difficulty": 0.1},
        completed=True,
    )
    hard = RoutingRewardModel.from_task_outcome(
        {"event_type": "task.completed", "task_id": "hard", "completion_rate": 1.0, "intrinsic_difficulty": 0.9},
        completed=True,
    )

    assert micro.total_reward < hard.total_reward
    assert micro.to_trace_payload()["difficulty_weighted_reward"] < hard.to_trace_payload()["difficulty_weighted_reward"]
