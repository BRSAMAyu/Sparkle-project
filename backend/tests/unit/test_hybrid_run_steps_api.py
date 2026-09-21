"""X-07 · /runs hybrid step 端点 API 契约测试（幂等 resume / 恢复推导 / 409/422）.

App kill/reopen 语义（test_runs_api 同构）：步骤计划/awaiting 戳/完成戳全部
持久在 ``agent_runs.steps``，新客户端实例按 run_id 查询得到同一 ``awaiting_
step`` 推导（含 ownership/prompt/artifacts），不依赖任何内存/WS 状态。

「用户操作两次不会 resume 两次」在 API 面的证据：complete 双发（同 key 与
换 key）第二次得 200 + ``step_replay=true``，且服务端 ``run.user_resumed``
事件恰一条。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.api.v1.runs import router
from app.models.user import User
from tests.unit.test_agent_run_service import (  # noqa: F401 — 复用 helpers
    _OUTBOX_DDL,
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


_PLAN = {
    "steps": [
        {
            "step_id": "s1",
            "ordinal": 1,
            "label": "整理资料",
            "owner": "agent",
            "completion_condition": {"kind": "agent_output"},
        },
        {
            "step_id": "s2",
            "ordinal": 2,
            "label": "确认清单",
            "owner": "human",
            "completion_condition": {"kind": "user_confirmation"},
        },
    ]
}


async def _make_hybrid_run_to_awaiting(client, *, expires_in: timedelta | None = None) -> str:
    resp = await client.post("/api/v1/runs", json={"objective": "错题变复习卡", **_PLAN})
    assert resp.status_code == 201, resp.text
    run_id = resp.json()["run"]["run_id"]

    resp = await client.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "RUNNING"})
    assert resp.status_code == 200, resp.text

    resp = await client.post(f"/api/v1/runs/{run_id}/steps/s1/agent-complete", json={})
    assert resp.status_code == 200, resp.text
    assert resp.json()["run"]["status"] == "RUNNING"  # agent 步进不改状态

    body: dict = {"prompt": "请确认清单"}
    if expires_in is not None:
        body["wait_expires_at"] = (datetime.now(UTC).replace(tzinfo=None) + expires_in).isoformat()
    resp = await client.post(f"/api/v1/runs/{run_id}/steps/s2/await", json=body)
    assert resp.status_code == 200, resp.text
    return run_id


async def test_define_plan_and_full_handoff_lifecycle(db_session, outbox_tables, client):
    user = await _make_user(db_session)
    _auth_as(user)

    resp = await client.post("/api/v1/runs", json={"objective": "错题变复习卡"})
    run_id = resp.json()["run"]["run_id"]

    # PUT 计划（幂等重投）
    resp = await client.put(f"/api/v1/runs/{run_id}/steps", json=_PLAN)
    assert resp.status_code == 200, resp.text
    assert [s["step_id"] for s in resp.json()["run"]["steps"]] == ["s1", "s2"]
    resp = await client.put(f"/api/v1/runs/{run_id}/steps", json=_PLAN)
    assert resp.status_code == 200
    assert resp.json()["transition_applied"] is False  # 幂等 no-op

    # 越表 owner → 422
    bad = {
        "steps": [{"step_id": "x", "ordinal": 1, "owner": "robot", "completion_condition": {"kind": "agent_output"}}]
    }
    resp = await client.put(f"/api/v1/runs/{run_id}/steps", json=bad)
    assert resp.status_code == 422


async def test_complete_double_fire_resumes_once_step_replay(db_session, outbox_tables, client):
    user = await _make_user(db_session)
    _auth_as(user)
    run_id = await _make_hybrid_run_to_awaiting(client)

    first = await client.post(
        f"/api/v1/runs/{run_id}/steps/s2/complete",
        json={"idempotency_key": "u07:s2:confirm", "action": "confirm"},
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["run"]["status"] == "RUNNING"
    assert body["transition_applied"] is True
    assert body["step_replay"] is False

    # 同 key 双击
    second = await client.post(
        f"/api/v1/runs/{run_id}/steps/s2/complete",
        json={"idempotency_key": "u07:s2:confirm"},
    )
    assert second.status_code == 200
    assert second.json()["step_replay"] is True
    assert second.json()["run"]["status"] == "RUNNING"

    # 换 key 重发（另一台设备重试）
    third = await client.post(
        f"/api/v1/runs/{run_id}/steps/s2/complete",
        json={"idempotency_key": "u07:s2:confirm-device-2"},
    )
    assert third.status_code == 200
    assert third.json()["step_replay"] is True

    # 服务端 run.user_resumed 事件恰一条
    transitions = await client.get(f"/api/v1/runs/{run_id}/transitions")
    resume_rows = [t for t in transitions.json()["items"] if t["event_name"] == "run.user_resumed"]
    assert len(resume_rows) == 1

    # 缺幂等键 → 422
    resp = await client.post(f"/api/v1/runs/{run_id}/steps/s2/complete", json={"action": "confirm"})
    assert resp.status_code == 422


async def test_owner_discipline_at_api(db_session, outbox_tables, client):
    user = await _make_user(db_session)
    _auth_as(user)

    resp = await client.post("/api/v1/runs", json={"objective": "错题变复习卡", **_PLAN})
    run_id = resp.json()["run"]["run_id"]
    await client.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "RUNNING"})

    # 用户不能替 Agent 完成 agent-owned 步骤（owner 纪律双向闭环）
    resp = await client.post(
        f"/api/v1/runs/{run_id}/steps/s1/complete",
        json={"idempotency_key": "user-tries-agent-step"},
    )
    assert resp.status_code == 409
    assert "agent-owned" in resp.json()["detail"]


async def test_cold_reopen_derives_awaiting_step(db_session, outbox_tables, client):
    """冷启动恢复面：新 client 实例（= 新 App 进程）仅凭 run_id 还原 awaiting step。"""
    user = await _make_user(db_session)
    _auth_as(user)
    run_id = await _make_hybrid_run_to_awaiting(client, expires_in=timedelta(minutes=30))

    fresh_client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    resp = await fresh_client.get(f"/api/v1/runs/{run_id}")
    await fresh_client.aclose()
    assert resp.status_code == 200
    run = resp.json()["run"]
    assert run["status"] == "AWAITING_USER"
    awaiting = run["awaiting_step"]
    assert awaiting["step_id"] == "s2"
    assert awaiting["state"] == "awaiting"
    assert awaiting["ownership"] == "human"  # U-04 P2：HUMAN 可达
    assert awaiting["prompt"] == "请确认清单"
    assert awaiting["expires_at"] is not None


async def test_cancel_and_expire_explicit_at_api(db_session, outbox_tables, client):
    user = await _make_user(db_session)
    _auth_as(user)

    # 取消后迟到确认 → 409 + 终态归因可见；awaiting_step 投影 state=cancelled
    run_id = await _make_hybrid_run_to_awaiting(client)
    resp = await client.post(f"/api/v1/runs/{run_id}/cancel", json={"reason": "user_cancelled"})
    assert resp.status_code == 200
    late = await client.post(
        f"/api/v1/runs/{run_id}/steps/s2/complete",
        json={"idempotency_key": "late-confirm"},
    )
    assert late.status_code == 409
    assert late.json()["detail"]["run"]["terminal_reason"] == "user_cancelled"
    assert late.json()["detail"]["run"]["awaiting_step"]["state"] == "cancelled"

    # 过期 sweep 后迟到确认 → 409 + state=expired
    run_id2 = await _make_hybrid_run_to_awaiting(client, expires_in=timedelta(minutes=-1))
    resp = await client.post("/api/v1/runs/recover", json={"stale_after_seconds": 60})
    assert resp.status_code == 200
    detail = await client.get(f"/api/v1/runs/{run_id2}")
    assert detail.json()["run"]["status"] == "TIMED_OUT"
    assert detail.json()["run"]["awaiting_step"]["state"] == "expired"
    late2 = await client.post(
        f"/api/v1/runs/{run_id2}/steps/s2/complete",
        json={"idempotency_key": "late-confirm-2"},
    )
    assert late2.status_code == 409
    assert late2.json()["detail"]["run"]["awaiting_step"]["state"] == "expired"
