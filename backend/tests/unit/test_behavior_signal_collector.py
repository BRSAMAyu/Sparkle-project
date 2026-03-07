from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.behavior_signal_collector import BehaviorSignalCollector


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


@pytest.mark.asyncio
async def test_behavior_signal_collector_creates_fragment_for_too_difficult_streak():
    user_id = uuid4()
    task_id = uuid4()
    rows = [
        (SimpleNamespace(category="too_difficult"), "高数作业"),
        (SimpleNamespace(category="too_difficult"), "线代习题"),
        (SimpleNamespace(category="too_difficult"), "概率论复习"),
    ]
    db = SimpleNamespace(execute=AsyncMock(return_value=_RowsResult(rows)))
    collector = BehaviorSignalCollector(db, redis=None)
    fragment = SimpleNamespace(id=uuid4())
    collector.cognitive_service.create_fragment = AsyncMock(return_value=fragment)
    collector.cognitive_service.analyze_behavior = AsyncMock()
    collector._maybe_emit_inactivity_signal = AsyncMock()
    collector._maybe_emit_pattern_adjustment = AsyncMock()
    collector._mark_signal_emitted = AsyncMock()

    await collector.handle_task_feedback_event(
        {
            "user_id": str(user_id),
            "task_id": str(task_id),
            "category": "too_difficult",
        }
    )

    collector.cognitive_service.create_fragment.assert_awaited_once()
    fragment_payload = collector.cognitive_service.create_fragment.await_args.kwargs
    assert fragment_payload["source_type"] == "behavior_auto"
    assert "连续3次反馈任务太难" in fragment_payload["content"]
    collector.cognitive_service.analyze_behavior.assert_awaited_once_with(user_id, fragment.id)
    collector._maybe_emit_pattern_adjustment.assert_awaited_once()


@pytest.mark.asyncio
async def test_behavior_signal_collector_reacts_to_high_confidence_pattern_event(monkeypatch):
    user_id = uuid4()
    plan_id = uuid4()
    db = SimpleNamespace()
    collector = BehaviorSignalCollector(db, redis=None)
    collector.plan_state_service.get_active_plan_states = AsyncMock(
        return_value=[SimpleNamespace(plan_id=plan_id, status="active")]
    )

    on_detected = AsyncMock(return_value=[])
    monkeypatch.setattr(
        "app.services.behavior_signal_collector.AdaptiveReplanner.on_behavior_pattern_detected",
        on_detected,
    )

    await collector.handle_behavior_pattern_event(
        {
            "user_id": str(user_id),
            "pattern_name": "Planning Optimism",
            "confidence_score": 0.85,
        }
    )

    on_detected.assert_awaited_once()
    assert on_detected.await_args.kwargs["user_id"] == user_id
    assert on_detected.await_args.kwargs["plan_id"] == plan_id
    assert on_detected.await_args.kwargs["pattern_name"] == "Planning Optimism"
