import json
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.schemas.user import UserRegister
from app.services.user_service import UserService


def _result_with_scalar(value):
    result = Mock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_get_by_email_returns_user():
    db = AsyncMock()
    user = Mock()
    user.email = "test@example.com"
    db.execute.return_value = _result_with_scalar(user)

    found = await UserService.get_by_email(db, "test@example.com")
    assert found is user


@pytest.mark.asyncio
async def test_create_user_hashes_password():
    db = AsyncMock()
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
    db = AsyncMock()
    user = Mock()
    db.execute.return_value = _result_with_scalar(user)
    service = UserService(db, redis_client=None)

    found = await service.get_user_by_id(uuid4())
    assert found is user


@pytest.mark.asyncio
async def test_get_context_uses_cache():
    db = AsyncMock()
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
    }
    redis.get.return_value = json.dumps(cached_payload)

    service = UserService(db, redis)
    context = await service.get_context(user_id)
    assert context is not None
    assert context.nickname == "cached_user"
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_context_returns_none_for_missing_user():
    db = AsyncMock()
    redis = AsyncMock()
    redis.get.return_value = None
    service = UserService(db, redis)
    service.get_user_by_id = AsyncMock(return_value=None)

    context = await service.get_context(uuid4())
    assert context is None
