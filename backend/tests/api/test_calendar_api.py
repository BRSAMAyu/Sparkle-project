from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.calendar import router as calendar_router
from app.db.session import get_db
from app.models.calendar_event import CalendarEvent
from app.models.user import User


@pytest.fixture
def calendar_client(db_session):
    app = FastAPI()
    app.include_router(calendar_router, prefix="/calendar")

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
async def test_soft_delete_and_restore_round_trip_keeps_deleted_at_naive(db_session, calendar_client):
    client, state = calendar_client
    user = User(
        username="calendar_delete_user",
        email="calendar_delete_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    event = CalendarEvent(
        user_id=user.id,
        title="Delete me",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(hours=1),
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    state["current_user"] = user

    delete_response = client.delete(f"/calendar/{event.id}")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"success": True}

    await db_session.refresh(event)
    assert event.deleted_at is not None
    assert event.deleted_at.tzinfo is None

    restore_response = client.post(f"/calendar/{event.id}/restore")

    assert restore_response.status_code == 200
    assert restore_response.json()["success"] is True

    await db_session.refresh(event)
    assert event.deleted_at is None


@pytest.mark.asyncio
async def test_batch_delete_uses_same_soft_delete_contract(db_session, calendar_client):
    client, state = calendar_client
    user = User(
        username="calendar_batch_user",
        email="calendar_batch_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    event = CalendarEvent(
        user_id=user.id,
        title="Batch delete me",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(hours=1),
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    state["current_user"] = user

    response = client.post(
        "/calendar/batch",
        json={
            "operations": [
                {
                    "action": "delete",
                    "event_id": str(event.id),
                }
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success_count"] == 1
    assert body["failure_count"] == 0

    await db_session.refresh(event)
    assert event.deleted_at is not None
    assert event.deleted_at.tzinfo is None
