from datetime import timezone, datetime
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


import pytest
from fastapi import FastAPI, HTTPException
from httpx import AsyncClient, ASGITransport

from app.api.v1.memory_admin import router
from app.api.deps import get_current_active_superuser, get_db
from app.config import settings
from app.models.memory import EpisodicMemory, MemoryPreference
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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/admin/memory/health-snapshot")
        assert resp.status_code == 200
        payload = resp.json()
        assert "evidence_missing_rate" in payload

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_memory_admin_revoke_inferred_lane(db_session, monkeypatch):
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
    inferred = EpisodicMemory(
        user_id=user_id,
        summary="AI auto memory",
        source_type="chat",
        source_id="session_1",
        source_lane="inferred_extraction",
        occurred_at=_utcnow(),
        importance_score=0.9,
        confidence=0.9,
        evidence_refs=[{"type": "chat_turn", "id": str(uuid4())}],
        evidence_token=str(uuid4()),
        decay_policy="7d",
        semantic_key="ai-auto-memory",
    )
    db_session.add(inferred)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_superuser():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_superuser] = override_superuser

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/v1/admin/memory/inferred/revoke", json={})
        assert resp.status_code == 200
        assert resp.json()["revoked"] == 1

    await db_session.refresh(inferred)
    assert inferred.revoked_at is not None
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_memory_admin_stage18_kill_switches(db_session, monkeypatch):
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
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_superuser():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_superuser] = override_superuser

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        get_resp = await ac.get("/api/v1/admin/memory/stage18/killswitch")
        assert get_resp.status_code == 200
        assert "flags" in get_resp.json()

        put_resp = await ac.put(
            "/api/v1/admin/memory/stage18/killswitch",
            json={
                "aggregator_enabled": True,
                "push_policy_enabled": True,
                "push_delivery_enabled": False,
            },
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["flags"]["aggregator_enabled"] == "live"
        assert put_resp.json()["flags"]["push_policy_enabled"] == "live"
        assert put_resp.json()["flags"]["push_delivery_enabled"] == "off"

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_memory_admin_stage19_kill_switches(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_GOVERNANCE", True, raising=False)
    monkeypatch.setattr("app.services.aurora_stage19_kill_switch_service.cache_service.redis", None)

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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        get_resp = await ac.get("/api/v1/admin/memory/stage19/killswitch")
        assert get_resp.status_code == 200
        assert "flags" in get_resp.json()

        put_resp = await ac.put(
            "/api/v1/admin/memory/stage19/killswitch",
            json={
                "working_memory_enabled": True,
                "llm_extractor_enabled": True,
                "consolidation_enabled": False,
            },
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["flags"]["working_memory_enabled"] == "live"
        assert put_resp.json()["flags"]["llm_extractor_enabled"] == "live"
        assert put_resp.json()["flags"]["consolidation_enabled"] == "off"

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_memory_admin_stage21_kill_switches(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_GOVERNANCE", True, raising=False)
    monkeypatch.setattr("app.services.aurora_stage21_kill_switch_service.cache_service.redis", None)

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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        get_resp = await ac.get("/api/v1/admin/memory/stage21/killswitch")
        assert get_resp.status_code == 200
        assert "flags" in get_resp.json()

        put_resp = await ac.put(
            "/api/v1/admin/memory/stage21/killswitch",
            json={
                "skill_store_enabled": True,
                "skill_selection_enabled": True,
                "skill_share_enabled": False,
            },
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["flags"]["skill_store_enabled"] == "live"
        assert put_resp.json()["flags"]["skill_selection_enabled"] == "live"
        assert put_resp.json()["flags"]["skill_share_enabled"] == "off"

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_memory_admin_expanded_aurora_kill_switches(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_GOVERNANCE", True, raising=False)
    for module in (
        "app.services.aurora_stage23_kill_switch_service",
        "app.services.aurora_stage24_policy_kill_switch_service",
        "app.services.aurora_stage25_reflection_kill_switch_service",
        "app.services.aurora_stage26_scene_kill_switch_service",
        "app.services.aurora_stage27_foresight_kill_switch_service",
        "app.services.aurora_stage28_traits_kill_switch_service",
        "app.services.aurora_stage29_srl_kill_switch_service",
        "app.services.aurora_stage30_metacognition_kill_switch_service",
        "app.services.aurora_stage31_idiographic_kill_switch_service",
        "app.services.aurora_stage33_kill_switch_service",
    ):
        monkeypatch.setattr(f"{module}.cache_service.redis", None)

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

    cases = {
        "stage23": ({"mode": "live"}, "bayesian_mode"),
        "stage24": ({"mode": "shadow"}, "policy_compiler_mode"),
        "stage25": ({"mode": "live"}, "reflection_wire_mode"),
        "stage26": ({"mode": "shadow"}, "mode"),
        "stage27": ({"mode": "live", "attractor": "live", "deviation": "shadow", "jitai": "off"}, "mode"),
        "stage28": ({"mode": "live", "nlp_mode": "shadow", "coldstart_mode": "live"}, "mode"),
        "stage29": (
            {
                "mode": "live",
                "tracker_mode": "shadow",
                "bridge_mode": "live",
                "scaffolding_consume_mode": "shadow",
            },
            "mode",
        ),
        "stage30": (
            {
                "mode": "live",
                "dashboard": "live",
                "process_scaffolding": "shadow",
                "fsm_combine": "off",
            },
            "mode",
        ),
        "stage31": ({"mode": "shadow"}, "mode"),
        "stage33": (
            {
                "mode": "live",
                "social": "live",
                "srl": "shadow",
                "wm_prompt": "shadow",
                "events": "off",
            },
            "mode",
        ),
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for stage, (payload, asserted_key) in cases.items():
            put_resp = await ac.put(f"/api/v1/admin/memory/{stage}/killswitch", json=payload)
            assert put_resp.status_code == 200
            assert put_resp.json()["flags"][asserted_key] == payload["mode"]

            get_resp = await ac.get(f"/api/v1/admin/memory/{stage}/killswitch")
            assert get_resp.status_code == 200
            assert "flags" in get_resp.json()

    app.dependency_overrides = {}
