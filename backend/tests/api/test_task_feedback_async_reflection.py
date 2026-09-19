"""P1-C red/green: reflection submit must ack fast even with a slow LLM.

daily-flow-eval-r2 DF-1 residual: POST /tasks/{id}/feedback took 26.7s /
0.97s / >30s(503 gateway timeout) across three simulated days while the row
WAS persisted — a "client failed, server succeeded" false failure caused by
running the reflection inference chain (adaptive replanning + structured
reflection LLM behavior analysis + remedial insertion) inline in the request.

Fix contract tested here:
1. With a slow reflection LLM stubbed, the endpoint still acks in <2s (200)
   and the feedback row is persisted synchronously.
2. The heavy inference chain is scheduled exactly once as a background
   followup task, and the followup actually executes it (against its own
   session) after the ack.
"""

from __future__ import annotations

import asyncio
import time
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_user, get_db
from app.api.v1.tasks import router as tasks_router
from app.core.cache import cache_service
from app.models.base import Base
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_feedback import TaskFeedback
from app.models.user import User
from app.services.task_feedback_service import TaskFeedbackService

_EXCLUDED_TABLES = {"accountability_partnership", "accountability_checkin"}

_SLOW_LLM_SECONDS = 8.0
_ACK_BUDGET_SECONDS = 2.0


class _SharedSessionFactory:
    """Wraps an existing AsyncSession so `async with factory()` reuses it."""

    def __init__(self, session: AsyncSession):
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *exc_info) -> bool:
        return False


def _make_slow_reflection_stub(calls: list, delay: float):
    """Stub TaskReflectionService whose structured-answer path is slow (LLM)."""

    class _SlowReflectionService:
        def __init__(self, db, redis=None):
            self.db = db
            self.redis = redis

        async def submit_reflection_answer(self, **kwargs):
            calls.append(kwargs)
            await asyncio.sleep(delay)
            return {"prompt": {"question": "stub"}, "status": "completed"}

        async def maybe_enqueue_reflection_prompt(self, **kwargs):
            return None

    return _SlowReflectionService


@pytest.fixture
async def p1c_sqlite():
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


