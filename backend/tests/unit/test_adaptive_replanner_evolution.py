from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.orchestration.adaptive_replanner import CognitivePatternTrigger, PlanParameterAdjustment
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


@pytest.mark.asyncio
async def test_replanner_rolls_back_after_two_negative_feedbacks() -> None:
    user_id = uuid4()
    plan_id = uuid4()
    state = SimpleNamespace(
        facts={
            "adaptive_adjustments": {"time_multiplier": 1.15},
            "adaptive_meta": {
                "active_snapshot_id": "snap-new",
                "adjustment_snapshots": [
                    {
                        "id": "snap-base",
                        "adaptive_adjustments": {"time_multiplier": 1.0},
                        "trigger": "baseline",
                        "reasons": [],
                    },
                    {
                        "id": "snap-new",
                        "adaptive_adjustments": {"time_multiplier": 1.15},
                        "trigger": "task_feedback",
                        "reasons": ["time_overrun"],
                    },
                ],
                "rollback_monitor": {
                    "current_snapshot_id": "snap-new",
                    "negative_feedback_streak": 1,
                    "last_feedback_category": "too_difficult",
                },
            },
        }
    )
    replanner = object.__new__(AdaptiveReplanner)
    replanner.plan_state_service = SimpleNamespace(
        get_plan_state=AsyncMock(return_value=state),
        upsert_plan_state=AsyncMock(),
    )
    replanner.cognitive_pattern_trigger = SimpleNamespace(
        _direction=lambda value: "increase" if (value or 0) > 0 else "decrease"
    )
    replanner._enqueue_adaptation_update = AsyncMock()

    records = await replanner._maybe_rollback_after_feedback(
        user_id=user_id,
        plan_id=plan_id,
        feedback_category="too_difficult",
        task_id=uuid4(),
    )

    assert len(records) == 1
    assert "回滚" in records[0].what_changed
    patch = replanner.plan_state_service.upsert_plan_state.await_args.kwargs["patch"]
    assert patch["facts"]["adaptive_adjustments"]["time_multiplier"] == 1.0
    assert patch["facts"]["adaptive_meta"]["active_snapshot_id"] == "snap-base"
    failed_adjustments = patch["facts"]["adaptive_meta"]["failed_adjustments"]
    assert failed_adjustments
    assert failed_adjustments[0]["constraint_key"] == "time_multiplier"
    assert patch["facts"]["adaptive_meta"]["rollback_learning_state"]["last_restored_snapshot_id"] == "snap-base"


@pytest.mark.asyncio
async def test_handle_report_marks_no_adjustment_produced_when_patch_is_noop() -> None:
    replanner = object.__new__(AdaptiveReplanner)
    user_id = uuid4()
    plan_id = uuid4()
    state = SimpleNamespace(facts={"adaptive_meta": {}}, constraints={})
    report = PlanHealthReport(
        plan_id=plan_id,
        user_id=user_id,
        status="active",
        severity="warning",
        reasons=["progress_lag"],
        metrics={"progress_rate": 0.3},
        requires_adjustment=True,
        recommended_action="adjust",
    )

    replanner.plan_state_service = SimpleNamespace(get_plan_state=AsyncMock(return_value=state))
    replanner.plan_health_signal_service = SimpleNamespace(maybe_publish=AsyncMock())
    replanner._apply_cognitive_pattern_adjustments = AsyncMock(return_value=[])
    replanner._apply_incremental_adjustment = AsyncMock(return_value=[])
    replanner._recently_triggered = lambda *args, **kwargs: False

    await replanner._handle_report(report, trigger="task_feedback")

    kwargs = replanner.plan_health_signal_service.maybe_publish.await_args.kwargs
    assert kwargs["action_taken"] == "no_adjustment_produced"
    assert kwargs["adaptation_records"] == []


def test_cognitive_pattern_trigger_skips_previously_failed_adjustment() -> None:
    adjustment = PlanParameterAdjustment(
        parameter="task_duration_multiplier",
        value=1.3,
        reason="test",
        pattern_name="planning optimism",
        confidence_score=0.82,
    )

    assert CognitivePatternTrigger._matches_failed_adjustment(
        adjustment,
        [
            {
                "constraint_key": "task_duration_multiplier",
                "direction": "increase",
            }
        ],
    ) is True

    assert CognitivePatternTrigger._matches_failed_adjustment(
        adjustment,
        [
            {
                "constraint_key": "task_duration_multiplier",
                "direction": "decrease",
            }
        ],
    ) is False
