"""V3-FIX-286 · guest 种子观测面盲区 —— 种子内部失败必须真实可见 红绿锁.

卡面（wt567 并发猎缺轴 1 相邻面，P3）：FIX-55 的 seed_status/GUEST_SEED_TOTAL
挂在 `seed_guest_user_data` 调用外，而该函数自 FIX-13（09-19）起把
`_seed_guest_user_data` 全程包在 try+begin_nested 内吞异常仅告警——种子内部
失败恒报 seeded/reseeded + success 计数，auth.py 三个 except 分支只剩
commit/refresh 失败可触发，「失败可见」目标被击穿。

可证伪判据（台账原文）：stub `app.services.guest_seed_service._seed_guest_user_data`
恒 raise RuntimeError，调 POST /api/v1/auth/guest（新 guest）——修前响应
seed_status=="seeded" 且 GUEST_SEED_TOTAL{outcome="success"}+1（期望 failed/failure）。

修复口径（观测面，非致命控制流零变化）：
- ``seed_guest_user_data`` SAVEPOINT 隔离回滚后上抛 :class:`GuestSeedError`
 （FIX-13 隔离语义不变，吞光改为可见）。
- guest_login 仍 200（种子失败不阻断主流程）；seed_status 如实报
  ``failed`` + ``seed_failure_reason`` 回传 + GUEST_SEED_TOTAL{failure}+1。
- 新客路径保留「失败重试一次」语义（SAVEPOINT 隔离下同事务重试）。

红测（base 上红）：
1. 新客种子内部失败 → 仍 200 但 seed_status=="failed" + failure 计数
  （修前恒 "seeded" + success 计数：红）。
2. 老客补种内部失败 → seed_status=="failed" + failure 计数
  （修前恒 "reseeded" + success 计数：红）。
3. 新客首败重试成功 → seed_status=="seeded" 且种子恰被调 2 次
  （修前吞光后无重试直达成功，calls==1：红）。
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


def _stub_inner_seed(monkeypatch: pytest.MonkeyPatch, behavior) -> list[int]:
    """stub 种子内层 ``_seed_guest_user_data``（台账判据锚点）。

    behavior: ``"raise"`` 恒抛 | ``"ok"`` 恒过 | callable(calls)->bool 抛否。
    """
    calls: list[int] = []

    async def _inner(session, user):  # noqa: ANN001
        calls.append(1)
        should_raise = behavior(calls) if callable(behavior) else behavior == "raise"
        if should_raise:
            raise RuntimeError("simulated seed outage (V3-FIX-286)")

    monkeypatch.setattr(gss_module, "_seed_guest_user_data", _inner)
    return calls


async def _post_guest(client: AsyncClient, guest_id: str | None = None) -> object:
    # guest_login 的 guest_id 是 query 参数（auth.py: `guest_id: str | None = None`
    # 无 Body 注解），body 传入不生效——FIX-55 测试即踩此口径（恒随机新客）。
    if guest_id is None:
        guest_id = f"guest_{uuid4().hex[:8]}"
    return await client.post("/api/v1/auth/guest", params={"guest_id": guest_id})


# --- 红测 1：新客种子内部失败 → failed + failure 计数（非致命 200 保持） ----------


@pytest.mark.asyncio
async def test_new_guest_seed_internal_failure_is_visible(guest_app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_inner_seed(monkeypatch, "raise")

    from app.core.metrics import GUEST_SEED_TOTAL

    success_before = GUEST_SEED_TOTAL.labels(outcome="success")._value.get()
    failure_before = GUEST_SEED_TOTAL.labels(outcome="failure")._value.get()

    async with AsyncClient(
        transport=ASGITransport(app=guest_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await _post_guest(client)

    assert resp.status_code == 200, f"种子失败必须保持非致命（200），实际 {resp.status_code}: {resp.text[:200]}"
    body = resp.json()
    assert body.get("seed_status") == "failed", (
        f"种子内部失败必须如实报 failed（修前被吞恒报 seeded：红），实际: {body.get('seed_status')!r}"
    )
    reason = body.get("seed_failure_reason")
    assert isinstance(reason, str) and reason, f"失败必须带 seed_failure_reason 原因，实际: {reason!r}"
    success_after = GUEST_SEED_TOTAL.labels(outcome="success")._value.get()
    failure_after = GUEST_SEED_TOTAL.labels(outcome="failure")._value.get()
    assert success_after == success_before, (
        f"种子内部失败不得计 success（修前恒 +1：红）before={success_before} after={success_after}"
    )
    assert failure_after >= failure_before + 1, (
        f"种子内部失败必须计 failure（GUEST_SEED_TOTAL）before={failure_before} after={failure_after}"
    )


# --- 红测 2：老客补种内部失败 → failed（修前恒 reseeded） ------------------------


@pytest.mark.asyncio
async def test_existing_guest_reseed_internal_failure_is_visible(
    guest_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    guest_id = f"guest_{uuid4().hex[:8]}"
    failure_before = 0
    from app.core.metrics import GUEST_SEED_TOTAL

    failure_before = GUEST_SEED_TOTAL.labels(outcome="failure")._value.get()

    async with AsyncClient(
        transport=ASGITransport(app=guest_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        # 首登：种子内部无碍，建号成功
        _stub_inner_seed(monkeypatch, "ok")
        first = await _post_guest(client, guest_id)
        assert first.status_code == 200 and first.json().get("seed_status") == "seeded"

        # 重登：种子内部失败（台账判据：stub _seed_guest_user_data 恒 raise）
        _stub_inner_seed(monkeypatch, "raise")
        second = await _post_guest(client, guest_id)

    assert second.status_code == 200, f"补种失败必须保持非致命（200），实际 {second.status_code}: {second.text[:200]}"
    body = second.json()
    assert body.get("seed_status") == "failed", (
        f"老客补种内部失败必须如实报 failed（修前被吞恒报 reseeded：红），实际: {body.get('seed_status')!r}"
    )
    assert isinstance(body.get("seed_failure_reason"), str) and body["seed_failure_reason"]
    after = GUEST_SEED_TOTAL.labels(outcome="failure")._value.get()
    assert after >= failure_before + 1, f"补种失败必须计 failure，before={failure_before} after={after}"


# --- 红测 3：新客首败重试成功 → seeded 且种子恰被调 2 次（重试语义真实可达） -------


@pytest.mark.asyncio
async def test_new_guest_seed_retry_after_transient_failure_recovers(
    guest_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _stub_inner_seed(monkeypatch, lambda seq: len(seq) == 1)

    from app.core.metrics import GUEST_SEED_TOTAL

    success_before = GUEST_SEED_TOTAL.labels(outcome="success")._value.get()

    async with AsyncClient(
        transport=ASGITransport(app=guest_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await _post_guest(client)

    assert resp.status_code == 200, f"瞬时失败经重试应 200，实际 {resp.status_code}: {resp.text[:200]}"
    body = resp.json()
    assert body.get("seed_status") == "seeded", (
        f"重试成功应报 seeded，实际: {body.get('seed_status')!r}（修前吞光首轮后无重试直达：calls 口径红）"
    )
    assert len(calls) == 2, f"首败后应重试一次（种子恰被调 2 次），实际 calls={calls}"
    assert "seed_failure_reason" not in body, "最终成功不得携带失败原因键"
    success_after = GUEST_SEED_TOTAL.labels(outcome="success")._value.get()
    assert success_after == success_before + 1, f"重试成功应计 success，before={success_before} after={success_after}"
