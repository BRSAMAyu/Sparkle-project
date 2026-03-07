from uuid import uuid4

from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.plan_progress_service import PlanHealthReport


def test_build_adjustment_record_prefers_hard_task_template() -> None:
    replanner = object.__new__(AdaptiveReplanner)
    report = PlanHealthReport(
        plan_id=uuid4(),
        user_id=uuid4(),
        status="active",
        severity="warning",
        reasons=["difficulty_too_hard", "time_overrun"],
        metrics={
            "overrun_count": 3,
            "feedback_stats": {"too_difficult": 3},
        },
        requires_adjustment=True,
        recommended_action="adjust",
    )

    record = replanner._build_adjustment_record(
        report,
        {"adaptive_adjustments": {"difficulty_shift": -0.1, "time_multiplier": 1.15}},
        "too_difficult",
    )

    assert record.user_facing_message == "我发现你最近的任务偏难了，帮你调轻了一些。"
    assert "降低任务启动门槛" in record.expected_effect
