from datetime import datetime
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
from app.models.achievement import AchievementRarity, AchievementType, VisualEffectType
from app.schemas.achievement import AchievementDetail, AchievementShareResponse


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


def _achievement_detail() -> AchievementDetail:
    return AchievementDetail(
        id="speed_learner",
        name="速通大师",
        description="24小时内解锁20个新知识点",
        icon_url="/icons/achievements/speed_learner.png",
        type=AchievementType.HIDDEN,
        rarity=AchievementRarity.EPIC,
        category="hidden",
        is_hidden=True,
        hint="效率至上...",
        sort_order=103,
        parent_id=None,
        trigger_code="SPEED_UNLOCK",
        trigger_config={"count": 20, "hours": 24},
        prerequisites=None,
        visual_effect_type=VisualEffectType.SUPERNOVA,
        visual_config={"particle_count": 100, "expansion_speed": 2.0},
        reward_config=[{"type": "title", "value": "speed_learner", "display": "速通大师"}],
        total_unlocked=0,
        created_at=datetime(2026, 3, 10, 0, 0, 0),
        updated_at=datetime(2026, 3, 10, 0, 0, 0),
    )


def test_share_endpoint_supports_canonical_and_deprecated_routes(achievement_client):
    payload = AchievementShareResponse(
        card_url="/uploads/achievement-cards/user-1/speed_learner_v1.png",
        mime_type="image/png",
        width=1080,
        height=1440,
        generated_at=datetime(2026, 3, 10, 10, 0, 0),
        achievement=_achievement_detail(),
    )

    with patch(
        "app.api.v1.achievements._share_achievement_card",
        new=AsyncMock(return_value=payload),
    ):
        canonical = achievement_client.post("/achievements/speed_learner/share")
        deprecated = achievement_client.post("/achievements/achievements/speed_learner/share")

    assert canonical.status_code == 200
    assert deprecated.status_code == 200
    assert canonical.json()["card_url"] == payload.card_url
    assert deprecated.json()["mime_type"] == "image/png"
    assert canonical.json()["achievement"]["id"] == "speed_learner"


def test_process_achievement_event_requires_internal_token(achievement_client):
    with patch("app.api.v1.achievements.settings.INTERNAL_API_KEY", "secret-key"):
        response = achievement_client.post(
            "/achievements/events/process",
            params={"user_id": str(uuid4()), "event_type": "task_completed"},
            json={"task_id": "task-1"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid internal token"


def test_process_achievement_event_accepts_internal_token_and_user_id(achievement_client):
    unlocked = [
        {
            "achievement_id": "task_master",
            "name": "任务达人",
            "rarity": "rare",
            "visual_effect": {"pulse": True},
            "visual_effect_type": "supernova",
            "rewards": [{"type": "photon", "amount": 50}],
            "is_first": False,
            "unlocked_at": "2026-03-10T10:00:00",
        }
    ]

    with patch("app.api.v1.achievements.settings.INTERNAL_API_KEY", "secret-key"):
        with patch(
            "app.api.v1.achievements.AchievementEngine.process_event",
            new=AsyncMock(return_value=unlocked),
        ) as mocked_process:
            response = achievement_client.post(
                "/achievements/events/process",
                params={"user_id": str(uuid4()), "event_type": "task_completed"},
                json={"task_id": "task-1"},
                headers={"X-Internal-Token": "secret-key", "Idempotency-Key": "achv-evt-1"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["unlocked_count"] == 1
    assert body["unlocked"][0]["achievement_id"] == "task_master"
    mocked_process.assert_awaited_once()


def test_process_achievement_event_requires_idempotency_key(achievement_client):
    with patch("app.api.v1.achievements.settings.INTERNAL_API_KEY", "secret-key"):
        response = achievement_client.post(
            "/achievements/events/process",
            params={"user_id": str(uuid4()), "event_type": "task_completed"},
            json={"task_id": "task-1"},
            headers={"X-Internal-Token": "secret-key"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Idempotency-Key header is required"


def test_share_templates_route_is_not_shadowed_by_dynamic_achievement_route(achievement_client):
    response = achievement_client.get("/achievements/share-templates?locale=zh")

    assert response.status_code == 200
    body = response.json()
    assert body["templates"]
    assert body["templates"][0]["id"]
