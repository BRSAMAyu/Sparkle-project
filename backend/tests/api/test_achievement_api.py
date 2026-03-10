from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.achievements import router as achievements_router
from app.db.session import get_db


@pytest.fixture
def achievement_client():
    app = FastAPI()
    app.include_router(achievements_router, prefix="/achievements")

    async def _override_get_db():
        yield MagicMock(spec=AsyncSession)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

    with TestClient(app) as test_client:
        yield test_client


def test_close_to_unlock_endpoint_returns_nested_progress_shape(achievement_client):
    payload = [
        {
            "achievement": {
                "id": "speed_learner",
                "name": "速通大师",
                "description": "24小时内解锁20个新知识点",
                "icon_url": "/icons/achievements/speed_learner.png",
                "type": "hidden",
                "rarity": "epic",
                "category": "hidden",
                "is_hidden": True,
                "hint": "效率至上...",
                "sort_order": 103,
                "parent_id": None,
                "trigger_code": "SPEED_UNLOCK",
                "trigger_config": {"count": 20, "hours": 24},
                "prerequisites": None,
                "visual_effect_type": "supernova",
                "visual_config": {"particle_count": 100, "expansion_speed": 2.0},
                "reward_config": [{"type": "title", "value": "speed_learner", "display": "速通大师"}],
                "total_unlocked": 0,
                "created_at": "2026-03-10T00:00:00",
                "updated_at": "2026-03-10T00:00:00",
            },
            "user_progress": {
                "user_id": str(uuid4()),
                "achievement_id": "speed_learner",
                "progress": 0.8,
                "progress_value": 16,
                "progress_target": 20,
                "is_pinned": False,
                "share_count": 0,
                "is_first_unlocker": False,
                "unlocked_at": None,
                "last_progress_update": None,
            },
            "is_unlocked": False,
            "progress_percentage": 80,
        }
    ]

    with patch(
        "app.api.v1.achievements.AchievementEngine.get_close_to_unlock_achievements",
        new=AsyncMock(return_value=payload),
    ):
        response = achievement_client.get("/achievements/close-to-unlock")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["data"][0]["achievement"]["id"] == "speed_learner"
    assert body["data"][0]["user_progress"]["progress_value"] == 16
    assert body["data"][0]["progress_percentage"] == 80
