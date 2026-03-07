from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.task import Task, TaskStatus, TaskType
from app.models.task_feedback import TaskFeedback
from app.models.user import User
from app.services.task_reflection_service import TaskReflectionService


@pytest.mark.asyncio
async def test_maybe_enqueue_reflection_prompt_for_difficult_feedback(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    task = Task(
        id=uuid4(),
        user_id=user_id,
        plan_id=uuid4(),
        title="多元函数练习",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=25,
        actual_minutes=30,
        difficulty=4,
        energy_cost=2,
        tags=[],
    )
    feedback = TaskFeedback(
        id=uuid4(),
        user_id=user_id,
        task_id=task.id,
        category="too_difficult",
        feedback_text="太难了",
    )
    db_session.add_all([user, task, feedback])
    await db_session.commit()

    service = TaskReflectionService(db_session, redis=None)
    prompt = await service.maybe_enqueue_reflection_prompt(
        user_id=user_id,
        task=task,
        feedback=feedback,
        category="too_difficult",
        time_spent_minutes=30,
    )

    assert prompt is not None
    assert prompt["feedback_id"] == str(feedback.id)
    assert "概念没理解" in prompt["options"]


@pytest.mark.asyncio
async def test_submit_reflection_answer_persists_payload_and_creates_fragment(
    db_session,
    monkeypatch,
):
    user_id = uuid4()
    task_id = uuid4()
    feedback_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    task = Task(
        id=task_id,
        user_id=user_id,
        plan_id=uuid4(),
        title="线性代数补课",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=20,
        actual_minutes=22,
        difficulty=3,
        energy_cost=2,
        tags=[],
    )
    feedback = TaskFeedback(
        id=feedback_id,
        user_id=user_id,
        task_id=task_id,
        category="too_difficult",
    )
    db_session.add_all([user, task, feedback])
    await db_session.commit()

    created = {}

    async def fake_create_fragment(self, **kwargs):
        created["content"] = kwargs["content"]
        return SimpleNamespace(id=uuid4())

    async def fake_analyze_behavior(self, user_id, fragment_id):
        created["analyzed"] = True
        return {"ok": True}

    monkeypatch.setattr(
        "app.services.task_reflection_service.CognitiveService.create_fragment",
        fake_create_fragment,
    )
    monkeypatch.setattr(
        "app.services.task_reflection_service.CognitiveService.analyze_behavior",
        fake_analyze_behavior,
    )

    service = TaskReflectionService(db_session, redis=None)
    payload = await service.submit_reflection_answer(
        user_id=user_id,
        feedback_id=feedback_id,
        selected_option="概念没理解",
        free_text="矩阵变换这块完全没跟上",
    )

    assert payload["status"] == "completed"
    await db_session.refresh(feedback)
    assert feedback.reflection_payload["selected_option"] == "概念没理解"
    assert created["analyzed"] is True
