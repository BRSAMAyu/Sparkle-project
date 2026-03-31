from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1 import profile_transparency as profile_api
from app.api.v1.profile_transparency import router as profile_router
from app.core.cache import cache_service
from app.db.session import get_db
from app.models.user import User
from app.services.memory_service import MemoryService
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_write_service import ProfileWriteService


@pytest.fixture
def profile_client(db_session):
    app = FastAPI()
    app.include_router(profile_router)

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


def test_override_inferred_rejects_non_adjustable_key(profile_client):
    client, state = profile_client
    state["current_user"] = type("UserStub", (), {"id": uuid4()})()

    response = client.post(
        "/profile/override-inferred",
        json={"key": "community_engagement_level", "value": "high"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "key is not adjustable"


def test_reset_override_requires_key(profile_client):
    client, state = profile_client
    state["current_user"] = type("UserStub", (), {"id": uuid4()})()

    response = client.post("/profile/reset-override", json={"key": ""})

    assert response.status_code == 400
    assert response.json()["detail"] == "key required"


def test_inferred_preferences_returns_behavioral_baseline_for_sparse_user(profile_client):
    client, state = profile_client
    state["current_user"] = type("UserStub", (), {"id": uuid4()})()

    response = client.get("/profile/inferred-preferences")

    assert response.status_code == 200
    payload = response.json()
    keys = {item["key"] for item in payload}
    assert "avg_question_complexity" in keys
    assert "community_engagement_level" in keys
    assert "social_learning_preference" in keys


@pytest.mark.asyncio
async def test_preference_rollback_restores_inferred_backup(profile_client, db_session):
    client, state = profile_client
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    state["current_user"] = type("UserStub", (), {"id": user_id})()

    class _RedisStub:
        def __init__(self) -> None:
            self._store: dict[str, dict[str, str]] = {}
            self._ttl: dict[str, int] = {}

        async def hset(self, key: str, field: str, value: str) -> None:
            self._store.setdefault(key, {})[field] = value

        async def hget(self, key: str, field: str) -> str | None:
            return self._store.get(key, {}).get(field)

        async def hgetall(self, key: str) -> dict[str, str]:
            return dict(self._store.get(key, {}))

        async def hdel(self, key: str, field: str) -> None:
            if key in self._store:
                self._store[key].pop(field, None)

        async def expire(self, key: str, ttl: int) -> None:
            self._ttl[key] = ttl

        async def get(self, key: str) -> str | None:
            return None

        async def setex(self, key: str, ttl: int, value: str) -> None:
            self._ttl[key] = ttl

        async def delete(self, *keys: str) -> None:
            return None

    redis = _RedisStub()
    original_redis = cache_service.redis
    cache_service.redis = redis
    profile_api.cache_service.redis = redis

    try:
        pref_service = PreferenceService(db_session, redis=redis)
        await pref_service.update_explicit(user_id, {"community_engagement_level": "low"})
        await pref_service.update_inferred(user_id, {"community_engagement_level": "moderate"})

        service = ProfileWriteService(db_session, redis=redis)
        await service.override_inferred_preference(
            user_id=user_id,
            pref_key="community_engagement_level",
            pref_value={"value": "high"},
            evidence_refs=[{"type": "user_state", "id": "override", "schema_version": "test.v1"}],
            source="override_test",
        )
        memory_service = MemoryService(db_session)
        await memory_service.upsert_preference(
            user_id=user_id,
            pref_key="community_engagement_level",
            pref_value={"value": "low"},
            evidence_refs=[{"type": "user_state", "id": "history-low"}],
            source_type="user_state",
        )
        await memory_service.upsert_preference(
            user_id=user_id,
            pref_key="community_engagement_level",
            pref_value={"value": "high"},
            evidence_refs=[{"type": "user_state", "id": "history-high"}],
            source_type="user_state",
        )

        response = client.post(
            "/profile/preferences/rollback",
            json={"pref_key": "community_engagement_level"},
        )

        assert response.status_code == 200

        prefs = await pref_service.get_preferences(user_id)
        backups = await service.list_inferred_backups(user_id)

        assert prefs.explicit["community_engagement_level"] == "low"
        assert prefs.inferred["community_engagement_level"] == "moderate"
        assert "community_engagement_level" not in backups
    finally:
        cache_service.redis = original_redis
        profile_api.cache_service.redis = original_redis
