"""X-05B · FIX-29 runs API 硬化测试（N1 intent 归属 + N3 cancel reason 白名单）.

- N1：POST /runs 挂他人 intent → 404（不泄露存在性、不抢占投影、不窥时间线）；
     不存在 intent → 404；本人 intent → 201 照常；
- N3：cancel reason 服务端白名单 ``{user_cancelled}``（terminal_reason_vocabulary
     的用户语义子集）——词表内他词（如 queue_stale）与任意串一律 422。
"""

from __future__ import annotations

from sqlalchemy import text

from app.api.deps import get_current_user, get_db
from app.api.v1.runs import router
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tests.unit.test_agent_run_service import (  # noqa: F401 — 复用 helpers
    _OUTBOX_DDL,
    _make_intent,
    _make_user,
)

app = FastAPI()
app.include_router(router, prefix="/api/v1")


async def _setup(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()


async def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_n1_foreign_intent_404_no_hijack(db_session):
    """挂他人 intent → 404，且不落任何 run 行（不抢占该 intent 的投影）。"""
    await _setup(db_session)
    owner = await _make_user(db_session)
    attacker = await _make_user(db_session)
    intent = await _make_intent(db_session, owner)

    app.dependency_overrides[get_current_user] = lambda: attacker
    async with await _client() as client:
        resp = await client.post(
            "/api/v1/runs",
            json={"objective": "hijack", "intent_id": str(intent.id)},
        )
    assert resp.status_code == 404, resp.text

    result = await db_session.execute(text("SELECT COUNT(*) FROM agent_runs"))
    assert int(result.scalar_one()) == 0  # 无 run 行 → 他人投影轨道未被抢占


async def test_n1_unknown_intent_404(db_session):
    import uuid

    await _setup(db_session)
    user = await _make_user(db_session)
    app.dependency_overrides[get_current_user] = lambda: user
    async with await _client() as client:
        resp = await client.post(
            "/api/v1/runs",
            json={"objective": "obj", "intent_id": str(uuid.uuid4())},
        )
    assert resp.status_code == 404


async def test_n1_own_intent_still_creates(db_session):
    """正路径：本人 intent → 201，run.intent_id 正确挂接。"""
    await _setup(db_session)
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)

    app.dependency_overrides[get_current_user] = lambda: user
    async with await _client() as client:
        resp = await client.post(
            "/api/v1/runs",
            json={"objective": "my run", "intent_id": str(intent.id)},
        )
    assert resp.status_code == 201, resp.text
    assert resp.json()["run"]["intent_id"] == str(intent.id)


async def test_n3_cancel_reason_whitelist(db_session):
    """N3：默认/白名单 reason → 200；词表内他词与任意串 → 422。"""
    await _setup(db_session)
    user = await _make_user(db_session)
    app.dependency_overrides[get_current_user] = lambda: user

    async with await _client() as client:
        created = await client.post("/api/v1/runs", json={"objective": "obj"})
        run_id = created.json()["run"]["run_id"]

        ok = await client.post(f"/api/v1/runs/{run_id}/cancel", json={"reason": "user_cancelled"})
        assert ok.status_code == 200
        assert ok.json()["run"]["terminal_reason"] == "user_cancelled"

        # 幂等重放（已终态）不再走 reason 校验路径——先建第二个 run。
        second = await client.post("/api/v1/runs", json={"objective": "obj2"})
        second_id = second.json()["run"]["run_id"]
        vocab_but_not_client = await client.post(
            f"/api/v1/runs/{second_id}/cancel", json={"reason": "queue_stale"}
        )
        assert vocab_but_not_client.status_code == 422, vocab_but_not_client.text
        assert "client-selectable" in vocab_but_not_client.json()["detail"]

        third = await client.post("/api/v1/runs", json={"objective": "obj3"})
        arbitrary = await client.post(
            f"/api/v1/runs/{third.json()['run']['run_id']}/cancel", json={"reason": "banana"}
        )
        assert arbitrary.status_code == 422

        # 被拒后 run 保持活跃（未半取消）。
        still = await client.get(f"/api/v1/runs/{second_id}")
        assert still.json()["run"]["status"] == "QUEUED"
        assert still.json()["run"]["is_terminal"] is False
