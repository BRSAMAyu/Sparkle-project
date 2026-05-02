from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.api.v1.tasks import router as tasks_router
from app.core.cache import cache_service
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User


@pytest.fixture
def tasks_client(db_session, monkeypatch):
    app = FastAPI()
    app.include_router(tasks_router, prefix="/tasks")
    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    class _FakeAuroraStore:
        def __init__(self, redis):
            pass

        async def load_energy(self, user_id):
            return SimpleNamespace(
                current_level="L1",
                wake_score=0.4,
                is_cooling_down=False,
            )

    monkeypatch.setattr(
        "app.services.daily_task_selection_service.AuroraRuntimeStore",
        _FakeAuroraStore,
    )
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    cache_service._local_cache.clear()

    with TestClient(app) as client:
        yield client, state

    cache_service._local_cache.clear()


async def _create_user_and_task(db_session):
    token = uuid4().hex[:8]
    user = User(
        username=f"priority_api_{token}",
        email=f"priority_api_{token}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()
    task = Task(
        user_id=user.id,
        title="Explainable recommendation task",
        type=TaskType.LEARNING,
        tags=["api"],
        estimated_minutes=20,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=3,
        due_date=date.today(),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(task)
    return user, task


@pytest.mark.asyncio
async def test_priority_reasoning_cache_miss_returns_202_then_cached_payload(tasks_client, db_session):
    client, state = tasks_client
    user, task = await _create_user_and_task(db_session)
    state["current_user"] = user

    first = client.get(f"/tasks/{task.id}/priority-reasoning")
    assert first.status_code == 202
    assert first.json()["status"] == "calculating"

    second = client.get(f"/tasks/{task.id}/priority-reasoning")
    assert second.status_code == 200
    payload = second.json()["data"]
    assert payload["task_id"] == str(task.id)
    assert payload["primary_reason"]
    assert len(payload["supporting_signals"]) == 4


@pytest.mark.asyncio
async def test_priority_reasoning_refresh_returns_synchronous_payload(tasks_client, db_session):
    client, state = tasks_client
    user, task = await _create_user_and_task(db_session)
    state["current_user"] = user

    response = client.get(f"/tasks/{task.id}/priority-reasoning?refresh=true")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["task_id"] == str(task.id)
    assert {signal["type"] for signal in payload["supporting_signals"]} == {
        "spaced_repetition",
        "goal_progress",
        "energy_match",
        "social_context",
    }
