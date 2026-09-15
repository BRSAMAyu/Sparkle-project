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


@pytest.fixture
def enable_memory_panel(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_PANEL", True, raising=False)


@pytest.mark.asyncio
async def test_memory_api_list_and_history(db_session, enable_memory_panel):
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
        pref_value={"value": 0.4},
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.9},
        evidence_refs=[{"type": "event", "id": "evt_2"}],
    )

    await service.create_goal(
        user_id=user_id,
        title="Goal One",
        status="active",
        evidence_refs=[{"type": "event", "id": "evt_3"}],
    )

    await service.create_episodic_memory(
        user_id=user_id,
        summary="Memory One",
        source_type="analysis",
        source_id="src_1",
        occurred_at=_utcnow(),
        importance_score=0.6,
        tags=["execution"],
        evidence_refs=[{"type": "event", "id": "evt_4"}],
    )

    async def override_get_db():
        yield db_session

    async def override_get_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        pref_resp = await ac.get("/api/v1/memory/preferences")
        assert pref_resp.status_code == 200
        pref_items = pref_resp.json()["items"]
        assert pref_items[0]["pref_key"] == "depth_preference"

        history_resp = await ac.get(
            "/api/v1/memory/preferences/depth_preference/history"
        )
        assert history_resp.status_code == 200
        assert len(history_resp.json()["items"]) == 2

        goals_resp = await ac.get("/api/v1/memory/goals")
        assert goals_resp.status_code == 200
        assert goals_resp.json()["items"][0]["title"] == "Goal One"

        episodic_resp = await ac.get("/api/v1/memory/episodic")
        assert episodic_resp.status_code == 200
        assert episodic_resp.json()["items"][0]["summary"] == "Memory One"

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_memory_api_retract_flag(db_session, monkeypatch, enable_memory_panel):
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
    record = await service.create_episodic_memory(
        user_id=user_id,
        summary="Memory Two",
        source_type="analysis",
        source_id="src_2",
        occurred_at=_utcnow(),
        importance_score=0.4,
        tags=["cognitive"],
        evidence_refs=[{"type": "event", "id": "evt_5"}],
    )

    async def override_get_db():
        yield db_session

    async def override_get_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_user

    monkeypatch.setattr(settings, "ENABLE_MEMORY_RETRACTION", False, raising=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/memory/retract",
            json={"type": "episodic", "id": str(record.id), "reason": "user"},
        )
        assert resp.status_code == 403

    monkeypatch.setattr(settings, "ENABLE_MEMORY_RETRACTION", True, raising=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/memory/retract",
            json={"type": "episodic", "id": str(record.id), "reason": "user"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "retracted"

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_memory_api_correction_actions(db_session, monkeypatch, enable_memory_panel):
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
    preference = await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.6},
        evidence_refs=[{"type": "event", "id": "evt_10"}],
        confidence=0.6,
    )

    async def override_get_db():
        yield db_session

    async def override_get_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_user

    monkeypatch.setattr(settings, "ENABLE_MEMORY_CORRECTION", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_RETRACTION", True, raising=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/memory/correct",
            json={
                "type": "preference",
                "id": str(preference.id),
                "action": "lower_confidence",
                "reason": "user",
            },
        )
        assert resp.status_code == 200
        payload = resp.json()["item"]
        assert payload["confidence"] == pytest.approx(0.5)
        assert payload["correction_count"] == 1

        resp = await ac.post(
            "/api/v1/memory/correct",
            json={
                "type": "preference",
                "id": str(preference.id),
                "action": "reject",
                "reason": "user",
            },
        )
        assert resp.status_code == 200
        payload = resp.json()["item"]
        assert payload["retracted_at"] is not None
        assert payload["correction_count"] == 2

    app.dependency_overrides = {}
