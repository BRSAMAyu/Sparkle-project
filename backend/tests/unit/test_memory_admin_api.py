from datetime import UTC, datetime
from uuid import uuid4

def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


import pytest
from fastapi import FastAPI, HTTPException
from httpx import AsyncClient, ASGITransport

from app.api.v1.memory_admin import router
from app.api.deps import get_current_active_superuser, get_db
from app.config import settings
from app.models.memory import MemoryPreference
from app.models.user import User

app = FastAPI()
app.include_router(router, prefix="/api/v1")


@pytest.mark.asyncio
async def test_memory_admin_access_control(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_GOVERNANCE", True, raising=False)

    async def override_get_db():
        yield db_session

    def override_superuser_forbidden():
        raise HTTPException(status_code=403, detail="forbidden")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_superuser] = override_superuser_forbidden

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/admin/memory/stats")
        assert resp.status_code == 403

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_memory_admin_stats_shape(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_GOVERNANCE", True, raising=False)

    user_id = uuid4()
    admin_user = User(
        id=user_id,
        username=f"admin_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(admin_user)

    pref = MemoryPreference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.5},
        version=1,
        evidence_missing=True,
        evidence_checked_at=_utcnow(),
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    db_session.add(pref)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_superuser():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_superuser] = override_superuser

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/admin/memory/stats")
        assert resp.status_code == 200
        payload = resp.json()
        assert "counts" in payload
        assert "preferences" in payload["counts"]

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_memory_admin_health_snapshot(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_GOVERNANCE", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_HEALTH_SNAPSHOT", True, raising=False)

    user_id = uuid4()
    admin_user = User(
        id=user_id,
        username=f"admin_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(admin_user)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_superuser():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_superuser] = override_superuser

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/admin/memory/health-snapshot")
        assert resp.status_code == 200
        payload = resp.json()
        assert "evidence_missing_rate" in payload

    app.dependency_overrides = {}
