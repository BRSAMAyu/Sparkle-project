from __future__ import annotations

import json
from datetime import timezone, datetime
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.models.task import Task, TaskStatus, TaskType
from app.services.task_feedback_service import TaskFeedbackService


class _FakeRedis:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def get(self, key: str) -> str | None:
        return json.dumps(self.payload, ensure_ascii=False)


@pytest.mark.asyncio
async def test_task_feedback_service_updates_routing_profile_after_execution_first_struggle(
    db_session,
    test_user,
    monkeypatch,
) -> None:
    task = Task(
        user_id=test_user.id,
        plan_id=uuid4(),
        title="热力学练习",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=30,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.COMPLETED,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    replanner_calls = AsyncMock(return_value=[])
    reflection_calls = AsyncMock(return_value=None)
    routing_calls = AsyncMock(
        return_value={
            "procrastination_threshold": 0.57,
            "emotional_sensitivity": 0.5,
            "directness_preference": 0.5,
        }
    )
    event_publish = AsyncMock(return_value=None)

    class _FakeAdaptiveReplanner:
        def __init__(self, db, redis):
            self.on_task_feedback = replanner_calls

        @staticmethod
        def is_strong_cognitive_struggle_feedback(*, category, feedback_text) -> bool:
            return category == "unclear" or "不理解" in str(feedback_text or "")

    monkeypatch.setattr(
        "app.services.task_feedback_service.AdaptiveReplanner",
        _FakeAdaptiveReplanner,
    )
    monkeypatch.setattr(
        "app.services.task_feedback_service.TaskReflectionService",
        lambda db, redis: SimpleNamespace(maybe_enqueue_reflection_prompt=reflection_calls),
    )
    monkeypatch.setattr(
        "app.services.task_feedback_service.RoutingProfileService",
        lambda db, redis: SimpleNamespace(record_session_outcome=routing_calls),
    )
    monkeypatch.setattr("app.services.task_feedback_service.event_bus.publish", event_publish)

    service = TaskFeedbackService(
        db_session,
        redis=_FakeRedis(
            {
                "mode": "execution_first",
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            }
        ),
    )

    feedback, reflection_prompt = await service.submit_feedback(
        user_id=test_user.id,
        task_id=task.id,
        feedback_text="我还是不理解这部分概念",
        category="unclear",
    )

    assert reflection_prompt is None
    assert feedback.category == "unclear"
    assert feedback.feedback_text == "我还是不理解这部分概念"
    replanner_kwargs = replanner_calls.await_args.kwargs
    assert replanner_kwargs["feedback_text"] == "我还是不理解这部分概念"
    assert replanner_kwargs["category"] == "unclear"
    routing_kwargs = routing_calls.await_args.kwargs
    assert routing_kwargs["route_mode"] == "execution_first"
    assert routing_kwargs["execution_suggestion_ignored"] is True
