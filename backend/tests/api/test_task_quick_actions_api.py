from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.api.v1.chat import router as chat_router
from app.api.v1.tasks import router as tasks_router
from app.core.cache import cache_service
from app.models.task import SubTask, SubTaskStatus, Task, TaskStatus, TaskType
from app.models.user import User
from app.services.llm_service import LLMResponse
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


@pytest.fixture
def task_chat_client(db_session):
    app = FastAPI()
    app.include_router(chat_router, prefix="/chat")

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
    priority: int = 1,
    estimated_minutes: int = 30,
    difficulty: int = 3,
    energy_cost: int = 2,
) -> Task:
    task = Task(
        user_id=user_id,
        title=title,
        type=TaskType.LEARNING,
        tags=["quick-action"],
        estimated_minutes=estimated_minutes,
        difficulty=difficulty,
        energy_cost=energy_cost,
        status=TaskStatus.PENDING,
        priority=priority,
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
    assert payload["data"]["task"]["due_date"] == (date.today() + timedelta(days=1)).isoformat()

    await db_session.refresh(primary_task)
    assert primary_task.due_date == date.today() + timedelta(days=1)
    assert "snoozed" in (primary_task.tags or [])


@pytest.mark.asyncio
async def test_recommended_tasks_balance_deadline_priority_and_aurora_energy(
    tasks_client,
    db_session,
    monkeypatch,
):
    client, state = tasks_client
    user = await _create_user(db_session)
    await _create_task(
        db_session,
        user_id=user.id,
        title="Hard but loud task",
        due_date=date.today(),
        priority=5,
        estimated_minutes=45,
        difficulty=5,
        energy_cost=5,
    )
    gentle_task = await _create_task(
        db_session,
        user_id=user.id,
        title="Doable recovery step",
        due_date=date.today() + timedelta(days=1),
        priority=1,
        estimated_minutes=15,
        difficulty=2,
        energy_cost=2,
    )
    state["current_user"] = user

    class _FakeAuroraStore:
        def __init__(self, redis):
            pass

        async def load_energy(self, user_id):
            return SimpleNamespace(
                current_level="L2",
                wake_score=0.82,
                is_cooling_down=False,
            )

    monkeypatch.setattr(
        "app.services.daily_task_selection_service.AuroraRuntimeStore",
        _FakeAuroraStore,
    )

    response = client.get("/tasks/recommended?limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == str(gentle_task.id)
    assert payload[0]["title"] == "Doable recovery step"


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


@pytest.mark.asyncio
async def test_stuck_task_returns_live_aurora_diagnosis(tasks_client, db_session, monkeypatch):
    client, state = tasks_client
    user = await _create_user(db_session)
    task = await _create_task(
        db_session,
        user_id=user.id,
        title="拆 TCP 状态机",
        due_date=date.today(),
    )
    state["current_user"] = user

    async def _fake_diagnosis(*args, **kwargs):
        return {
            "mistake_diagnosis": "你卡在 TCP 状态机的状态转换断点。",
            "one_targeted_fix": "先只画 SYN 到 SYN-RECEIVED 这一条边。",
            "diagnosis_question": "你卡在状态转换还是触发条件？",
            "diagnosis_options": ["状态转换", "触发条件"],
            "targeted_fix": "先只画 SYN 到 SYN-RECEIVED 这一条边。",
            "check_question": "LISTEN 收到 SYN 后是什么状态？",
            "source": "test",
            "task_state": {"stage": "stuck", "stuck_topic": "TCP 状态机"},
        }

    mock_publish = AsyncMock()
    monkeypatch.setattr(TaskService, "_build_stuck_diagnosis", _fake_diagnosis)
    monkeypatch.setattr("app.services.task_service.event_bus_reliable.publish", mock_publish)
    monkeypatch.setattr("app.services.task_service.publish_srl_event", AsyncMock())

    response = client.post(
        f"/tasks/{task.id}/stuck",
        json={
            "stuck_point": "TCP 状态机",
            "recent_steps": ["画了 CLOSED", "卡在 LISTEN"],
            "elapsed_seconds": 420,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "stuck"
    assert payload["data"]["task"]["status"] == "STUCK"
    assert payload["data"]["diagnosis"]["mistake_diagnosis"] == "你卡在 TCP 状态机的状态转换断点。"
    assert payload["data"]["diagnosis"]["one_targeted_fix"] == "先只画 SYN 到 SYN-RECEIVED 这一条边。"
    assert payload["data"]["diagnosis"]["targeted_fix"] == "先只画 SYN 到 SYN-RECEIVED 这一条边。"

    await db_session.refresh(task)
    assert task.status == TaskStatus.STUCK
    assert task.guide_json["stuck_help"]["source"] == "test"
    mock_publish.assert_awaited_once()
    assert mock_publish.await_args.args[0] == "task.stuck"
    assert mock_publish.await_args.args[1]["stuck_point"] == "TCP 状态机"


@pytest.mark.asyncio
async def test_stuck_task_sends_stage_context_to_aurora(tasks_client, db_session, monkeypatch):
    client, state = tasks_client
    user = await _create_user(db_session)
    task = await _create_task(
        db_session,
        user_id=user.id,
        title="拆 TCP 状态机",
        due_date=date.today(),
    )
    state["current_user"] = user
    captured: dict[str, object] = {}

    class _FakePlan:
        messages = ["mistake_diagnosis: 卡在状态转换。\none_targeted_fix: 只画 SYN 这一条边。"]

    class _FakeRuntime:
        async def plan_turn(self, **kwargs):
            captured.update(kwargs)
            return _FakePlan()

    monkeypatch.setattr("app.aurora.runtime_v1.service.AuroraRuntimeV1Service", lambda: _FakeRuntime())
    monkeypatch.setattr("app.services.task_service.event_bus_reliable.publish", AsyncMock())
    monkeypatch.setattr("app.services.task_service.publish_srl_event", AsyncMock())

    response = client.post(
        f"/tasks/{task.id}/stuck",
        json={
            "stuck_point": "TCP 状态机",
            "recent_steps": ["画了 CLOSED", "卡在 LISTEN"],
            "elapsed_seconds": 420,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["task"]["status"] == "STUCK"
    assert "mistake_diagnosis" in payload["data"]["diagnosis"]
    assert "one_targeted_fix" in payload["data"]["diagnosis"]
    extra_context = captured["request_extra_context"]
    assert extra_context["task_state"]["stage"] == "stuck"
    assert extra_context["task_state"]["stuck_topic"] == "TCP 状态机"
    assert extra_context["task_stage"] == "stuck"

    await db_session.refresh(task)
    assert task.status == TaskStatus.STUCK


@pytest.mark.asyncio
async def test_next_task_chat_message_inherits_stuck_context(task_chat_client, db_session, monkeypatch):
    client, state = task_chat_client
    user = await _create_user(db_session)
    task = await _create_task(
        db_session,
        user_id=user.id,
        title="拆 TCP 状态机",
        due_date=date.today(),
    )
    task.status = TaskStatus.STUCK
    task.guide_json = {
        "stuck_runtime": {
            "stage": "stuck",
            "stuck_point": "TCP 状态机",
            "recent_steps": ["画了 CLOSED", "卡在 LISTEN"],
            "elapsed_seconds": 420,
        }
    }
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    state["current_user"] = user
    captured: dict[str, object] = {}

    async def _fake_chat_with_tools(**kwargs):
        captured.update(kwargs)
        return LLMResponse(
            content="mistake_diagnosis: 卡在 LISTEN 收到 SYN 后的状态转换。\none_targeted_fix: 只画 SYN 到 SYN-RECEIVED 这一条边。",
            tool_calls=None,
        )

    monkeypatch.setattr("app.api.v1.chat.llm_service.chat_with_tools", _fake_chat_with_tools)

    response = client.post(
        f"/chat/task/{task.id}",
        json={"message": "我还是不知道下一步怎么画"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "mistake_diagnosis" in payload["message"]
    assert "one_targeted_fix" in payload["message"]
    assert captured["user_message"] == "我还是不知道下一步怎么画"
    assert "STUCK TASK DIAGNOSTIC MODE" in captured["system_prompt"]
    assert '"stage": "stuck"' in captured["system_prompt"]

    await db_session.refresh(task)
    assert task.status == TaskStatus.STUCK
