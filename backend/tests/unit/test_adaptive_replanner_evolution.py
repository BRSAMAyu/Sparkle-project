from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.orchestration.adaptive_replanner import AdaptiveReplanner, CognitivePatternTrigger, PlanParameterAdjustment
from app.orchestration.dual_core_router import AdaptationRecord
from app.orchestration.step_feedback_collector import PlanExecutionFeedback
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


@pytest.mark.asyncio
async def test_on_task_feedback_uses_struggle_trigger_for_unclear_feedback() -> None:
    user_id = uuid4()
    plan_id = uuid4()
    task_id = uuid4()
    replanner = object.__new__(AdaptiveReplanner)
    replanner._maybe_record_breakdown_feedback = AsyncMock()
    replanner._maybe_rollback_after_feedback = AsyncMock(return_value=[])
    replanner.evaluate_plan_health_now = AsyncMock(return_value=[])

    await replanner.on_task_feedback(
        user_id=user_id,
        plan_id=plan_id,
        task_id=task_id,
        category="unclear",
        difficulty_delta=-0.1,
        feedback_text="这里我还是不理解这个概念",
    )

    kwargs = replanner.evaluate_plan_health_now.await_args.kwargs
    assert kwargs["trigger"] == "task_feedback_struggle"
    assert kwargs["feedback_category"] == "unclear"


@pytest.mark.asyncio
async def test_on_plan_execution_completed_records_execution_delta_without_replan() -> None:
    user_id = uuid4()
    plan_id = uuid4()
    replanner = object.__new__(AdaptiveReplanner)
    state = SimpleNamespace(facts={"adaptive_meta": {"recent_execution_feedback_deltas": []}})
    replanner.plan_state_service = SimpleNamespace(
        get_plan_state=AsyncMock(return_value=state),
        upsert_plan_state=AsyncMock(),
    )
    replanner.plan_review_service = SimpleNamespace(trigger_replanning=AsyncMock())
    replanner._enqueue_adaptation_update = AsyncMock()
    replanner._apply_cognitive_pattern_adjustments = AsyncMock(return_value=[])

    feedback = PlanExecutionFeedback(
        plan_id=str(plan_id),
        user_id=str(user_id),
        session_id="session-1",
        validation_status="passed",
        quality_score=0.95,
        total_steps=3,
        steps_passed=3,
        steps_failed=0,
        aborted=False,
        step_feedbacks=[],
        slow_tools=[],
        failed_tools=[],
        unreliable_dependencies=[],
    )

    records = await replanner.on_plan_execution_completed(
        user_id=user_id,
        plan_id=plan_id,
        feedback=feedback,
    )

    assert records == []
    patch = replanner.plan_state_service.upsert_plan_state.await_args.kwargs["patch"]
    adaptive_meta = patch["facts"]["adaptive_meta"]
    assert adaptive_meta["last_execution_feedback_delta"]["validation_status"] == "passed"
    assert adaptive_meta["last_execution_feedback_delta"]["needs_replanning"] is False
    assert adaptive_meta["last_plan_revision_summary"]["new_next_action"].startswith("继续")
    replanner.plan_review_service.trigger_replanning.assert_not_called()


@pytest.mark.asyncio
async def test_adaptation_update_explains_why_plan_changed(monkeypatch) -> None:
    user_id = uuid4()
    replanner = object.__new__(AdaptiveReplanner)
    replanner.redis = None
    enqueue = AsyncMock(return_value=True)

    class _FakeSystemUpdateService:
        def __init__(self, redis=None):
            self.redis = redis

        async def enqueue(self, user_id_arg, payload):
            await enqueue(user_id_arg, payload)
            return True

    monkeypatch.setattr("app.orchestration.adaptive_replanner.SystemUpdateService", _FakeSystemUpdateService)

    await replanner._enqueue_adaptation_update(
        user_id,
        AdaptationRecord(
            what_changed="重新规划了当前阶段的执行路径",
            why="触发原因：progress_lag, difficulty_too_hard",
            expected_effect="避免沿着当前失效路径继续推进。",
            user_facing_message="我发现原来的推进方式已经不够合适，准备帮你重新收紧计划。",
            source="adaptive_replanner",
        ),
        update_type="plan_adaptation",
    )

    payload = enqueue.await_args.args[1]
    assert payload["title"] == "计划已根据真实进展调整"
    assert "原因：触发原因：progress_lag, difficulty_too_hard" in payload["description"]
    assert payload["metadata"]["adaptation_reason"] == "触发原因：progress_lag, difficulty_too_hard"
    assert payload["metadata"]["adaptation_record"]["source"] == "adaptive_replanner"


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
