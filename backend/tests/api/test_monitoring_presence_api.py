from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.api.v1.monitoring as monitoring_module
from app.api.deps import get_current_active_superuser, get_current_user
from app.api.v1.monitoring import router as monitoring_router
from app.db.session import get_db
from app.models.community import Friendship, FriendshipStatus, Group, GroupMember, GroupRole, GroupType
from app.models.user import User


@pytest.fixture
def monitoring_client(db_session, monkeypatch):
    app = FastAPI()
    app.include_router(monitoring_router, prefix="/monitoring")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    monkeypatch.setattr(monitoring_module.manager, "is_user_online", AsyncMock(return_value=True))

    with TestClient(app) as client:
        yield client, state


async def _user(db_session, username: str, *, is_superuser: bool = False) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
        is_superuser=is_superuser,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_online_presence_allows_self(db_session, monitoring_client) -> None:
    client, state = monitoring_client
    user = await _user(db_session, "presence_self")
    await db_session.commit()
    state["current_user"] = user

    response = client.get(f"/monitoring/online/{user.id}")

    assert response.status_code == 200
    assert response.json()["online"] is True


@pytest.mark.asyncio
async def test_online_presence_rejects_unrelated_user(db_session, monitoring_client) -> None:
    client, state = monitoring_client
    viewer = await _user(db_session, "presence_viewer")
    target = await _user(db_session, "presence_target")
    await db_session.commit()
    state["current_user"] = viewer

    response = client.get(f"/monitoring/online/{target.id}")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_online_presence_allows_friend(db_session, monitoring_client) -> None:
    client, state = monitoring_client
    viewer = await _user(db_session, "presence_friend_viewer")
    target = await _user(db_session, "presence_friend_target")
    db_session.add(
        Friendship(
            user_id=viewer.id,
            friend_id=target.id,
            initiated_by=viewer.id,
            status=FriendshipStatus.ACCEPTED,
        )
    )
    await db_session.commit()
    state["current_user"] = viewer

    response = client.get(f"/monitoring/online/{target.id}")

    assert response.status_code == 200
    assert response.json()["online"] is True


@pytest.mark.asyncio
async def test_online_presence_allows_shared_group_member(db_session, monitoring_client) -> None:
    client, state = monitoring_client
    viewer = await _user(db_session, "presence_group_viewer")
    target = await _user(db_session, "presence_group_target")
    group = Group(name="presence-group", type=GroupType.SQUAD)
    db_session.add(group)
    await db_session.flush()
    db_session.add_all(
        [
            GroupMember(group_id=group.id, user_id=viewer.id, role=GroupRole.MEMBER),
            GroupMember(group_id=group.id, user_id=target.id, role=GroupRole.MEMBER),
        ]
    )
    await db_session.commit()
    state["current_user"] = viewer

    response = client.get(f"/monitoring/online/{target.id}")

    assert response.status_code == 200
    assert response.json()["online"] is True


@pytest.mark.asyncio
async def test_monitoring_stats_and_metrics_require_superuser(db_session, monitoring_client) -> None:
    client, _ = monitoring_client

    def _forbidden_superuser():
        raise HTTPException(status_code=403, detail="forbidden")

    client.app.dependency_overrides[get_current_active_superuser] = _forbidden_superuser

    assert client.get("/monitoring/stats").status_code == 403
    assert client.get("/monitoring/metrics").status_code == 403
