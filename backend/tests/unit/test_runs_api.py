"""X-05 · /runs API 契约测试（权威读端点 / 409 / 404 / kill-reopen 语义）.

App kill/reopen 验收的 API 级证据：状态持久在 DB，新客户端实例（= 新 App 进程）
按 run_id 查询得到同一权威状态，不依赖任何内存/WS 状态。
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.api.v1.runs import router
from app.models.user import User
from tests.unit.test_agent_run_service import (  # noqa: F401 — 复用 helpers
    _OUTBOX_DDL,
    _make_intent,
    _make_user,
)


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


app = FastAPI()
app.include_router(router, prefix="/api/v1")


@pytest.fixture(name="db_override")
async def db_override_fixture(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(name="client")
async def client_fixture(db_session, db_override):
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _auth_as(user: User):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_superuser] = lambda: user


def _clear_auth():
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_active_superuser, None)


@pytest.fixture(autouse=True)
def _reset_auth_after_each_test():
    yield
    _clear_auth()


def _forbid_superuser():
    def _raise():
        raise HTTPException(status_code=403, detail="forbidden")

    app.dependency_overrides[get_current_active_superuser] = _raise


async def test_full_api_lifecycle_with_409_on_illegal(db_session, outbox_tables, client):
    user = await _make_user(db_session)
    _auth_as(user)

    # create（幂等键）
    resp = await client.post(
        "/api/v1/runs",
        json={"objective": "整理错题本并生成复习计划", "idempotency_key": "req-1", "steps_total": 4},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    run_id = body["run"]["run_id"]
    assert body["run"]["status"] == "QUEUED"
    assert body["idempotent_replay"] is False

    # 重复 create 同幂等键 → replay（不 201 第二个 run）
    resp2 = await client.post(
        "/api/v1/runs",
        json={"objective": "整理错题本并生成复习计划", "idempotency_key": "req-1"},
    )
    assert resp2.status_code == 201
    assert resp2.json()["run"]["run_id"] == run_id
    assert resp2.json()["idempotent_replay"] is True

    # QUEUED → AWAITING_USER 合法（先 RUNNING）
    assert (await client.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "RUNNING"})).status_code == 200
    assert (await client.post(f"/api/v1/runs/{run_id}/cancel", json={})).status_code == 200
    assert (await client.post(f"/api/v1/runs/{run_id}/cancel", json={})).status_code == 200  # 幂等 no-op

    # 终态后再 resume → 409（非法迁移，非 500；tasks 500→409 先例同族）
    resp3 = await client.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "RUNNING"})
    assert resp3.status_code == 409
    assert "terminal" in resp3.json()["detail"]


async def test_illegal_transition_returns_409_not_500(db_session, outbox_tables, client):
    """图级非法（白名单合法目标 + 非法当前态）→ 409；白名单/未知值 → 422（R2 F4）。"""
    user = await _make_user(db_session)
    _auth_as(user)
    resp = await client.post("/api/v1/runs", json={"objective": "obj"})
    run_id = resp.json()["run"]["run_id"]

    # 白名单拒绝（注入终态/等待态/未知串）→ 422，绝不 500、绝不 200 伪造迁移。
    bad = await client.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "SUCCEEDED"})
    assert bad.status_code == 422
    assert "resume" in bad.json()["detail"]

    unknown = await client.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "banana"})
    assert unknown.status_code == 422  # 原为 plain ValueError → 500

    waiting = await client.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "AWAITING_USER"})
    assert waiting.status_code == 422

    # 白名单合法目标在图级非法的当前态上 → 409（非法迁移，非 500）。
    await client.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "RUNNING"})
    await client.post(f"/api/v1/runs/{run_id}/cancel", json={})
    terminal = await client.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "RUNNING"})
    assert terminal.status_code == 409
    assert "terminal" in terminal.json()["detail"]

    # steps 在 QUEUED 也应可用（QUEUED 是活跃态，允许）。
    resp = await client.post("/api/v1/runs", json={"objective": "obj2"})
    step = await client.post(f"/api/v1/runs/{resp.json()['run']['run_id']}/steps", json={"step_id": "s1", "ordinal": 1})
    assert step.status_code == 200


async def test_resume_whitelist_allows_only_execution_landings(db_session, outbox_tables, client):
    """resume 落点只允许 RUNNING/EXECUTING（AGENT_RUNTIME §2 两个执行落点）。"""
    user = await _make_user(db_session)
    _auth_as(user)
    created = await client.post("/api/v1/runs", json={"objective": "obj"})
    run_id = created.json()["run"]["run_id"]

    ok_running = await client.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "RUNNING"})
    assert ok_running.status_code == 200
    ok_executing = await client.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "EXECUTING"})
    assert ok_executing.status_code == 200
    assert ok_executing.json()["run"]["status"] == "EXECUTING"


async def test_cancel_propagates_to_execution_intent(db_session, outbox_tables, client, monkeypatch):
    """R2 F2：run cancel 必须传播到 ExecutionIntent（协作取消），intent 撤销执行资格。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)  # status=READY（活跃）

    # 外部边界 stub：event_bus.publish 不触真实 Redis（发布可靠性由 bus 自身测试覆盖）。
    published: list[tuple[str, str | None]] = []

    async def _fake_publish(event_type, payload, stream="sparkle_events"):
        published.append((str(event_type), payload.get("new_status")))
        return "test-msg-id"

    monkeypatch.setattr("app.services.execution_service.event_bus.publish", _fake_publish)

    _auth_as(user)
    created = await client.post("/api/v1/runs", json={"objective": "obj", "intent_id": str(intent.id)})
    assert created.status_code == 201, created.text
    run_id = created.json()["run"]["run_id"]

    resp = await client.post(f"/api/v1/runs/{run_id}/cancel", json={})
    assert resp.status_code == 200, resp.text
    assert resp.json()["run"]["status"] == "CANCELLED"

    await db_session.refresh(intent)
    assert intent.status.value == "canceled"  # 执行资格已撤销（协议真源同步取消）
    assert any(et == "execution.status_changed" and new == "canceled" for et, new in published)


