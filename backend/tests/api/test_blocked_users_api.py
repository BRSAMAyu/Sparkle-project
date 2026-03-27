from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db
from app.api.v1.community import router as community_router
from app.models.community import UserBlock
from app.models.user import User


def _make_user(*, username: str) -> User:
    return User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
        password_login_enabled=True,
        nickname=username,
        registration_source="email",
        is_active=True,
    )


async def _commit_all(db_session, *objects):
    db_session.add_all(list(objects))
    await db_session.commit()
    for obj in objects:
        await db_session.refresh(obj)


@pytest_asyncio.fixture
async def blocked_users_app(db_session):
    app = FastAPI()
    app.include_router(community_router, prefix="/community")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    yield app, state

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_get_blocked_users_returns_base_schema_fields(blocked_users_app, db_session):
    app, state = blocked_users_app
    blocker = _make_user(username="blocked_users_owner")
    blocked = _make_user(username="blocked_users_target")
    await _commit_all(db_session, blocker, blocked)

    block = UserBlock(
        blocker_id=blocker.id,
        blocked_id=blocked.id,
        reason="test block",
    )
    await _commit_all(db_session, block)

    state["current_user"] = blocker

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/community/users/blocked")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(block.id)
    assert payload[0]["blocked_user"]["id"] == str(blocked.id)
    assert payload[0]["reason"] == "test block"