async def _create_completed_task(session: AsyncSession) -> tuple[User, Task]:
    user = User(
        username=f"p1c_{uuid4().hex[:8]}",
        email=f"p1c_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
    )
    session.add(user)
    await session.flush()
    task = Task(
        user_id=user.id,
        title="反思提交超时复现任务",
        type=TaskType.TRAINING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=30,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return user, task


def _build_app(monkeypatch, session: AsyncSession) -> tuple[FastAPI, dict]:
    async def _noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.task_feedback_service.event_bus.publish", _noop_publish)
    monkeypatch.setattr("app.services.task_feedback_service.publish_srl_event", _noop_publish)

    monkeypatch.setattr(
        "app.services.task_feedback_service.FOLLOWUP_SESSION_FACTORY",
        _SharedSessionFactory(session),
        raising=False,  # pre-fix module has no such attr; red must fail on timing
    )

    app = FastAPI()
    app.include_router(tasks_router, prefix="/tasks")
    state: dict = {"current_user": None}

    async def _override_get_db():
        yield session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    return app, state


_STRUCTURED_FEEDBACK = {
    "completion_quality": 3,
    "category": "unclear",
    "feedback_text": "卡在公式应用上了",
    "stuck_point": "热力学公式看得懂但不知道什么时候套用",
    "effective_method": "先画能量流向图",
    "adjustment_intention": "下次先做 1 道代表题",
}


@pytest.mark.asyncio
async def test_feedback_acks_fast_with_slow_llm_and_schedules_followup(p1c_sqlite, monkeypatch):
    """红：旧代码在请求内同步跑 LLM → >2s。绿：快速 ack + followup 被调度一次。"""
    reflection_calls: list = []
    monkeypatch.setattr(
        "app.services.task_feedback_service.TaskReflectionService",
        _make_slow_reflection_stub(reflection_calls, _SLOW_LLM_SECONDS),
    )
    scheduled: list = []

    def _capture_spawn(coro):
        scheduled.append(coro)
        coro.close()  # assert scheduling only; the pipeline itself is covered below
        return None

    monkeypatch.setattr("app.services.task_feedback_service.spawn_followup_task", _capture_spawn, raising=False)

    app, state = _build_app(monkeypatch, p1c_sqlite)
    user, task = await _create_completed_task(p1c_sqlite)
    state["current_user"] = user

    cache_service._local_cache.clear()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            started = time.perf_counter()
            response = client.post(f"/tasks/{task.id}/feedback", json=_STRUCTURED_FEEDBACK)
            elapsed = time.perf_counter() - started

        assert response.status_code == 200, response.text
        assert response.json()["success"] is True
        # P1-C core contract: slow LLM must not hold the request hostage.
        assert elapsed < _ACK_BUDGET_SECONDS, (
            f"endpoint took {elapsed:.2f}s with a slow LLM stub; " "heavy inference is still blocking the request path"
        )
        # inference stub must NOT have run inside the request
        assert reflection_calls == []
        # async followup scheduled exactly once, with structured reflection flagged
        assert len(scheduled) == 1, "deferred heavy followup must be scheduled once"
    finally:
        cache_service._local_cache.clear()

    # feedback row is persisted synchronously (client-failed/server-succeeded impossible)
    result = await p1c_sqlite.execute(select(TaskFeedback).where(TaskFeedback.task_id == task.id))
    stored = result.scalar_one_or_none()
    assert stored is not None
    assert stored.category == "unclear"


@pytest.mark.asyncio
async def test_deferred_followup_executes_reflection_pipeline(p1c_sqlite, monkeypatch):
    """异步任务被真实调度并执行：join 后 LLM stub 恰好被调一次，ack 不等待它。"""
    reflection_calls: list = []
    monkeypatch.setattr(
        "app.services.task_feedback_service.TaskReflectionService",
        _make_slow_reflection_stub(reflection_calls, 0.3),
    )

    async def _noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.task_feedback_service.event_bus.publish", _noop_publish)
    monkeypatch.setattr("app.services.task_feedback_service.publish_srl_event", _noop_publish)
    monkeypatch.setattr(
        "app.services.task_feedback_service.FOLLOWUP_SESSION_FACTORY",
        _SharedSessionFactory(p1c_sqlite),
        raising=False,  # pre-fix module has no such attr; red must fail on timing
    )
    cache_service._local_cache.clear()

    try:
        user, task = await _create_completed_task(p1c_sqlite)
        service = TaskFeedbackService(p1c_sqlite, redis=None)

        started = time.perf_counter()
        feedback, reflection_prompt = await service.submit_feedback(
            user_id=user.id,
            task_id=task.id,
            **_STRUCTURED_FEEDBACK,
            defer_heavy_followups=True,
        )
        elapsed = time.perf_counter() - started

        assert feedback.id is not None
        assert elapsed < _ACK_BUDGET_SECONDS, f"submit took {elapsed:.2f}s"
        assert reflection_calls == [], "LLM inference must not run before the ack"
        assert reflection_prompt is None  # structured prompt is deferred with the pipeline

        await service.join_followup()

        assert len(reflection_calls) == 1, "deferred followup must run the reflection once"
        assert reflection_calls[0]["feedback_id"] == feedback.id
        assert reflection_calls[0]["stuck_point"] == _STRUCTURED_FEEDBACK["stuck_point"]
    finally:
        cache_service._local_cache.clear()


@pytest.mark.asyncio
async def test_inline_mode_still_persists_and_runs_pipeline(p1c_sqlite, monkeypatch):
    """邻域回归：默认内联模式（defer_heavy_followups=False）保持历史语义。"""
    reflection_calls: list = []
    monkeypatch.setattr(
        "app.services.task_feedback_service.TaskReflectionService",
        _make_slow_reflection_stub(reflection_calls, 0.0),
    )

    async def _noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.task_feedback_service.event_bus.publish", _noop_publish)
    monkeypatch.setattr("app.services.task_feedback_service.publish_srl_event", _noop_publish)
    cache_service._local_cache.clear()

    try:
        user, task = await _create_completed_task(p1c_sqlite)
        service = TaskFeedbackService(p1c_sqlite, redis=None)
        feedback, reflection_prompt = await service.submit_feedback(
            user_id=user.id,
            task_id=task.id,
            **_STRUCTURED_FEEDBACK,
        )

        assert len(reflection_calls) == 1
        assert reflection_prompt == {"question": "stub"}
        result = await p1c_sqlite.execute(select(TaskFeedback).where(TaskFeedback.task_id == task.id))
        stored = result.scalar_one_or_none()
        assert stored is not None and stored.id == feedback.id
    finally:
        cache_service._local_cache.clear()
