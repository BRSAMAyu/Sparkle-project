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
