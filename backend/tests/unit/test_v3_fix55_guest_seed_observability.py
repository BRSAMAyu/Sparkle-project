"""V3-FIX-55 · guest 种子静默失败 —— 失败计数指标 + seed_status 字段 红绿锁.

卡面（清扫轮4 P3）：guest 演示数据播种失败时只落 warning/error 日志，
对调用方完全静默——登录 200 照常返回，但没有任何字段告诉客户端
「演示数据没种上」，也没有指标让失败可计数、可告警（auth.py guest_login
的 seed try/except 链）。

修复口径（观测面，不改重试/非致命语义）：
- ``sparkle_guest_seed_total{outcome}`` 计数器：success / failure。
- 登录响应新增 ``seed_status`` 字段：``seeded``（新客播种成功）/
  ``reseeded``（老客幂等补种成功）/ ``failed``（两轮皆败，账号可用）。
- 失败路径保持非致命：HTTP 仍 200，用户可继续使用。

红测（base 上红）：
1. 新客播种成功 → 200 + ``seed_status == "seeded"``（base 无该字段：红）。
2. 新客两轮播种皆败 → 仍 200 + ``seed_status == "failed"`` + 失败计数
  （base 无该字段且无指标：红）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1 import auth as auth_module
from app.core.rate_limiting import setup_rate_limiting
from app.db.session import get_db
from app.services import guest_seed_service as gss_module


@pytest.fixture(name="guest_app")
async def guest_app_fixture(db_session, monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(auth_module.router, prefix="/api/v1/auth")

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db

    # 签发面 mock：观测面测试不触 token/session/audit 真实链
    async def _fake_issue(**kwargs):  # noqa: ANN003
        return {"access_token": "test-access", "refresh_token": "test-refresh"}

    monkeypatch.setattr(auth_module, "_issue_auth_tokens", _fake_issue)

    yield app
    app.dependency_overrides.clear()


def _script_seed(monkeypatch: pytest.MonkeyPatch, fail: bool) -> list[int]:
    calls: list[int] = []

    async def _seed(session, user):  # noqa: ANN001
        calls.append(1)
        if fail:
            raise RuntimeError("simulated seed outage")

    monkeypatch.setattr(gss_module, "seed_guest_user_data", _seed)
    return calls


async def _post_guest(client: AsyncClient) -> object:
    return await client.post("/api/v1/auth/guest", json={"guest_id": f"guest_{uuid4().hex[:8]}"})


# --- 红测 1：新客播种成功 → seed_status == "seeded" -------------------------------


@pytest.mark.asyncio
async def test_guest_login_reports_seed_status_seeded(guest_app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    _script_seed(monkeypatch, fail=False)

    async with AsyncClient(
        transport=ASGITransport(app=guest_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await _post_guest(client)

    assert resp.status_code == 200, f"guest 登录应 200，实际 {resp.status_code}: {resp.text[:200]}"
    body = resp.json()
    assert (
        body.get("seed_status") == "seeded"
    ), f"新客播种成功必须回 seed_status=seeded（base 无该字段：红），实际: {body.get('seed_status')!r}"


# --- 红测 2：两轮播种皆败 → seed_status == "failed" + 失败计数 --------------------


@pytest.mark.asyncio
async def test_guest_login_reports_seed_failure_with_metric(
    guest_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _script_seed(monkeypatch, fail=True)

    from app.core.metrics import GUEST_SEED_TOTAL

    before = GUEST_SEED_TOTAL.labels(outcome="failure")._value.get()

    async with AsyncClient(
        transport=ASGITransport(app=guest_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await _post_guest(client)

    assert resp.status_code == 200, f"种子失败必须保持非致命（200），实际 {resp.status_code}: {resp.text[:200]}"
    body = resp.json()
    assert (
        body.get("seed_status") == "failed"
    ), f"两轮播种皆败必须回 seed_status=failed（base 无该字段：红），实际: {body.get('seed_status')!r}"
    after = GUEST_SEED_TOTAL.labels(outcome="failure")._value.get()
    assert after >= before + 1, f"失败必须被计数（sparkle_guest_seed_total failure），before={before} after={after}"
    assert len(calls) == 2, f"新客失败路径应有首轮+重试共 2 次播种调用，实际 {len(calls)}"
