from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.api.v1.audit import list_admin_audit_actions
from app.middleware import admin_audit
from app.middleware.admin_audit import ADMIN_AUDIT_METADATA_ATTR, AdminAuditMiddleware, audit_admin_action


class _FakeScalarResult:
    def __init__(self, rows: list[SimpleNamespace]):
        self._rows = rows

    def all(self) -> list[SimpleNamespace]:
        return self._rows


class _FakeExecuteResult:
    def __init__(self, rows: list[SimpleNamespace]):
        self._rows = rows

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._rows)


class _FakeSession:
    def __init__(self, rows: list[SimpleNamespace]):
        self.rows = rows

    async def execute(self, _query):
        return _FakeExecuteResult(self.rows)


@pytest.mark.asyncio
async def test_admin_audit_middleware_records_decorated_admin_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    async def fake_record_admin_audit_log(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(admin_audit, "record_admin_audit_log", fake_record_admin_audit_log)
    user_id = uuid4()

    app = FastAPI()
    app.add_middleware(AdminAuditMiddleware)

    @app.post("/api/v1/admin/policies/publish")
    @audit_admin_action(category="policy_publish", risk="high")
    async def publish_policy(request: Request) -> dict[str, str]:
        request.state.token_payload = {"sub": str(user_id), "type": "access"}
        request.state.request_id = "req-admin-1"
        request.state.trace_id = "trace-admin-1"
        return {"status": "ok"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/admin/policies/publish?secret=hidden",
            headers={"user-agent": "pytest", "x-admin-user-id": str(user_id)},
        )

    assert response.status_code == 200
    assert captured["status_code"] == 200
    assert captured["error"] is None
    request = captured["request"]
    metadata = admin_audit._metadata_for_request(request)
    assert metadata.category == "policy_publish"
    assert metadata.risk == "high"
    assert request.state.token_payload["sub"] == str(user_id)


def test_audit_admin_action_attaches_metadata() -> None:
    @audit_admin_action(category="marketplace_takedown", risk="high", action="deprecate_pack")
    async def endpoint() -> None:
        return None

    metadata = getattr(endpoint, ADMIN_AUDIT_METADATA_ATTR)
    assert metadata.category == "marketplace_takedown"
    assert metadata.risk == "high"
    assert metadata.action == "deprecate_pack"


@pytest.mark.asyncio
async def test_admin_audit_query_api_filters_for_super_admin(
) -> None:
    user_id = uuid4()
    row = SimpleNamespace(
        id=uuid4(),
        admin_user_id=user_id,
        action="replay_dlq_events",
        category="dlq_replay",
        risk="high",
        method="POST",
        path="/api/v1/dlq/replay",
        status_code=200,
        outcome="success",
        duration_ms=12.5,
        ip_address="127.0.0.1",
        request_id="req-1",
        trace_id="trace-1",
        error_message=None,
        details={"decorated": True},
        occurred_at=admin_audit._utcnow(),
        retention_until=admin_audit._utcnow() + timedelta(days=90),
    )

    response = await list_admin_audit_actions(
        admin_user_id=user_id,
        category="dlq_replay",
        risk=None,
        outcome=None,
        path_prefix=None,
        limit=50,
        offset=0,
        db=_FakeSession([row]),
        _admin=SimpleNamespace(is_superuser=True),
    )

    assert response.limit == 50
    assert len(response.items) == 1
    assert response.items[0].action == "replay_dlq_events"
    assert response.items[0].category == "dlq_replay"
