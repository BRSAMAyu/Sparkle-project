"""D-04 · capsule statistics period window tests.

`GET /capsules/stats` is a real per-user DB aggregation. The optional
`start` / `end` query parameters scope every counter (received / read /
favorited / feedback, including the average rating) to capsules, favorites
and feedback created inside the window. Nothing outside the window may leak
in, and nothing inside may be invented.
"""

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.capsules import router as capsules_router
from app.db.session import get_db
from app.models.capsule_favorite import CapsuleFavorite
from app.models.capsule_feedback import CapsuleFeedback
from app.models.curiosity_capsule import CuriosityCapsule
from app.models.user import User


@pytest.fixture
def stats_client(db_session):
    app = FastAPI()
    app.include_router(capsules_router, prefix="/capsules")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


def _capsule(user_id, created_at, *, is_read=False):
    return CuriosityCapsule(
        user_id=user_id,
        title="capsule",
        content="content",
        is_read=is_read,
        created_at=created_at,
        updated_at=created_at,
    )


@pytest.mark.asyncio
async def test_stats_without_window_counts_all_history(db_session, stats_client):
    """Regression: no start/end → previous all-time behaviour is preserved."""
    client, state = stats_client
    user = User(
        username="caps_stats_all",
        email="caps_stats_all@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    state["current_user"] = user

    now = datetime.utcnow()
    db_session.add_all([
        _capsule(user.id, now - timedelta(days=90), is_read=True),
        _capsule(user.id, now - timedelta(days=1), is_read=True),
        _capsule(user.id, now - timedelta(days=1)),
    ])
    await db_session.commit()

    response = client.get("/capsules/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_received"] == 3
    assert payload["total_read"] == 2
    assert payload["total_favorited"] == 0
    assert payload["total_feedback_given"] == 0
    assert payload["average_rating_given"] is None


@pytest.mark.asyncio
async def test_stats_period_window_scopes_every_counter(db_session, stats_client):
    client, state = stats_client
    user = User(
        username="caps_stats_window",
        email="caps_stats_window@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    state["current_user"] = user

    now = datetime.utcnow()
    window_start = now - timedelta(days=30)
    window_end = now + timedelta(days=1)

    in_window_read = _capsule(user.id, now - timedelta(days=10), is_read=True)
    in_window_unread = _capsule(user.id, now - timedelta(days=5))
    out_of_window_old = _capsule(user.id, now - timedelta(days=60), is_read=True)
    future = _capsule(user.id, now + timedelta(days=2))
    db_session.add_all([in_window_read, in_window_unread, out_of_window_old, future])
    await db_session.commit()

    favorite_in = CapsuleFavorite(
        user_id=user.id,
        capsule_id=in_window_read.id,
        created_at=now - timedelta(days=9),
        updated_at=now - timedelta(days=9),
    )
    favorite_out = CapsuleFavorite(
        user_id=user.id,
        capsule_id=out_of_window_old.id,
        created_at=now - timedelta(days=59),
        updated_at=now - timedelta(days=59),
    )
    feedback_in_5 = CapsuleFeedback(
        user_id=user.id,
        capsule_id=in_window_read.id,
        rating=5,
        created_at=now - timedelta(days=8),
        updated_at=now - timedelta(days=8),
    )
    feedback_in_1 = CapsuleFeedback(
        user_id=user.id,
        capsule_id=in_window_unread.id,
        rating=1,
        created_at=now - timedelta(days=4),
        updated_at=now - timedelta(days=4),
    )
    feedback_out = CapsuleFeedback(
        user_id=user.id,
        capsule_id=out_of_window_old.id,
        rating=5,
        created_at=now - timedelta(days=58),
        updated_at=now - timedelta(days=58),
    )
    db_session.add_all([favorite_in, favorite_out, feedback_in_5, feedback_in_1, feedback_out])
    await db_session.commit()

    response = client.get(
        "/capsules/stats",
        params={
            "start": window_start.isoformat() + "Z",
            "end": window_end.isoformat() + "Z",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_received"] == 2  # in-window only
    assert payload["total_read"] == 1
    assert payload["total_favorited"] == 1
    assert payload["total_feedback_given"] == 2
    # (5 + 1) / 2 — the out-of-window 5-star feedback must not leak in
    assert payload["average_rating_given"] == pytest.approx(3.0)


@pytest.mark.asyncio
async def test_stats_window_excludes_other_users(db_session, stats_client):
    client, state = stats_client
    user = User(
        username="caps_stats_owner",
        email="caps_stats_owner@example.com",
        hashed_password="hashed",
    )
    other = User(
        username="caps_stats_other",
        email="caps_stats_other@example.com",
        hashed_password="hashed",
    )
    db_session.add_all([user, other])
    await db_session.commit()
    state["current_user"] = user

    now = datetime.utcnow()
    db_session.add_all([
        _capsule(user.id, now - timedelta(days=1), is_read=True),
        _capsule(other.id, now - timedelta(days=1), is_read=True),
        _capsule(other.id, now - timedelta(days=1)),
    ])
    await db_session.commit()

    response = client.get(
        "/capsules/stats",
        params={
            "start": (now - timedelta(days=30)).isoformat() + "Z",
            "end": (now + timedelta(days=1)).isoformat() + "Z",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_received"] == 1
    assert payload["total_read"] == 1
