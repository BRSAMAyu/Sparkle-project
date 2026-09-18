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
    assert (
        AdaptiveReplanner.should_compress(
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
        )
        is True
    )


def test_calendar_capacity_shortfall_becomes_lightweight_adjustment() -> None:
    report = PlanHealthReport(
        plan_id=uuid4(),
        user_id=uuid4(),
        status="active",
        severity="critical",
        reasons=["progress_lag"],
        metrics={"progress_rate": 0.35},
        requires_adjustment=True,
        recommended_action="replan",
    )

    adjusted = AdaptiveReplanner._apply_calendar_capacity_to_report(
        report,
        {
            "required_daily_minutes": 180,
            "available_minutes_by_date": {
                "2026-05-01": 90,
                "2026-05-02": 80,
                "2026-05-03": 100,
            },
            "capacity_summary": {
                "next_3_days_available_minutes": 270,
                "next_3_days_required_minutes": 540,
                "planning_intensity_hint": "lower",
            },
        },
    )

    assert adjusted.severity == "warning"
    assert adjusted.recommended_action == "adjust"
    assert "calendar_capacity_shortfall" in adjusted.reasons
    assert adjusted.metrics["calendar_capacity"]["next_3_days_available_minutes"] == 270

    replanner = object.__new__(AdaptiveReplanner)
    adjustments = replanner._calculate_adjustments({}, adjusted, None)
    assert adjustments["adaptive_adjustments"]["calendar_aware"] is True
    assert adjustments["adaptive_adjustments"]["task_density_mode"] == "calendar_aware_reduced"

    record = replanner._build_adjustment_record(adjusted, adjustments, feedback_category=None)
    assert "日程时间不够" in record.user_facing_message


# ===========================================================================
# P2-2 (sysrev round1): adjustment cooldown arms only after task-level landing
# ===========================================================================


def _build_adjustment_replanner(applier_result) -> AdaptiveReplanner:
    replanner = object.__new__(AdaptiveReplanner)
    replanner.db = None
    replanner._card_bridge = None
    replanner.plan_state_service = SimpleNamespace(
        get_plan_state=AsyncMock(return_value=SimpleNamespace(facts={"adaptive_meta": {}}, constraints={})),
        upsert_plan_state=AsyncMock(),
    )
    replanner._calculate_adjustments = lambda *args, **kwargs: {"adaptive_adjustments": {"time_multiplier": 1.1}}
    replanner.plan_adjustment_applier = SimpleNamespace(
        apply_incremental_changes=AsyncMock(return_value=applier_result)
    )
    replanner._enqueue_adaptation_update = AsyncMock()
    return replanner


def _noop_patch_result() -> SimpleNamespace:
    return SimpleNamespace(
        applied=True,
        affected_task_ids=[],
        inserted_task_ids=[],
        hidden_task_ids=[],
        user_facing_summary=None,
    )


def _landed_patch_result() -> SimpleNamespace:
    return SimpleNamespace(
        applied=True,
        affected_task_ids=[uuid4()],
        inserted_task_ids=[],
        hidden_task_ids=[],
        user_facing_summary="微调完成",
    )


@pytest.mark.asyncio
async def test_noop_patch_does_not_arm_adjustment_cooldown():
    """Zero task-level changes must not consume the 2h adjustment cooldown."""
    replanner = _build_adjustment_replanner(_noop_patch_result())

    records = await replanner._apply_incremental_adjustment(_noop_patch_report(), trigger="task_feedback")

    assert records == []
    for call in replanner.plan_state_service.upsert_plan_state.await_args_list:
        meta = call.kwargs["patch"]["facts"]["adaptive_meta"]
        assert "last_adjustment_at" not in meta, "cooldown armed despite zero task-level changes"


@pytest.mark.asyncio
async def test_landed_patch_arms_adjustment_cooldown():
    """A landed task-level adjustment writes last_adjustment_at (cooldown armed)."""
    replanner = _build_adjustment_replanner(_landed_patch_result())

    records = await replanner._apply_incremental_adjustment(_noop_patch_report(), trigger="task_feedback")

    assert len(records) == 1
    armed = [
        call
        for call in replanner.plan_state_service.upsert_plan_state.await_args_list
        if "last_adjustment_at" in call.kwargs["patch"]["facts"]["adaptive_meta"]
    ]
    assert armed, "cooldown not armed after a landed task-level adjustment"
    assert armed[-1].kwargs["patch"]["facts"]["adaptive_meta"]["last_trigger"] == "task_feedback"


def _noop_patch_report() -> PlanHealthReport:
    return PlanHealthReport(
        plan_id=uuid4(),
        user_id=uuid4(),
        status="active",
        severity="warning",
        reasons=["progress_lag"],
        metrics={"progress_rate": 0.2},
        requires_adjustment=True,
        recommended_action="adjust",
    )
