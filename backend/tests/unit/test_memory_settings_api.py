from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.deps import get_current_user, get_db
from app.api.v1.memory_settings import router
from app.config import settings
from app.core.memory_constants import PREFERENCE_KEYS
from app.models.user import User

app = FastAPI()
app.include_router(router, prefix="/api/v1")


@pytest.fixture
def enable_memory_controls(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_USER_MEMORY_CONTROLS", True, raising=False)


@pytest.mark.asyncio
async def test_memory_settings_get_and_update(db_session, enable_memory_controls):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_get_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/memory/settings")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["enabled"] is True
        assert payload["allow_inferred_episodic"] is True
        assert payload["capture_level"] == "medium"

        pref_key = sorted(PREFERENCE_KEYS)[0]
        update = await ac.put(
            "/api/v1/memory/settings",
            json={
                "allow_preferences": False,
                "capture_level": "low",
                "allow_inferred_episodic": False,
                "blocked_pref_keys": [pref_key],
                "blocked_sources": ["chat"],
            },
        )
        assert update.status_code == 200
        updated_payload = update.json()
        assert updated_payload["allow_preferences"] is False
        assert updated_payload["allow_inferred_episodic"] is False
        assert updated_payload["capture_level"] == "low"
        assert pref_key in updated_payload["blocked_pref_keys"]
        assert "chat" in updated_payload["blocked_sources"]

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_memory_settings_validation(db_session, enable_memory_controls):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_get_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.put(
            "/api/v1/memory/settings",
            json={"blocked_pref_keys": ["not_a_key"]},
        )
        assert resp.status_code == 422

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_push_settings_get_and_update(db_session, enable_memory_controls):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_get_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/memory/push-settings")
        assert resp.status_code == 200
        payload = resp.json()
        # FIX-45①：fresh GET 默认值跟随 settings.PUSH_OPT_IN_DEFAULT_ENABLED
        # （dailyflow DF-9，9957f42d：默认 True = opt-out 产品语义），而非旧断言的 False。
        default_enabled = bool(settings.PUSH_OPT_IN_DEFAULT_ENABLED)
        assert payload["enabled"] is default_enabled
        assert payload["quiet_hours_start"] == "22:00"

        # PUT 显式翻转总开关（相对默认值取反，钉住 update 链真的落库而非回显默认）
        update = await ac.put(
            "/api/v1/memory/push-settings",
            json={
                "enabled": not default_enabled,
                "allow_commitment_follow_up": True,
                "allow_engagement_recovery": True,
                "quiet_hours_start": "23:00",
                "quiet_hours_end": "07:00",
            },
        )
        assert update.status_code == 200
        updated_payload = update.json()
        assert updated_payload["enabled"] is (not default_enabled)
        assert updated_payload["allow_commitment_follow_up"] is True
        assert updated_payload["allow_engagement_recovery"] is True
        assert updated_payload["quiet_hours_start"] == "23:00"
        assert updated_payload["quiet_hours_end"] == "07:00"

    app.dependency_overrides = {}
