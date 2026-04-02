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
async def test_user_execution_connection_diagnostics_are_available(db_session, monkeypatch):
    async def override_get_db():
        yield db_session

    async def override_user():
        return User(
            id=uuid4(),
            username="exec_diag_user",
            email="exec_diag_user@example.com",
            hashed_password="hashed",
            is_active=True,
        )

    async def fake_diagnose(self, *, user_id=None):
        return {
            "reachable": False,
            "overall_status": "failed",
            "summary": "认证检查未通过：pairing required",
            "generated_at": "2026-04-02T12:00:00",
            "transport": "gateway_ws",
            "connection_source": "user_profile",
            "gateway_url": "https://remote.openclaw.example",
            "ws_url": "wss://remote.openclaw.example",
            "checks": [
                {
                    "key": "dns",
                    "label": "DNS 解析",
                    "status": "passed",
                    "message": "已解析到 1 个地址",
                    "details": {"addresses": ["100.64.0.8"]},
                },
                {
                    "key": "auth",
                    "label": "认证检查",
                    "status": "failed",
                    "message": "pairing required",
                    "suggestion": "重新配对当前设备",
                    "details": {"has_device_token": True},
                },
            ],
        }

    monkeypatch.setattr("app.api.v1.executions.ExecutionService.diagnose_connection", fake_diagnose)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        resp = await ac.get("/api/v1/executions/connection/diagnose")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["reachable"] is False
    assert payload["overall_status"] == "failed"
    assert payload["connection_source"] == "user_profile"
    assert len(payload["checks"]) == 2
    assert payload["checks"][1]["key"] == "auth"
    assert payload["checks"][1]["suggestion"] == "重新配对当前设备"
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
async def test_user_execution_preferences_crud(db_session):
    user = User(
        id=uuid4(),
        username="exec_preferences_user",
        email="exec_preferences_user@example.com",
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
            "/api/v1/executions/preferences",
            json={
                "mode": "custom",
                "custom_rules": {
                    "browser_read": "auto",
                    "shell_exec": "confirm",
                    "install": "reject",
                },
                "node_affinity": {
                    "browser": "node-macbook-pro",
                    "shell": "node-workstation",
                },
                "notification_level": "all",
                "auto_extend_timeout": False,
                "trust_auto_upgrade": True,
                "execution_budget": {
                    "daily_token_limit": 1200,
                    "monthly_token_limit": 6000,
                },
            },
        )
        get_resp = await ac.get("/api/v1/executions/preferences")

    assert put_resp.status_code == 200
    assert get_resp.status_code == 200
    assert put_resp.json()["mode"] == "custom"
    assert put_resp.json()["custom_rules"]["install"] == "reject"
    assert put_resp.json()["node_affinity"]["shell"] == "node-workstation"
    assert put_resp.json()["notification_level"] == "all"
    assert put_resp.json()["execution_budget"]["daily_token_limit"] == 1200
    assert get_resp.json()["execution_budget"]["monthly_token_limit"] == 6000
    assert get_resp.json()["summary"]
    assert "recommendations" in get_resp.json()
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_user_execution_nodes_are_available(db_session, monkeypatch):
    async def override_get_db():
        yield db_session

    async def override_user():
        return User(
            id=uuid4(),
            username="exec_nodes_user",
            email="exec_nodes_user@example.com",
            hashed_password="hashed",
            is_active=True,
        )

    async def fake_list_nodes(self, *, user_id=None, connected_only=True, last_connected=None):
        return [
            {
                "node_id": "node-shell",
                "name": "Sparkle Node",
                "platform": "macos",
                "connected": True,
                "status": "idle",
                "active_runs": 1,
                "last_seen": "2026-04-02T12:00:00",
                "commands": ["system.run"],
                "caps": ["system.run"],
            }
        ]

    monkeypatch.setattr("app.api.v1.executions.ExecutionService.list_nodes", fake_list_nodes)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        resp = await ac.get("/api/v1/executions/nodes")

    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 1
    assert payload[0]["node_id"] == "node-shell"
    assert payload[0]["active_runs"] == 1
    assert payload[0]["status"] == "idle"
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
async def test_user_execution_retry_endpoint(db_session, monkeypatch):
    async def override_get_db():
        yield db_session

    async def override_user():
        return User(
            id=uuid4(),
            username="exec_retry_user",
            email="exec_retry_user@example.com",
            hashed_password="hashed",
            is_active=True,
        )

    async def fake_retry(self, *, intent_id, user_id):  # noqa: ARG001
        class _FakeIntent:
            def __init__(self):
                self.id = intent_id
                self.task_id = uuid4()
                self.plan_id = None
                self.execution_mode = type("Mode", (), {"value": "agent"})()
                self.executor = type("Exec", (), {"value": "openclaw"})()
                self.target_env = None
                self.status = type("Status", (), {"value": "running"})()
                self.trust_level = type("Trust", (), {"value": "raw"})()
                self.external_run_id = None
                self.goal = "retry"
                self.error_category = None
                self.error_message = None
                self.dispatched_at = None
                self.completed_at = None
                self.created_at = None
                self.policy = {}

            def to_dict(self):
                return {
                    "id": str(self.id),
                    "task_id": str(self.task_id),
                    "plan_id": None,
                    "execution_mode": "agent",
                    "executor": "openclaw",
                    "target_env": None,
                    "status": "running",
                    "trust_level": "raw",
                    "external_run_id": None,
                    "goal": "retry",
                    "error_category": None,
                    "error_message": None,
                    "dispatched_at": None,
                    "completed_at": None,
                    "created_at": None,
                    "policy": {},
                }

        return _FakeIntent()

    monkeypatch.setattr("app.api.v1.executions.ExecutionService.retry_intent", fake_retry)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/executions/{uuid4()}/retry")

    assert resp.status_code == 200
    assert resp.json()["status"] == "running"
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_user_execution_batch_endpoint(db_session, monkeypatch):
    async def override_get_db():
        yield db_session

    async def override_user():
        return User(
            id=uuid4(),
            username="exec_batch_user",
            email="exec_batch_user@example.com",
            hashed_password="hashed",
            is_active=True,
        )

    async def fake_dispatch_batch(self, *, intent_ids, user_id, execution_strategy):  # noqa: ARG001
        return {
            "batch_id": "batch-1",
            "status": "partial",
            "requested_strategy": execution_strategy,
            "resolved_strategy": "parallel",
            "task_ids": ["task-1", "task-2"],
            "intent_ids": [str(item) for item in intent_ids],
            "completed_count": 1,
            "failed_count": 0,
            "queued_count": 1,
            "items": [
                {
                    "intent_id": str(intent_ids[0]),
                    "task_id": "task-1",
                    "status": "succeeded",
                    "target_env": "browser",
                    "error_message": None,
                }
            ],
        }

    monkeypatch.setattr("app.api.v1.executions.ExecutionService.dispatch_batch", fake_dispatch_batch)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/executions/batch/handoff",
            json={"intent_ids": [str(uuid4()), str(uuid4())], "execution_strategy": "auto"},
        )

    assert resp.status_code == 200
    assert resp.json()["resolved_strategy"] == "parallel"
    assert resp.json()["queued_count"] == 1
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_user_execution_task_batch_endpoint(db_session, monkeypatch):
    async def override_get_db():
        yield db_session

    async def override_user():
        return User(
            id=uuid4(),
            username="exec_task_batch_user",
            email="exec_task_batch_user@example.com",
            hashed_password="hashed",
            is_active=True,
        )

    async def fake_handoff_tasks_batch(self, *, task_ids, user_id, execution_strategy):  # noqa: ARG001
        return {
            "batch_id": "batch-task-1",
            "status": "completed",
            "requested_strategy": execution_strategy,
            "resolved_strategy": "sequential",
            "task_ids": [str(item) for item in task_ids],
            "intent_ids": [str(uuid4()) for _ in task_ids],
            "completed_count": len(task_ids),
            "failed_count": 0,
            "queued_count": 0,
            "items": [
                {
                    "intent_id": str(uuid4()),
                    "task_id": str(task_ids[0]),
                    "status": "succeeded",
                    "target_env": "browser",
                    "error_message": None,
                }
            ],
        }

    monkeypatch.setattr("app.api.v1.executions.ExecutionService.handoff_tasks_batch", fake_handoff_tasks_batch)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/executions/tasks/handoff/batch",
            json={"task_ids": [str(uuid4()), str(uuid4())], "execution_strategy": "auto"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["completed_count"] == 2
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_user_execution_schedule_crud_endpoint(db_session):
    user = User(
        id=uuid4(),
        username="exec_schedule_user",
        email="exec_schedule_user@example.com",
        hashed_password="hashed",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    from app.models.task import Task, TaskStatus, TaskType

    task = Task(
        user_id=user.id,
        title="定时检查",
        type=TaskType.PLANNING,
        tags=["browser"],
        estimated_minutes=5,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    async def override_get_db():
        yield db_session

    async def override_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_resp = await ac.post(
            "/api/v1/executions/schedules",
            json={
                "task_id": str(task.id),
                "goal": "每天检查一次",
                "trigger_type": "cron",
                "trigger_config": {"cron": "0 8 * * *"},
            },
        )
        list_resp = await ac.get("/api/v1/executions/schedules")

    assert create_resp.status_code == 200
    assert list_resp.status_code == 200
    assert list_resp.json()
    assert list_resp.json()[0]["task_id"] == str(task.id)
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
