from datetime import timezone, datetime
from uuid import uuid4

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.v1.memory import router
from app.api.deps import get_current_user, get_db
from app.config import settings
from app.models.user import User
from app.services.memory_service import MemoryService

app = FastAPI()
app.include_router(router, prefix="/api/v1")


@pytest.mark.asyncio
async def test_memory_export_flag(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_PANEL", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_EXPORT", False, raising=False)

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

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/memory/export")
        assert resp.status_code == 404

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_memory_export_payload(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_PANEL", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_EXPORT", True, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    service = MemoryService(db_session)
    await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.6},
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    episodic = await service.create_episodic_memory(
        user_id=user_id,
        summary="Memory Export",
        source_type="analysis",
        source_id="src_1",
        occurred_at=_utcnow(),
        importance_score=0.5,
        tags=["cognitive"],
        evidence_refs=[{"type": "event", "id": "evt_2", "user_deleted": True}],
    )
    episodic.evidence_missing = True
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_get_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/memory/export")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["user_id"] == str(user_id)
        assert payload["preferences"][0]["pref_key"] == "depth_preference"
        episodic_item = payload["episodic"][0]
        assert episodic_item["evidence_missing"] is True
        assert "evidence_snapshot" in episodic_item

    app.dependency_overrides = {}
