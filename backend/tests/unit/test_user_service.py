import json
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.models.user import User
from app.schemas.user import UserRegister
from app.services.personalization.preference_service import PreferenceService
from app.services.user_service import UserService


def _mock_db():
    db = AsyncMock()
    db.add = Mock()
    db.delete = Mock()
    return db


def _result_with_scalar(value):
    result = Mock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_get_by_email_returns_user():
    db = _mock_db()
    user = Mock()
    user.email = "test@example.com"
    db.execute.return_value = _result_with_scalar(user)

    found = await UserService.get_by_email(db, "test@example.com")
    assert found is user


@pytest.mark.asyncio
async def test_create_user_hashes_password():
    db = _mock_db()
    user_in = UserRegister(
        username="user1",
        email="u1@example.com",
        password="secret-123",
    )
    with patch("app.services.user_service.get_password_hash", return_value="hashed"):
        user = await UserService.create(db, user_in)
    assert user.hashed_password == "hashed"
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_id_from_db():
    db = _mock_db()
    user = Mock()
    db.execute.return_value = _result_with_scalar(user)
    service = UserService(db, redis_client=None)

    found = await service.get_user_by_id(uuid4())
    assert found is user


@pytest.mark.asyncio
async def test_get_context_uses_cache():
    db = _mock_db()
    redis = AsyncMock()
    user_id = uuid4()
    cached_payload = {
        "user_id": str(user_id),
        "nickname": "cached_user",
        "timezone": "Asia/Shanghai",
        "language": "zh-CN",
        "is_pro": False,
        "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5, "flame_level": 1, "flame_brightness": 0},
        "active_slots": {"slots": []},
        "daily_cap": 5,
        "persona_type": "coach",
        "preference_version": 0,
    }
    redis.get.return_value = json.dumps(cached_payload)

    service = UserService(db, redis)
    with patch.object(PreferenceService, "get_preference_version", new=AsyncMock(return_value=0)):
        context = await service.get_context(user_id)
        assert context is not None
        assert context.nickname == "cached_user"
        db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_context_returns_none_for_missing_user():
    db = _mock_db()
    redis = AsyncMock()
    redis.get.return_value = None
    service = UserService(db, redis)
    service.get_user_by_id = AsyncMock(return_value=None)

    context = await service.get_context(uuid4())
    assert context is None


class _RedisCache:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str):
        return self._store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self._store[key] = value

    async def delete(self, *keys: str):
        for key in keys:
            self._store.pop(key, None)


@pytest.mark.asyncio
async def test_get_context_refreshes_stale_cache_when_preference_version_changes(db_session):
    redis = _RedisCache()
    user = User(username="ctxversion", email="ctxversion@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = UserService(db_session, redis)
    first_context = await service.get_context(user.id)
    assert first_context is not None
    assert first_context.preference_version == 1
    stale_cache = dict(redis._store)

    await PreferenceService(db_session, redis).update_explicit(user.id, {"timezone": "America/New_York"})
    redis._store.update(stale_cache)

    refreshed = await service.get_context(user.id)

    assert refreshed is not None
    assert refreshed.timezone == "America/New_York"
    assert refreshed.preference_version == 2
