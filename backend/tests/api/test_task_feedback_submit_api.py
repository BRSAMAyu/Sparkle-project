"""Regression test for daily-flow DF-1: reflection (task feedback) submit 400.

daily-flow-eval observed POST /tasks/{id}/feedback returning 400
"TaskFeedbackResponse.created_at Input should be a valid string" on every
attempt even though the row was persisted (client-visible failure, duplicate
submit risk). Root cause: TaskFeedbackResponse declared created_at/updated_at
as ``str`` while the ORM provides ``datetime``; the pydantic ValidationError
(subclass of ValueError) was swallowed by the endpoint's ``except ValueError``
and surfaced as HTTP 400.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_user, get_db
from app.api.v1.tasks import router as tasks_router
from app.core.cache import cache_service
from app.models.base import Base
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User

_EXCLUDED_TABLES = {"accountability_partnership", "accountability_checkin"}


@pytest.fixture
async def sqlite_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    tables = [t for name, t in Base.metadata.tables.items() if name not in _EXCLUDED_TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def feedback_client(sqlite_session, monkeypatch):
    async def _noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.task_feedback_service.event_bus.publish", _noop_publish)
    monkeypatch.setattr("app.services.task_feedback_service.publish_srl_event", _noop_publish)

    # P1-C: the endpoint now defers heavy followups to a background task that
    # opens its own session. Keep tests hermetic: share the sqlite session and
    # record (then close) scheduled followup coroutines instead of spawning.
    class _SharedSessionFactory:
        def __init__(self, session):
            self._session = session

        def __call__(self):
            return self

        async def __aenter__(self):
            return self._session

        async def __aexit__(self, *exc_info):
            return False

    monkeypatch.setattr(
        "app.services.task_feedback_service.FOLLOWUP_SESSION_FACTORY",
        _SharedSessionFactory(sqlite_session),
    )
    scheduled = []

    def _capture_spawn(coro):
        scheduled.append(coro)
        coro.close()  # close without running: keeps the portal loop task-free
        return None

    monkeypatch.setattr("app.services.task_feedback_service.spawn_followup_task", _capture_spawn)

    app = FastAPI()
    app.include_router(tasks_router, prefix="/tasks")

    state = {"current_user": None, "scheduled_followups": scheduled}

    async def _override_get_db():
        yield sqlite_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    cache_service._local_cache.clear()

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, state, sqlite_session

    cache_service._local_cache.clear()


async def _create_completed_task(session: AsyncSession) -> tuple[User, Task]:
    user = User(
        username=f"task_feedback_{uuid4().hex[:8]}",
        email=f"task_feedback_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
    )
    session.add(user)
    await session.flush()

    task = Task(
        user_id=user.id,
        title="复盘状态机",
        type=TaskType.TRAINING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=30,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return user, task


@pytest.mark.asyncio
async def test_submit_task_feedback_returns_200_with_serializable_timestamps(feedback_client):
    client, state, session = feedback_client
    user, task = await _create_completed_task(session)
    state["current_user"] = user

    response = client.post(
        f"/tasks/{task.id}/feedback",
        json={"completion_quality": 4, "category": "just_right", "feedback_text": "节奏合适"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["data"]["task_id"] == str(task.id)
    # created_at must serialize to a string (ISO), not blow up validation.
    assert isinstance(body["data"]["created_at"], str)
    assert body["data"]["created_at"]


@pytest.mark.asyncio
async def test_feedback_row_is_persisted_when_submit_succeeds(feedback_client):
    client, state, session = feedback_client
    user, task = await _create_completed_task(session)
    state["current_user"] = user

    response = client.post(
        f"/tasks/{task.id}/feedback",
        json={"completion_quality": 5, "category": "too_easy"},
    )

    assert response.status_code == 200, response.text

    from sqlalchemy import select

    from app.models.task_feedback import TaskFeedback

    result = await session.execute(select(TaskFeedback).where(TaskFeedback.task_id == task.id))
    stored = result.scalar_one_or_none()
    assert stored is not None, "feedback row must be persisted on a successful submit"
    assert stored.category == "too_easy"


@pytest.mark.asyncio
async def test_resubmit_feedback_updates_existing_row(feedback_client):
    client, state, session = feedback_client
    user, task = await _create_completed_task(session)
    state["current_user"] = user

    first = client.post(f"/tasks/{task.id}/feedback", json={"category": "too_difficult"})
    assert first.status_code == 200, first.text
    second = client.post(f"/tasks/{task.id}/feedback", json={"category": "just_right"})
    assert second.status_code == 200, second.text
    assert second.json()["data"]["category"] == "just_right"
