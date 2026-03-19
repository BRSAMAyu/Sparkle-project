from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import and_, select

from app.api.deps import get_current_user
from app.api.v1.visual_elements import router as visual_elements_router
from app.db.session import get_db
from app.models.achievement import UserAchievement
from app.models.user import User
from app.models.visual_element import (
    UserVisualElement,
    VisualElement,
    VisualElementRarity,
    VisualElementType,
    VisualElementUnlockSource,
)


@pytest.fixture
def visual_client(db_session):
    app = FastAPI()
    app.include_router(visual_elements_router, prefix="/visual-elements")

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
async def test_unlock_by_achievement_rejects_locked_achievement(db_session, visual_client):
    client, state = visual_client
    user = User(
        username="visual_lock_user",
        email="visual_lock_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    db_session.add(
        VisualElement(
            id="bg_aurora",
            name="Aurora",
            description="Aurora background",
            element_type=VisualElementType.BACKGROUND,
            rarity=VisualElementRarity.RARE,
            unlock_source=VisualElementUnlockSource.ACHIEVEMENT,
            unlock_requirement={"achievement_id": "streak_30"},
            config={"gradient": ["#000", "#fff"]},
            is_active=True,
            is_default=False,
            sort_order=1,
        )
    )
    await db_session.commit()
    state["current_user"] = user

    response = client.post("/visual-elements/unlock-by-achievement", params={"achievement_id": "streak_30"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Achievement not unlocked"


@pytest.mark.asyncio
async def test_unlock_by_achievement_unlocks_only_for_owned_achievement(db_session, visual_client):
    client, state = visual_client
    user = User(
        username="visual_unlock_user",
        email="visual_unlock_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    db_session.add(
        VisualElement(
            id="bg_aurora",
            name="Aurora",
            description="Aurora background",
            element_type=VisualElementType.BACKGROUND,
            rarity=VisualElementRarity.RARE,
            unlock_source=VisualElementUnlockSource.ACHIEVEMENT,
            unlock_requirement={"achievement_id": "streak_30"},
            config={"gradient": ["#000", "#fff"]},
            is_active=True,
            is_default=False,
            sort_order=1,
        )
    )
    await db_session.flush()
    db_session.add(
        UserAchievement(
            user_id=user.id,
            achievement_id="streak_30",
            progress=1.0,
            progress_value=30,
            progress_target=30,
            unlocked_at=datetime.utcnow(),
        )
    )
    await db_session.commit()
    state["current_user"] = user

    response = client.post("/visual-elements/unlock-by-achievement", params={"achievement_id": "streak_30"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["success"] is True
    assert body[0]["element"]["id"] == "bg_aurora"

    await db_session.refresh(user)
    unlocked_result = await db_session.execute(
        select(UserVisualElement).where(
            and_(
                UserVisualElement.user_id == user.id,
                UserVisualElement.element_id == "bg_aurora",
            )
        )
    )
    unlocked = unlocked_result.scalar_one_or_none()
    assert unlocked is not None
    assert unlocked.unlock_source == "achievement"


def test_unlock_internal_requires_internal_token(visual_client):
    from unittest.mock import patch

    client, state = visual_client
    state["current_user"] = User(
        id="00000000-0000-0000-0000-000000000001",
        username="visual_internal_user",
        email="visual_internal_user@example.com",
        hashed_password="hashed",
    )

    with patch("app.api.v1.visual_elements.settings.INTERNAL_API_KEY", "secret-key"):
        response = client.post(
            "/visual-elements/unlock",
            json={
                "element_id": "bg_default_dark",
                "source": "system",
                "source_id": "seed",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid internal token"