async def test_kill_reopen_semantics(db_session, outbox_tables, db_override):
    """App 杀进程重开：全新 HTTP 客户端实例按 run_id 查询，状态不丢。"""
    user = await _make_user(db_session)
    _auth_as(user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as first_session:
        created = await first_session.post("/api/v1/runs", json={"objective": "长任务", "idempotency_key": "kr-1"})
        run_id = created.json()["run"]["run_id"]
        await first_session.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "RUNNING"})
        # 用户在此杀掉 App（会话关闭）。

    # 「重开」：全新客户端、零内存，仅凭 run_id 查询。
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as reopened:
        fetched = await reopened.get(f"/api/v1/runs/{run_id}")
        assert fetched.status_code == 200
        assert fetched.json()["run"]["status"] == "RUNNING"

        # 不记得 run_id 也能按 user+active 找回。
        listed = await reopened.get("/api/v1/runs", params={"active": "true"})
        assert listed.status_code == 200
        assert [item["run_id"] for item in listed.json()["items"]] == [run_id]

        # 审计轨迹可查（append-only）。
        history = await reopened.get(f"/api/v1/runs/{run_id}/transitions")
        events = [t["event_name"] for t in history.json()["items"]]
        assert events == ["run.created", "run.status_changed"]


async def test_cross_user_isolation_404(db_session, outbox_tables, client):
    user_a = await _make_user(db_session)
    user_b = await _make_user(db_session)
    _auth_as(user_a)
    created = await client.post("/api/v1/runs", json={"objective": "secret obj"})
    run_id = created.json()["run"]["run_id"]

    _auth_as(user_b)
    assert (await client.get(f"/api/v1/runs/{run_id}")).status_code == 404
    assert (await client.get(f"/api/v1/runs/{run_id}/transitions")).status_code == 404
    assert (await client.post(f"/api/v1/runs/{run_id}/cancel", json={})).status_code == 404


async def test_unknown_run_404(db_session, outbox_tables, client):
    user = await _make_user(db_session)
    _auth_as(user)
    assert (await client.get(f"/api/v1/runs/{uuid4()}")).status_code == 404


async def test_recovery_endpoint_requires_superuser(db_session, outbox_tables, client):
    user = await _make_user(db_session)
    _auth_as(user)
    _forbid_superuser()
    resp = await client.post("/api/v1/runs/recover", json={})
    assert resp.status_code == 403


async def test_run_events_in_outbox(db_session, outbox_tables, client):
    """API 全程产生的 run 事件在 outbox 留痕（shared-fields 信封齐备）。"""
    user = await _make_user(db_session)
    _auth_as(user)
    created = await client.post("/api/v1/runs", json={"objective": "obj", "idempotency_key": "ev-1"})
    run_id = created.json()["run"]["run_id"]
    await client.post(f"/api/v1/runs/{run_id}/steps", json={"step_id": "s1", "ordinal": 1})

    result = await db_session.execute(
        text("SELECT event_type, payload, metadata FROM event_outbox WHERE aggregate_type = 'agent_run' ORDER BY id")
    )
    rows = [dict(r._mapping) for r in result.all()]
    assert [r["event_type"] for r in rows] == ["run.created", "run.step_completed"]
    metadata = json.loads(rows[0]["metadata"])
    assert metadata["schema_version"] == "event.v1"
    assert metadata["source"] == "server_service"
    assert metadata["correlation"]["run_id"] == run_id
