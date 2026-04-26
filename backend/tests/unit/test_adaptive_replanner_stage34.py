from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.orchestration.exam_sprint_policy import ExamSprintPolicyEngine, ExamSprintPolicyInput
from app.services.plan_progress_service import PlanHealthReport


@pytest.mark.asyncio
async def test_apply_incremental_adjustment_emits_visible_update_for_noop_patch() -> None:
    replanner = object.__new__(AdaptiveReplanner)
    report = PlanHealthReport(
        plan_id=uuid4(),
        user_id=uuid4(),
        status="active",
        severity="warning",
        reasons=["progress_lag"],
        metrics={"progress_rate": 0.2},
        requires_adjustment=True,
        recommended_action="adjust",
    )
    replanner.db = None
    replanner._card_bridge = None
    replanner.plan_state_service = SimpleNamespace(
        get_plan_state=AsyncMock(return_value=SimpleNamespace(facts={"adaptive_meta": {}}, constraints={})),
        upsert_plan_state=AsyncMock(),
    )
    replanner._calculate_adjustments = lambda *args, **kwargs: {"adaptive_adjustments": {"time_multiplier": 1.1}}
    replanner.plan_adjustment_applier = SimpleNamespace(
        apply_incremental_changes=AsyncMock(
            return_value=SimpleNamespace(
                applied=True,
                affected_task_ids=[],
                inserted_task_ids=[],
                hidden_task_ids=[],
                user_facing_summary=None,
            )
        )
    )
    replanner._enqueue_adaptation_update = AsyncMock()

    records = await replanner._apply_incremental_adjustment(report, trigger="task_feedback")

    assert records == []
    replanner._enqueue_adaptation_update.assert_awaited_once()
    kwargs = replanner._enqueue_adaptation_update.await_args.kwargs
    assert kwargs["update_type"] == "plan_adaptation_evaluated"


@pytest.mark.asyncio
async def test_compress_sprint_day_uses_behind_fail_safe() -> None:
    replanner = object.__new__(AdaptiveReplanner)
    seven_day_policy = ExamSprintPolicyEngine.build(
        ExamSprintPolicyInput(total_days=7, subject="计算机网络", daily_available_hours=2)
    ).to_dict()
    seven_day_policy["days_left"] = 5

    tasks = await replanner.compress_sprint_day(
        day_number=5,
        completion_rate=0.3,
        sprint_policy=seven_day_policy,
    )

    assert len(tasks) == 1
    task = tasks[0]
    assert task["task_kind"] == "compressed_recovery"
    assert task["compressed"] is True
    assert task["estimated_minutes"] <= 35
    assert task["optional_tasks"] == []
    assert "前一天完成率只有 30%" in task["compression_reason"]
    assert "下一天只保留 1 个核心任务和 1 个输出动作" in task["compression_reason"]


@pytest.mark.asyncio
async def test_compress_sprint_day_moves_task_away_from_calendar_conflict() -> None:
    replanner = object.__new__(AdaptiveReplanner)
    seven_day_policy = ExamSprintPolicyEngine.build(
        ExamSprintPolicyInput(total_days=7, subject="计算机网络", daily_available_hours=2)
    ).to_dict()
    seven_day_policy["days_left"] = 3

    tasks = await replanner.compress_sprint_day(
        day_number=5,
        completion_rate=0.4,
        sprint_policy=seven_day_policy,
        source_daily_spec={
            "day": 5,
            "title_focus": "TCP 流量控制",
            "scheduled_start_time": "14:00",
            "scheduled_end_time": "15:00",
        },
        calendar_context={
            "busy_events": [
                {
                    "title": "高数考试",
                    "start_time": "14:00",
                    "end_time": "15:30",
                }
            ]
        },
    )

    task = tasks[0]
    assert task["scheduled_start_time"] == "09:00"
    assert task["scheduled_end_time"] == "10:00"
    assert task["calendar_avoidance"]["applied"] is True
    assert "高数考试" in task["calendar_avoidance"]["conflicts"][0]["title"]


def test_should_compress_considers_same_day_class_conflict() -> None:
    assert AdaptiveReplanner.should_compress(
        completion_rate=0.75,
        days_left=3,
        source_daily_spec={
            "day": 1,
            "estimated_minutes": 70,
            "scheduled_start_time": "14:00",
            "scheduled_end_time": "15:10",
        },
        calendar_context={
            "busy_events": [
                {
                    "title": "下午上课",
                    "kind": "class",
                    "start_time": "14:00",
                    "end_time": "16:00",
                }
            ],
            "time_blocks_today": [{"start": "19:00", "end": "20:00"}],
        },
    ) is True
