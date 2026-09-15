from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.spine_event_bridge import SPINE_EVENT_TYPES, SpineEventBridge


def test_spine_event_bridge_builds_signals_for_h01_events() -> None:
    bridge = SpineEventBridge(redis_client=AsyncMock())

    samples = {
        "task.abandoned": {"user_id": "u1", "task_id": "t1", "reason": "too_hard"},
        "task.stuck": {"user_id": "u1", "task_id": "t1", "elapsed_seconds": 1200},
        "focus.session.completed": {"user_id": "u1", "session_id": "f1", "duration_minutes": 95},
        "plan.created": {"user_id": "u1", "plan_id": "p1", "metadata": {"plan_type": "exam"}},
        "srl.phase.transition": {"user_id": "u1", "evidence_id": "e1", "trigger_event_type": "plan.created"},
        "calendar.event.created": {"user_id": "u1", "event_id": "c1", "title": "midterm exam"},
        "calendar.event.updated": {"user_id": "u1", "event_id": "c1", "changes": {"title": "final exam"}},
        "calendar.event.deleted": {"user_id": "u1", "event_id": "c1"},
        "notification.fatigue_detected": {"user_id": "u1", "consecutive_dismissals": 3},
        "shop.purchase_completed": {"user_id": "u1", "item_name": "theme", "amount": 100},
        "achievement.unlocked": {"user_id": "u1", "achievement_name": "first_task", "rarity": "common"},
    }

    assert set(samples) == SPINE_EVENT_TYPES
    signals = {event_type: bridge.build_signal({"event_type": event_type, **payload}) for event_type, payload in samples.items()}

    assert signals["task.abandoned"].state_key == "execution_consistency"
    assert signals["task.stuck"].state_key == "knowledge_bottleneck"
    assert signals["focus.session.completed"].state_key == "cognitive_load"
    assert signals["plan.created"].state_key == "goal_mode"
    assert signals["srl.phase.transition"].state_key == "strategy_confidence"
    assert signals["calendar.event.created"].state_key == "time_context"
    assert signals["calendar.event.deleted"].claim == "calendar_deadline_removed"


@pytest.mark.asyncio
async def test_spine_event_bridge_runs_pipeline_for_supported_event() -> None:
    bridge = SpineEventBridge(redis_client=AsyncMock())
    bridge.spine._run_signal_pipeline = AsyncMock(return_value="trace")

    result = await bridge.handle_event({
        "event_type": "task.stuck",
        "user_id": "u1",
        "task_id": "t1",
        "elapsed_seconds": 1200,
    })

    assert result == "trace"
    bridge.spine._run_signal_pipeline.assert_awaited_once()
    kwargs = bridge.spine._run_signal_pipeline.await_args.kwargs
    assert kwargs["user_id"] == "u1"
    assert kwargs["signal"].claim == "task_stuck"


@pytest.mark.asyncio
async def test_task_event_consumer_dispatches_h01_events_to_spine_bridge() -> None:
    from app.services.task_event_consumer import TaskEventConsumer

    consumer = TaskEventConsumer(event_bus=AsyncMock())
    with patch.object(consumer, "_handle_spine_bridge_event", new_callable=AsyncMock) as mock_bridge:
        await consumer.handle_event({"event_type": "focus.session.completed", "user_id": "u1"})
        await consumer.handle_event({"event_type": "plan.created", "user_id": "u1"})
        await consumer.handle_event({"event_type": "srl.phase.transition", "user_id": "u1"})
        await consumer.handle_event({"event_type": "calendar.event.created", "user_id": "u1"})

    assert mock_bridge.await_count == 4


class TestCalendarSignalBridgeIntegration:
    """P2-11: CalendarSignalBridge wired into SpineEventBridge._calendar_changed()."""

    def test_deadline_pressure_detected_for_exam_within_72h(self) -> None:
        from datetime import UTC, datetime, timedelta

        bridge = SpineEventBridge(redis_client=AsyncMock())
        in_48h = (datetime.now(UTC) + timedelta(hours=48)).isoformat()

        signal = bridge.build_signal({
            "event_type": "calendar.event.created",
            "user_id": "u1",
            "event_id": "c1",
            "title": "Final Exam",
            "start_time": in_48h,
            "end_time": (datetime.now(UTC) + timedelta(hours=50)).isoformat(),
            "calendar_event_type": "exam",
        })

        assert signal is not None
        assert signal.state_key == "deadline_pressure"
        assert signal.claim == "upcoming_deadline"
        assert signal.priority == "medium"
        assert signal.confidence == 0.95
        assert "Final Exam" in signal.evidence_summary

    def test_deadline_pressure_high_urgency_within_24h(self) -> None:
        from datetime import UTC, datetime, timedelta

        bridge = SpineEventBridge(redis_client=AsyncMock())
        in_12h = (datetime.now(UTC) + timedelta(hours=12)).isoformat()

        signal = bridge.build_signal({
            "event_type": "calendar.event.created",
            "user_id": "u1",
            "event_id": "c2",
            "title": "Math Midterm",
            "start_time": in_12h,
            "calendar_event_type": "deadline",
        })

        assert signal is not None
        assert signal.state_key == "deadline_pressure"
        assert signal.priority == "high"

    def test_time_context_fallback_for_non_exam_event(self) -> None:
        from datetime import UTC, datetime, timedelta

        bridge = SpineEventBridge(redis_client=AsyncMock())
        in_48h = (datetime.now(UTC) + timedelta(hours=48)).isoformat()

        signal = bridge.build_signal({
            "event_type": "calendar.event.created",
            "user_id": "u1",
            "event_id": "c3",
            "title": "Study Group",
            "start_time": in_48h,
            "calendar_event_type": "meeting",
        })

        assert signal is not None
        assert signal.state_key == "time_context"
        assert signal.claim == "calendar_time_context_updated"

    def test_deleted_event_returns_removed_claim(self) -> None:
        from datetime import UTC, datetime, timedelta

        bridge = SpineEventBridge(redis_client=AsyncMock())
        in_48h = (datetime.now(UTC) + timedelta(hours=48)).isoformat()

        signal = bridge.build_signal({
            "event_type": "calendar.event.deleted",
            "user_id": "u1",
            "event_id": "c4",
            "title": "Canceled Exam",
            "start_time": in_48h,
            "calendar_event_type": "exam",
        })

        assert signal is not None
        assert signal.claim == "calendar_deadline_removed"
        assert signal.confidence == 0.62

    def test_no_start_time_falls_back_to_generic(self) -> None:
        bridge = SpineEventBridge(redis_client=AsyncMock())

        signal = bridge.build_signal({
            "event_type": "calendar.event.created",
            "user_id": "u1",
            "event_id": "c5",
            "title": "Some Event",
        })

        assert signal is not None
        assert signal.state_key == "time_context"
        assert signal.claim == "calendar_event_observed"
        assert signal.priority == "low"

    def test_detect_deadline_pressure_returns_none_for_future_event(self) -> None:
        from datetime import UTC, datetime, timedelta

        bridge = SpineEventBridge(redis_client=AsyncMock())
        in_200h = (datetime.now(UTC) + timedelta(hours=200)).isoformat()

        signal = bridge.build_signal({
            "event_type": "calendar.event.created",
            "user_id": "u1",
            "event_id": "c6",
            "title": "Way Future Exam",
            "start_time": in_200h,
            "calendar_event_type": "exam",
        })

        assert signal is not None
        # Falls through to time_context because >72h threshold
        assert signal.state_key == "time_context"
        assert signal.claim == "calendar_time_context_updated"
