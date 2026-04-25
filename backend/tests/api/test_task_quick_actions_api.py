from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.api.v1.tasks import router as tasks_router
from app.core.cache import cache_service
from app.models.task import SubTask, SubTaskStatus, Task, TaskStatus, TaskType
from app.models.user import User
from app.services.task_service import TaskService


@pytest.fixture
def tasks_client(db_session):
    app = FastAPI()
    app.include_router(tasks_router, prefix="/tasks")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    cache_service._local_cache.clear()

    with TestClient(app) as client:
        yield client, state

    cache_service._local_cache.clear()


async def _create_user(db_session) -> User:
    user = User(
        username="task_quick_action_user",
        email="task_quick_action_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_task(
    db_session,
    *,
    user_id,
    title: str,
    due_date: date | None = None,
) -> Task:
    task = Task(
        user_id=user_id,
        title=title,
        type=TaskType.LEARNING,
        tags=["quick-action"],
        estimated_minutes=30,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=1,
        due_date=due_date,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest.mark.asyncio
async def test_snooze_task_moves_due_date_without_replanning(tasks_client, db_session):
    client, state = tasks_client
    user = await _create_user(db_session)
    primary_task = await _create_task(
        db_session,
        user_id=user.id,
        title="复习线性代数",
        due_date=date.today(),
    )
    await _create_task(
        db_session,
        user_id=user.id,
        title="写错题总结",
        due_date=date.today(),
    )
    state["current_user"] = user

    response = client.post(f"/tasks/{primary_task.id}/snooze")

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "snooze"
    assert "写错题总结" in payload["message"]
    assert payload["data"]["task"]["due_date"] == (
        date.today() + timedelta(days=1)
    ).isoformat()

    await db_session.refresh(primary_task)
    assert primary_task.due_date == date.today() + timedelta(days=1)
    assert "snoozed" in (primary_task.tags or [])


@pytest.mark.asyncio
async def test_too_hard_returns_new_subtasks(tasks_client, db_session, monkeypatch):
    client, state = tasks_client
    user = await _create_user(db_session)
    task = await _create_task(
        db_session,
        user_id=user.id,
        title="完成一整章概率题",
        due_date=date.today(),
    )
    state["current_user"] = user

    async def _fake_breakdown(self, *, user_id, task_id, feedback_text=None):
        db_task = await self.db.get(Task, task_id)
        assert db_task is not None
        db_task.difficulty = 2
        self.db.add(db_task)

        subtasks = [
            SubTask(
                parent_task_id=db_task.id,
                title="先找出最卡的一类题",
                order=0,
                status=SubTaskStatus.PENDING,
                estimated_minutes=5,
                guide_content="只定位卡点。",
            ),
            SubTask(
                parent_task_id=db_task.id,
                title="做一道最小样例",
                order=1,
                status=SubTaskStatus.PENDING,
                estimated_minutes=10,
                guide_content="先做一题，不扩展。",
            ),
        ]
        for subtask in subtasks:
            self.db.add(subtask)

        await self.db.flush()
        return subtasks

    monkeypatch.setattr(
        "app.orchestration.adaptive_replanner.AdaptiveReplanner.break_down_single_task_for_too_hard",
        _fake_breakdown,
    )

    response = client.post(
        f"/tasks/{task.id}/too-hard",
        json={"reason": "这一张任务卡太重了"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "too_hard"
    assert len(payload["data"]["subtasks"]) == 2
    assert payload["data"]["subtasks"][0]["title"] == "先找出最卡的一类题"
    assert "先做" in payload["message"]

    await db_session.refresh(task)
    assert task.difficulty == 2


@pytest.mark.asyncio
async def test_skip_task_marks_task_abandoned(tasks_client, db_session, monkeypatch):
    client, state = tasks_client
    user = await _create_user(db_session)
    task = await _create_task(
        db_session,
        user_id=user.id,
        title="晚点再做的任务",
    )
    state["current_user"] = user

    async def _fake_abandon_task(*, db, task_id, user_id, reason=None):
        db_task = await db.get(Task, task_id)
        assert db_task is not None
        db_task.status = TaskStatus.ABANDONED
        db_task.completed_at = datetime.utcnow()
        db_task.user_note = f"Abandoned: {reason}" if reason else None
        db.add(db_task)
        await db.flush()
        return db_task

    monkeypatch.setattr(TaskService, "abandon_task", _fake_abandon_task)

    response = client.post(
        f"/tasks/{task.id}/skip",
        json={"reason": "今天先让路"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "skip"
    assert payload["message"] == "已跳过，这张卡不会再挤在今天了。"
    assert payload["data"]["task"]["status"] == "ABANDONED"
    assert UUID(payload["data"]["task"]["id"]) == task.id

    await db_session.refresh(task)
    assert task.status == TaskStatus.ABANDONED
    assert task.user_note == "Skipped from quick action"
