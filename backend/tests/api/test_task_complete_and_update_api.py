"""Regression tests for task lifecycle API fixes (sysrev round1 #02).

Covers:
- P1-1: POST /tasks/{id}/complete must map TaskService ValueError (invalid FSM
  transition, e.g. PENDING -> COMPLETED) to HTTP 400 instead of an unhandled 500.
- P2-5: PUT /tasks/{id} must delegate to TaskService.update so the task-card
  shadow projection (and other service-side side effects) is not skipped.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
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
from app.services import task_service as task_service_module

# ---------------------------------------------------------------------------
# Local SQLite fixture.
# The shared tests/conftest.py db_session fixture fails on SQLite because the
# accountability model declares a func.Least expression index (Postgres-only).
# These tests build the same in-memory schema minus the accountability tables.
# ---------------------------------------------------------------------------

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
async def tasks_client(sqlite_session):
    app = FastAPI()
    app.include_router(tasks_router, prefix="/tasks")

    state = {"current_user": None}

    async def _override_get_db():
        yield sqlite_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    cache_service._local_cache.clear()

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, state

    cache_service._local_cache.clear()


async def _create_user(session) -> User:
    user = User(
        username=f"task_lifecycle_{uuid4().hex[:8]}",
        email=f"task_lifecycle_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_task(session, *, user_id, status: TaskStatus = TaskStatus.PENDING) -> Task:
    task = Task(
        user_id=user_id,
        title="未启动的一键完成任务",
        type=TaskType.LEARNING,
        tags=["sysrev-p1-1"],
        estimated_minutes=30,
        difficulty=3,
        energy_cost=2,
        status=status,
        priority=1,
        due_date=date.today(),
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


# ===========================================================================
# P1-1: /complete maps invalid FSM transition to 400
# ===========================================================================


@pytest.mark.asyncio
async def test_complete_pending_task_returns_400_not_500(tasks_client, sqlite_session):
    """PENDING -> COMPLETED is FSM-forbidden; the API must answer 400, not 500."""
    client, state = tasks_client
    user = await _create_user(sqlite_session)
    state["current_user"] = user
    task = await _create_task(sqlite_session, user_id=user.id, status=TaskStatus.PENDING)

    resp = client.post(f"/tasks/{task.id}/complete", json={"actual_minutes": 25})

    assert resp.status_code == 400, resp.text
    assert "Invalid state transition" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_complete_paused_task_returns_400(tasks_client, sqlite_session):
    """PAUSED -> COMPLETED is likewise forbidden and must map to 400."""
    client, state = tasks_client
    user = await _create_user(sqlite_session)
    state["current_user"] = user
    task = await _create_task(sqlite_session, user_id=user.id, status=TaskStatus.PAUSED)

    resp = client.post(f"/tasks/{task.id}/complete", json={"actual_minutes": 25})

    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_complete_in_progress_task_still_succeeds(tasks_client, sqlite_session):
    """Guard against over-blocking: the legal IN_PROGRESS -> COMPLETED path stays 200."""
    client, state = tasks_client
    user = await _create_user(sqlite_session)
    state["current_user"] = user
    task = await _create_task(sqlite_session, user_id=user.id, status=TaskStatus.IN_PROGRESS)

    resp = client.post(f"/tasks/{task.id}/complete", json={"actual_minutes": 25})

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["data"]["task"]["status"] == TaskStatus.COMPLETED.value


# ===========================================================================
# P2-5: update_task delegates to TaskService.update (card projection sync)
# ===========================================================================


@pytest.mark.asyncio
async def test_update_task_goes_through_task_service_projection_sync(tasks_client, sqlite_session, monkeypatch):
    """PUT /tasks/{id} must route through TaskService.update so the shadow
    projection hook runs; a raw setattr bypass loses card protocol sync."""
    client, state = tasks_client
    user = await _create_user(sqlite_session)
    state["current_user"] = user
    task = await _create_task(sqlite_session, user_id=user.id, status=TaskStatus.PENDING)

    calls: list[SimpleNamespace] = []

    async def _spy_projection(db, task_obj):
        calls.append(task_obj)

    monkeypatch.setattr(task_service_module, "_sync_task_card_projection", _spy_projection)

    resp = client.put(f"/tasks/{task.id}", json={"title": "更新后的标题"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["title"] == "更新后的标题"
    assert any(
        t.id == task.id for t in calls
    ), "update_task must delegate to TaskService.update so _sync_task_card_projection runs"
