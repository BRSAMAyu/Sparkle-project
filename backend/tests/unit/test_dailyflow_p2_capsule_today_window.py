"""P2-H (daily-flow R2): capsules/today windowing + once-per-day generation.

Verdict from the R2 evidence archive: the endpoint never actually returned
"0 rows" — the same D1 unread capsule came back every day ("复读"), and the
missing daily regeneration was a *consequence*: auto-generation only fired
when the (unfiltered) unread list was empty. Today-windowing + a per-day
generation guard fix both without re-entering the 24s sync LLM path on
repeat calls.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4, UUID

import pytest

from app.models.curiosity_capsule import CuriosityCapsule
from app.services.curiosity_capsule_service import curiosity_capsule_service


def _capsule(*, user_id: UUID, created_at: datetime, is_read: bool = False) -> CuriosityCapsule:
    return CuriosityCapsule(
        user_id=user_id,
        title="t",
        content="c",
        related_subject="s",
        is_read=is_read,
        created_at=created_at,
    )


@pytest.mark.asyncio
async def test_today_capsules_excludes_older_unread_capsules(db_session):
    user_id = uuid4()
    db_session.add(_capsule(user_id=user_id, created_at=datetime.now() - timedelta(days=2)))
    db_session.add(_capsule(user_id=user_id, created_at=datetime.now()))
    await db_session.commit()

    rows = await curiosity_capsule_service.get_today_capsules(user_id, db_session)
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_has_generated_today_counts_read_capsules_too(db_session):
    user_id = uuid4()
    db_session.add(_capsule(user_id=user_id, created_at=datetime.now(), is_read=True))
    await db_session.commit()

    assert await curiosity_capsule_service.has_generated_today(user_id, db_session) is True
    assert await curiosity_capsule_service.has_generated_today(uuid4(), db_session) is False


@pytest.mark.asyncio
async def test_today_endpoint_does_not_regenerate_after_todays_capsule_was_read(db_session, monkeypatch):
    """Read today's capsule → endpoint returns [] but must NOT regenerate."""
    from app.api.deps import get_current_user
    from app.api.v1.capsules import router as capsules_router
    from app.db.session import get_db
    from app.models.user import User
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    user = User(username="p2h_user", email="p2h_user@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()
    db_session.add(_capsule(user_id=user.id, created_at=datetime.now(), is_read=True))
    await db_session.commit()

    generate_calls: list = []

    async def _spy_generate(*args, **kwargs):
        generate_calls.append(1)
        return None

    monkeypatch.setattr(
        "app.api.v1.capsules.curiosity_capsule_service.generate_daily_capsule",
        _spy_generate,
    )

    app = FastAPI()
    app.include_router(capsules_router, prefix="/capsules")

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: user

    with TestClient(app) as client:
        resp = client.get("/capsules/today")

    assert resp.status_code == 200
    assert resp.json() == []
    assert generate_calls == [], "today's capsule already existed (read); must not re-enter generation"


@pytest.mark.asyncio
async def test_today_endpoint_still_generates_on_a_fresh_day(db_session, monkeypatch):
    """Old unread capsule + nothing generated today → fresh generation runs
    (this is the daily regeneration the eval asked for)."""
    from app.api.deps import get_current_user
    from app.api.v1.capsules import router as capsules_router
    from app.db.session import get_db
    from app.models.user import User
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    user = User(username="p2h_user2", email="p2h_user2@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()
    db_session.add(_capsule(user_id=user.id, created_at=datetime.now() - timedelta(days=1)))
    await db_session.commit()

    fresh = SimpleNamespace(
        id=uuid4(),
        user_id=user.id,
        title="fresh",
        content="c",
        related_subject="s",
        capsule_type=None,
        is_read=False,
        created_at=datetime.now(),
        depth_level=None,
        related_task_id=None,
        feedback=None,
        is_favorited=False,
    )

    async def _fake_generate(*args, **kwargs):
        return fresh

    monkeypatch.setattr(
        "app.api.v1.capsules.curiosity_capsule_service.generate_daily_capsule",
        _fake_generate,
    )

    app = FastAPI()
    app.include_router(capsules_router, prefix="/capsules")

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: user

    with TestClient(app) as client:
        resp = client.get("/capsules/today")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1 and body[0]["title"] == "fresh"
