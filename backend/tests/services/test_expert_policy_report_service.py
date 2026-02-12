from datetime import UTC, datetime

from app.services.expert_policy_report_service import ExpertPolicyReportService


def test_policy_report_aggregate_contains_breakdowns() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    events = [
        {
            "event_type": "expert_selected",
            "data": {
                "expert_id": "math_agent",
                "policy_id": "expert_strategy_v2",
                "complexity_tier": "high",
                "task_type": "study_plan",
            },
        },
        {
            "event_type": "expert_invoked",
            "data": {
                "expert_id": "math_agent",
                "policy_id": "expert_strategy_v2",
                "complexity_tier": "high",
                "task_type": "study_plan",
            },
        },
        {
            "event_type": "expert_fallback",
            "data": {
                "reason": "reduce_expert_count_low_signal",
                "policy_id": "expert_strategy_v2",
                "complexity_tier": "high",
                "task_type": "study_plan",
            },
        },
        {
            "event_type": "user_feedback_bound",
            "data": {
                "workflow_id": "study_plan_workflow",
                "policy_id": "expert_strategy_v2",
                "task_type": "study_plan",
            },
        },
    ]
    report = ExpertPolicyReportService._aggregate(events=events, days=7, generated_at=now)

    assert report["totals"]["expert_selected"] == 1
    assert report["totals"]["expert_invoked"] == 1
    assert report["totals"]["expert_fallback"] == 1
    assert report["totals"]["user_feedback_bound"] == 1
    assert report["feedback_bindings"]["by_policy"]["expert_strategy_v2"] == 1
    assert report["breakdown"]["fallback_rate_by_policy"]["expert_strategy_v2"] == 1.0
    assert "policy_health" in report
    assert "recommendations" in report
    assert report["policy_health"]["expert_strategy_v2"]["status"] in {
        "healthy",
        "watch",
        "needs_tuning",
        "insufficient_data",
    }
