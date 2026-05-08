from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.api.v1.aurora import router as aurora_router


def test_daily_startup_endpoint_returns_runtime_payload():
    app = FastAPI()
    app.include_router(aurora_router)

    user_id = uuid4()
    state = {"current_user": type("UserStub", (), {"id": user_id})()}

    async def _override_get_db():
        yield None

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    payload = {
        "message": "昨天做得很好，今天继续 TCP 流量控制。",
        "today_focus": "TCP 流量控制",
        "estimated_minutes": 45,
        "adjustment_reason": "昨天完成率 90%，今天保持当前节奏。",
    }

    with patch(
        "app.api.v1.aurora.AuroraRuntimeV1Service.get_daily_startup_message",
        new=AsyncMock(return_value=payload),
    ) as mock_get_daily:
        with TestClient(app) as client:
            response = client.get(
                f"/aurora/daily-startup?plan_id={uuid4()}&user_id={user_id}",
            )

    assert response.status_code == 200
    assert response.json() == payload
    mock_get_daily.assert_awaited_once()


def test_comeback_context_endpoint_returns_runtime_payload():
    app = FastAPI()
    app.include_router(aurora_router)

    user_id = uuid4()
    state = {"current_user": type("UserStub", (), {"id": user_id})()}

    async def _override_get_db():
        yield None

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    payload = {
        "title": "好久不见，我一直在等你",
        "message": "你已经 6 天没来了，你的计算机网络冲刺还剩 3 天，现在回来还来得及。",
        "days_away": 6,
        "days_remaining": 3,
        "subject": "计算机网络",
        "next_task_title": "TCP 流量控制",
        "recent_task_summary": "TCP 流量控制",
        "light_restart_suggestion": "先开一个「30分钟保底版」，把「TCP 流量控制」推进到一个最小闭环。",
        "plan_id": str(uuid4()),
    }

    with patch(
        "app.api.v1.aurora.AuroraRuntimeV1Service.get_comeback_context",
        new=AsyncMock(return_value=payload),
    ) as mock_get_comeback:
        with TestClient(app) as client:
            response = client.get(
                f"/aurora/comeback-context?user_id={user_id}",
            )

    assert response.status_code == 200
    result = response.json()
    for key, value in payload.items():
        assert result[key] == value, f"Mismatch on key '{key}'"
    mock_get_comeback.assert_awaited_once()


def test_comeback_context_endpoint_returns_empty_object_when_not_eligible():
    app = FastAPI()
    app.include_router(aurora_router)

    user_id = uuid4()
    state = {"current_user": type("UserStub", (), {"id": user_id})()}

    async def _override_get_db():
        yield None

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with patch(
        "app.api.v1.aurora.AuroraRuntimeV1Service.get_comeback_context",
        new=AsyncMock(return_value=None),
    ) as mock_get_comeback:
        with TestClient(app) as client:
            response = client.get(
                f"/aurora/comeback-context?user_id={user_id}",
            )

    assert response.status_code == 200
    assert response.json() == {}
    mock_get_comeback.assert_awaited_once()
