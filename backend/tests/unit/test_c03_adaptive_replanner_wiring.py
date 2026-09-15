from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.services.task_event_consumer import TaskEventConsumer


class _FakeSessionCM:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_task_abandoned_consumer_routes_to_adaptive_replanner_health_eval():
    user_id = uuid4()
    task_id = uuid4()
    plan_id = uuid4()
    consumer = TaskEventConsumer(Mock())
    db_session = AsyncMock()
    db_session.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: plan_id))
    collector_instance = SimpleNamespace(handle_task_abandoned_event=AsyncMock())
    replanner_instance = SimpleNamespace(evaluate_plan_health_now=AsyncMock(return_value=[]))

    with patch("app.services.task_event_consumer.AsyncSessionLocal", return_value=_FakeSessionCM(db_session)), patch(
        "app.services.task_event_consumer.BehaviorSignalCollector",
        return_value=collector_instance,
    ), patch(
        "app.services.task_event_consumer.AdaptiveReplanner",
        return_value=replanner_instance,
    ), patch.object(
        consumer,
        "_handle_spine_bridge_event",
        new_callable=AsyncMock,
    ), patch.object(
        consumer,
        "_record_task_outcome",
        new_callable=AsyncMock,
    ):
        await consumer._handle_task_abandoned(
            {
                "event_type": "task.abandoned",
                "user_id": str(user_id),
                "task_id": str(task_id),
            }
        )

    collector_instance.handle_task_abandoned_event.assert_awaited_once()
    replanner_instance.evaluate_plan_health_now.assert_awaited_once()
    kwargs = replanner_instance.evaluate_plan_health_now.await_args.kwargs
    assert kwargs["user_id"] == user_id
    assert kwargs["plan_id"] == plan_id
    assert kwargs["task_id"] == task_id
    assert kwargs["trigger"] == "task_abandoned"
    assert kwargs["feedback_category"] == "abandoned"
    assert kwargs["completion_rate"] == 0.0


@pytest.mark.asyncio
async def test_task_stuck_consumer_routes_to_adaptive_replanner_health_eval():
    user_id = uuid4()
    task_id = uuid4()
    plan_id = uuid4()
    consumer = TaskEventConsumer(Mock())
    db_session = AsyncMock()
    db_session.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: plan_id))
    replanner_instance = SimpleNamespace(evaluate_plan_health_now=AsyncMock(return_value=[]))

    with patch("app.services.task_event_consumer.AsyncSessionLocal", return_value=_FakeSessionCM(db_session)), patch(
        "app.services.task_event_consumer.AdaptiveReplanner",
        return_value=replanner_instance,
    ), patch.object(
        consumer,
        "_handle_spine_bridge_event",
        new_callable=AsyncMock,
    ):
        await consumer._handle_task_stuck(
            {
                "event_type": "task.stuck",
                "user_id": str(user_id),
                "task_id": str(task_id),
                "category": "unclear",
            }
        )

    replanner_instance.evaluate_plan_health_now.assert_awaited_once()
    kwargs = replanner_instance.evaluate_plan_health_now.await_args.kwargs
    assert kwargs["user_id"] == user_id
    assert kwargs["plan_id"] == plan_id
    assert kwargs["task_id"] == task_id
    assert kwargs["trigger"] == "task_stuck"
    assert kwargs["feedback_category"] == "unclear"
