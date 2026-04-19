from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.api.v1.tasks import router as tasks_router
from app.core.cache import cache_service
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.task_guide_service import TaskGuideService


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


async def _create_user_and_task(db_session):
    user = User(
        username="task_guidance_user",
        email="task_guidance_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        title="复习数据库索引",
        type=TaskType.LEARNING,
        tags=["database", "index"],
        estimated_minutes=30,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=1,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(task)
    return user, task


@pytest.mark.asyncio
async def test_task_guidance_create_and_retrieve_human_guidance(tasks_client, db_session):
    client, state = tasks_client
    user, task = await _create_user_and_task(db_session)
    state["current_user"] = user

    with patch.object(
        TaskGuideService,
        "_generate_human_content",
        new=AsyncMock(return_value=("## 用户版任务指南\n- 先看索引定义\n- 再做两道题", "test_human_guidance")),
    ):
        create_response = client.post(f"/tasks/{task.id}/guidance?audience=human")

    assert create_response.status_code == 200
    payload = create_response.json()["data"]
    assert UUID(payload["id"])
    assert payload["task_id"] == str(task.id)
    assert payload["user_id"] == str(user.id)
    assert payload["audience"] == "human"
    assert payload["generated_by"] == "test_human_guidance"
    assert payload["policy_version"] == "stage4.task_guidance.v1"
    assert payload["content_format"] == "markdown"
    assert "用户版任务指南" in payload["content"]

    get_response = client.get(f"/tasks/{task.id}/guidance?audience=human")
    assert get_response.status_code == 200
    fetched = get_response.json()["data"]
    assert fetched["id"] == payload["id"]
    assert fetched["task_id"] == str(task.id)
    assert fetched["user_id"] == str(user.id)
    assert fetched["content"] == payload["content"]


@pytest.mark.asyncio
async def test_task_guidance_ai_variant_references_human_guidance(tasks_client, db_session):
    client, state = tasks_client
    user, task = await _create_user_and_task(db_session)
    state["current_user"] = user

    with patch.object(
        TaskGuideService,
        "_generate_human_content",
        new=AsyncMock(return_value=("## 用户版任务指南\n- 先搭主线\n- 再 drill", "test_human_guidance")),
    ):
        human_response = client.post(f"/tasks/{task.id}/guidance?audience=human")
        ai_response = client.post(f"/tasks/{task.id}/guidance?audience=ai")

    assert human_response.status_code == 200
    assert ai_response.status_code == 200

    human_payload = human_response.json()["data"]
    ai_payload = ai_response.json()["data"]

    assert ai_payload["audience"] == "ai"
    assert ai_payload["content_format"] == "plaintext"
    assert ai_payload["source_guidance_id"] == human_payload["id"]
    assert ai_payload["task_id"] == str(task.id)
    assert ai_payload["user_id"] == str(user.id)
    assert ai_payload["generated_by"] == "task_guidance_ai_scaffold"

    fetched_ai = client.get(f"/tasks/{task.id}/guidance?audience=ai")
    assert fetched_ai.status_code == 200
    assert fetched_ai.json()["data"]["id"] == ai_payload["id"]
