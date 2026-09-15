from __future__ import annotations

from app.orchestration.planning_workflow import PlanningWorkflowManager


def test_cold_start_context_preserves_goal_type_and_user_facing_baseline() -> None:
    manager = PlanningWorkflowManager(redis_client=False)
    collected: dict[str, object] = {}

    manager._update_onboarding_collected(collected, "我想做一个英语口语练习项目", 1)
    manager._update_onboarding_collected(collected, "两周后想能完成一次自我介绍，现在会一些", 2)
    manager._update_onboarding_collected(collected, "每天 45 分钟，周三没空", 3)

    cold_start = manager._build_cold_start_context(collected)

    assert cold_start["goal_type"] == "project"
    assert cold_start["knowledge_baseline"] == "已经学过一部分"
    assert cold_start["time_constraint_days"] == 14
    assert cold_start["daily_available_hours"] == 1
    assert cold_start["assumptions_correctable"] is True
    assert cold_start["completeness"] >= 0.6


def test_empty_onboarding_skip_context_is_safe_and_correctable() -> None:
    manager = PlanningWorkflowManager(redis_client=False)

    cold_start = manager._build_cold_start_context({})

    assert cold_start["goal_type"] == "learning"
    assert cold_start["time_constraint_days"] == 7
    assert cold_start["knowledge_baseline"] == ""
    assert cold_start["daily_available_hours"] == 0
    assert cold_start["completeness"] == 0.0
    assert cold_start["assumptions_correctable"] is True
