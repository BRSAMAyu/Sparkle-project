from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.api.v1 import executions, executions_admin
from app.models.user import User

app = FastAPI()
app.include_router(executions.router, prefix="/api/v1")
app.include_router(executions_admin.router, prefix="/api/v1")


@pytest.mark.asyncio
async def test_user_execution_router_does_not_expose_quality_summary_or_node_invoke(db_session):
    async def override_get_db():
        yield db_session

    async def override_user():
        return User(
            id=uuid4(),
            username="exec_user",
            email="exec_user@example.com",
            hashed_password="hashed",
            is_active=True,
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        summary_resp = await ac.get("/api/v1/executions/quality/summary")
        invoke_resp = await ac.post(
            "/api/v1/executions/nodes/node-shell/invoke",
            json={"command": "system.run", "params": {}},
        )

    assert summary_resp.status_code == 404
    assert invoke_resp.status_code == 404
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_user_execution_connection_status_is_available(db_session, monkeypatch):
    async def override_get_db():
        yield db_session

    async def override_user():
        return User(
            id=uuid4(),
            username="exec_user_status",
            email="exec_user_status@example.com",
            hashed_password="hashed",
            is_active=True,
        )

    async def fake_health(self, *, user_id=None):
        return {
            "openclaw_enabled": True,
            "gateway_url": "http://openclaw.local",
            "transport": "gateway_ws",
            "ws_url": "ws://openclaw.local",
            "connection_source": "global",
            "reachable": True,
            "latency_ms": 42,
            "message": "gateway_ws",
            "capabilities": ["实时生命周期", "节点调用"],
            "supports_approvals": True,
            "ingestion_layer": "execution_ingestor",
            "connected_nodes": 2,
            "supports_nodes": True,
            "supports_templates": True,
            "supports_quality_loop": True,
            "degraded_user_count": 1,
            "degradation_threshold": 3,
        }

    monkeypatch.setattr("app.api.v1.executions.ExecutionService.get_health", fake_health)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        resp = await ac.get("/api/v1/executions/connection/status")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["reachable"] is True
    assert payload["latency_ms"] == 42
    assert payload["capabilities"]
    assert payload["degraded_user_count"] == 1
    assert payload["connected_nodes"] == 2
    assert payload["connection_source"] == "global"
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_user_execution_connection_profile_crud(db_session):
    user = User(
        id=uuid4(),
        username="exec_profile_user",
        email="exec_profile_user@example.com",
        hashed_password="hashed",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        put_resp = await ac.put(
            "/api/v1/executions/connection/profile",
            json={
                "gateway_url": "https://remote.openclaw.example",
                "auth_token": "secret-token",
                "transport": "gateway_ws",
            },
        )
        get_resp = await ac.get("/api/v1/executions/connection/profile")
        delete_resp = await ac.delete("/api/v1/executions/connection/profile")

    assert put_resp.status_code == 200
    assert get_resp.status_code == 200
    assert delete_resp.status_code == 200
    assert put_resp.json()["configured"] is True
    assert put_resp.json()["gateway_url"] == "https://remote.openclaw.example"
    assert put_resp.json()["ws_url"] == "wss://remote.openclaw.example"
    assert get_resp.json()["auth_token"] == "secret-token"
    assert delete_resp.json()["configured"] is False
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_user_execution_profile_summary_is_available(db_session, monkeypatch):
    async def override_get_db():
        yield db_session

    async def override_user():
        return User(
            id=uuid4(),
            username="exec_user_profile",
            email="exec_user_profile@example.com",
            hashed_password="hashed",
            is_active=True,
        )

    async def fake_profile(self, user_id, days=30):
        return {
            "days": days,
            "total_executions": 6,
            "success_rate": 0.67,
            "by_type": {
                "browser": {"total": 3, "succeeded": 2, "success_rate": 0.67},
            },
            "trust_distribution": {"trusted": 4, "validated": 1, "raw": 1},
            "approval_request_count": 2,
            "top_templates": [["web_research_brief", 3]],
            "delegation_trend": "stable",
        }

    monkeypatch.setattr(
        "app.api.v1.executions.ExecutionProfileService.get_execution_profile",
        fake_profile,
    )
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        resp = await ac.get("/api/v1/executions/profile/summary?days=14")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["days"] == 14
    assert payload["total_executions"] == 6
    assert payload["top_templates"][0][0] == "web_research_brief"
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_execution_admin_routes_require_superuser(db_session):
    async def override_get_db():
        yield db_session

    def override_superuser_forbidden():
        raise HTTPException(status_code=403, detail="forbidden")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_superuser] = override_superuser_forbidden

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        summary_resp = await ac.get("/api/v1/admin/executions/quality/summary")
        nodes_resp = await ac.get("/api/v1/admin/executions/nodes")

    assert summary_resp.status_code == 403
    assert nodes_resp.status_code == 403
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_execution_admin_quality_summary_available_for_superuser(db_session, monkeypatch):
    admin_user = User(
        id=uuid4(),
        username="exec_admin",
        email="exec_admin@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(admin_user)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_superuser():
        return admin_user

    async def fake_summary(self):
        return {
            "experiment_id": "exp-1",
            "experiment_name": "openclaw_execution_strategy_v1",
            "status": "running",
            "sample_size_collected": 3,
            "variants": [
                {
                    "variant_id": "var-1",
                    "variant_name": "balanced_control",
                    "is_control": True,
                    "configuration": {},
                    "sample_size": 3,
                    "success_rate": 1.0,
                    "avg_quality": 0.9,
                    "avg_latency": 1200.0,
                }
            ],
        }

    monkeypatch.setattr("app.api.v1.executions_admin.ExecutionService.get_quality_summary", fake_summary)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_superuser] = override_superuser

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        resp = await ac.get("/api/v1/admin/executions/quality/summary")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["experiment_name"] == "openclaw_execution_strategy_v1"
    assert payload["sample_size_collected"] == 3
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_execution_admin_dashboard_available_for_superuser(db_session, monkeypatch):
    admin_user = User(
        id=uuid4(),
        username="exec_admin_dashboard",
        email="exec_admin_dashboard@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(admin_user)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_superuser():
        return admin_user

    async def fake_health(self):
        return {
            "openclaw_enabled": True,
            "gateway_url": "http://openclaw.local",
            "transport": "gateway_ws",
            "ws_url": "ws://openclaw.local",
            "reachable": True,
            "supports_approvals": True,
            "ingestion_layer": "execution_ingestor",
            "connected_nodes": 1,
            "supports_nodes": True,
            "supports_templates": True,
            "supports_quality_loop": True,
            "degraded_user_count": 2,
            "degradation_threshold": 3,
        }

    async def fake_profile(self, *, days=30):
        return {
            "days": days,
            "total_executions": 12,
            "success_rate": 0.75,
            "by_type": {
                "browser": {"total": 7, "succeeded": 6, "success_rate": 0.86},
            },
            "trust_distribution": {"trusted": 8, "validated": 3, "raw": 1},
            "approval_request_count": 4,
            "top_templates": [["web_research_brief", 5]],
            "delegation_trend": "increasing",
        }

    monkeypatch.setattr("app.api.v1.executions_admin.ExecutionService.get_health", fake_health)
    monkeypatch.setattr(
        "app.api.v1.executions_admin.ExecutionProfileService.get_execution_profile_for_all_users",
        fake_profile,
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_superuser] = override_superuser

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        resp = await ac.get("/api/v1/admin/executions/dashboard")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_executions"] == 12
    assert payload["connected_nodes"] == 1
    assert payload["degraded_user_count"] == 2
    assert payload["degradation_threshold"] == 3
    assert payload["delegation_trend"] == "increasing"
    app.dependency_overrides = {}
