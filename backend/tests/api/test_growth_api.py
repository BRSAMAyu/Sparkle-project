import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.api.v1.growth import router as growth_router
from app.models.user import User


@pytest.fixture
def growth_client(db_session):
    app = FastAPI()
    app.include_router(growth_router, prefix="/growth")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


@pytest.mark.asyncio
async def test_growth_dashboard_endpoint_returns_service_snapshot(growth_client, db_session):
    client, state = growth_client
    user = User(
        username="growth_api_user",
        email="growth_api_user@example.com",
        hashed_password="hashed",
        nickname="Ava",
    )
    db_session.add(user)
    await db_session.commit()
    state["current_user"] = user

    snapshot = {
        "growth_status": {"headline": "Ava，你本周在热力学上进步了 22%"},
        "most_important_task": {"title": "整理可逆过程错题"},
        "growth_signal": {"topic": "热力学"},
        "active_plan_progress": {"name": "热力学冲刺计划"},
    }

    with patch(
        "app.api.v1.growth.GrowthDashboardService.build_snapshot",
        new=AsyncMock(return_value=snapshot),
    ) as mock_build:
        response = client.get("/growth/dashboard")

    assert response.status_code == 200
    assert response.json() == snapshot
    mock_build.assert_awaited_once_with(user.id, user=user)


@pytest.mark.asyncio
async def test_daily_context_line_endpoint_returns_cached_line(growth_client, db_session):
    client, state = growth_client
    user = User(
        username="daily_line_user",
        email="daily_line_user@example.com",
        hashed_password="hashed",
        nickname="Ava",
    )
    db_session.add(user)
    await db_session.commit()
    state["current_user"] = user

    payload = {
        "text": "离热力学考试还有 3 天，今天先做错题复盘。",
        "source": "rule",
        "date": "2026-04-25",
    }

    with patch(
        "app.api.v1.growth.GrowthDashboardService.get_daily_context_line",
        new=AsyncMock(return_value=payload),
    ) as mock_build:
        response = client.get("/growth/daily-context-line")

    assert response.status_code == 200
    assert response.json() == payload
    mock_build.assert_awaited_once_with(user.id, user=user, force_refresh=False)


@pytest.mark.asyncio
async def test_weekly_narrative_endpoint_returns_cached_story(growth_client, db_session):
    client, state = growth_client
    user = User(
        username="growth_narrative_user",
        email="growth_narrative_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    state["current_user"] = user

    story = {
        "period": "本周成长故事",
        "body": "这周你在热力学上完成了 2 个任务。",
        "sentences": ["这周你在热力学上完成了 2 个任务。"],
        "is_placeholder": False,
    }

    with patch(
        "app.api.v1.growth.ProgressNarrativeService.get_weekly_narrative",
        new=AsyncMock(return_value=story),
    ) as mock_get:
        response = client.get("/growth/weekly-narrative")

    assert response.status_code == 200
    assert response.json() == story
    mock_get.assert_awaited_once_with(user.id)


@pytest.mark.asyncio
async def test_weekly_narrative_generate_endpoint_forces_refresh(growth_client, db_session):
    client, state = growth_client
    user = User(
        username="growth_narrative_refresh_user",
        email="growth_narrative_refresh_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    state["current_user"] = user

    story = {
        "period": "本周成长故事",
        "body": "手动刷新后的成长故事。",
        "sentences": ["手动刷新后的成长故事。"],
        "is_placeholder": False,
    }

    with patch(
        "app.api.v1.growth.ProgressNarrativeService.get_weekly_narrative",
        new=AsyncMock(return_value=story),
    ) as mock_get:
        response = client.post("/growth/weekly-narrative/generate")

    assert response.status_code == 200
    assert response.json() == story
    mock_get.assert_awaited_once_with(user.id, force=True)


@pytest.mark.asyncio
async def test_return_case_file_rebuild_path(growth_client, db_session):
    """GOAL-011: rebuild=true forces rebuild from chronicle."""
    client, state = growth_client
    user = User(
        username="returning_user_rebuild",
        email="returning_rebuild@example.com",
        hashed_password="hashed",
        nickname="Riku",
    )
    db_session.add(user)
    await db_session.commit()
    state["current_user"] = user

    case_payload = {
        "user_id": str(user.id),
        "chronicle_summary": {"total_entries": 5, "confirmed_count": 3, "pending_count": 1},
        "confirmed_insights": [
            {
                "claim": "对你来说，先做 worked example 再 drill 比直接刷题有效",
                "scope": "exam_sprint",
                "confidence": 0.85,
                "recommended_future_use": "在新计划中默认这个策略",
            }
        ],
        "pending_review": ["chron-1"],
        "generated_at": "2026-05-02T15:00:00",
    }

    with patch(
        "app.api.v1.growth.GrowthChronicleService.build_return_case_file",
        new=AsyncMock(return_value=case_payload),
    ) as mock_build:
        response = client.get("/growth/return-case-file?rebuild=true")

    assert response.status_code == 200
    body = response.json()
    assert body["chronicle_summary"]["confirmed_count"] == 3
    assert body["confirmed_insights"][0]["claim"].startswith("对你来说")
    assert body["source"] == "rebuild"
    mock_build.assert_awaited_once_with(str(user.id))


@pytest.mark.asyncio
async def test_return_case_file_cache_hit(growth_client, db_session):
    """GOAL-011: cached file returned without rebuilding."""
    client, state = growth_client
    user = User(
        username="returning_user_cached",
        email="returning_cached@example.com",
        hashed_password="hashed",
        nickname="Cha",
    )
    db_session.add(user)
    await db_session.commit()
    state["current_user"] = user

    cached = {
        "user_id": str(user.id),
        "chronicle_summary": {"total_entries": 2, "confirmed_count": 2, "pending_count": 0},
        "confirmed_insights": [],
        "pending_review": [],
        "generated_at": "2026-05-02T15:00:00",
    }

    fake_redis = AsyncMock()
    fake_redis.get = AsyncMock(return_value=json.dumps(cached))
    fake_redis.set = AsyncMock(return_value=True)

    with patch("app.api.v1.growth.cache_service") as mock_cache:
        mock_cache.redis = fake_redis
        with patch(
            "app.api.v1.growth.GrowthChronicleService.build_return_case_file",
            new=AsyncMock(),
        ) as mock_build:
            response = client.get("/growth/return-case-file")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "cache"
    assert body["chronicle_summary"]["confirmed_count"] == 2
    mock_build.assert_not_called()
