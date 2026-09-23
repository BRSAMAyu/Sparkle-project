"""AUTH-FOLLOWUP #3：guest access TTL 经 access_ttl claim 轮换透传。

深审报告（v3-output/AUTH-DEEP）A7 P2：guest 签发 access_expires_delta=7 天，
但 refresh 不透传该 delta → 访客首次刷新后 access 缩成默认 30 分钟（-99.4%），
401→refresh 循环压力徒增。

修复：_issue_auth_tokens 签发时把 access 寿命（秒）嵌入 claims["access_ttl"]；
refresh 按 payload 重建 access_expires_delta，无该 claim（旧 token/普通用户）
走默认，向后兼容；上界钳到 refresh 寿命。
"""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1 import auth as auth_module
from app.config import settings
from app.core import security as security_module
from app.core.rate_limiting import setup_rate_limiting

GUEST_ACCESS_TTL_SECONDS = 7 * 24 * 60 * 60


class _FakeDB:
    def __init__(self, user: object) -> None:
        self.user = user

    async def get(self, model, key):  # noqa: ANN001
        return self.user


def _make_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), is_active=True)


@pytest.fixture
def guest_payload():
    return {
        "sub": str(uuid4()),
        "sid": "sess-guest-1",
        "jti": "refresh-jti-guest",
        "exp": 1893456000,
        "type": "refresh",
        "is_guest": True,
        "access_ttl": GUEST_ACCESS_TTL_SECONDS,
    }


def _install_endpoint_mocks(monkeypatch, payload, calls):
    async def fake_decode(token, expected_type=None, **kwargs):  # noqa: ANN001
        return payload

    async def fake_revoke_by_id(db, *, user_id, session_id, ttl_seconds):  # noqa: ANN001
        calls.append("revoke")
        return None

    async def fake_blacklist(jti, exp):  # noqa: ANN001
        calls.append("blacklist")

    async def fake_upsert(db, *, user_id, session_id, refresh_token_jti, request):  # noqa: ANN001
        calls.append("upsert")
        return None

    monkeypatch.setattr(auth_module, "decode_token", fake_decode)
    monkeypatch.setattr(auth_module.auth_session_service, "revoke_session_by_id", fake_revoke_by_id)
    monkeypatch.setattr(auth_module, "blacklist_token", fake_blacklist)
    monkeypatch.setattr(auth_module.auth_session_service, "upsert_session", fake_upsert)


def _build_app(user):
    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(auth_module.router, prefix="/api/v1/auth")

    async def override_db():
        yield _FakeDB(user)

    app.dependency_overrides[auth_module.get_db] = override_db
    return app


async def _decode_token_payload(token: str, monkeypatch) -> dict:
    """真 JWT 解码（黑名单/水位/会话三查 mock 掉——本测试只看 TTL claims）。"""

    async def false_revoked(_jti):
        return False

    async def none_revoked_before(_uid):
        return None

    async def false_session(_sid):
        return False

    monkeypatch.setattr(security_module, "is_token_revoked", false_revoked)
    monkeypatch.setattr(security_module, "get_user_revoked_before", none_revoked_before)
    monkeypatch.setattr(security_module, "is_session_revoked", false_session)
    return await security_module.decode_token(token)


# ---------------------------------------------------------------------------
# helper 单元语义
# ---------------------------------------------------------------------------


def test_access_delta_from_payload_guest_seven_days():
    delta = auth_module._access_delta_from_payload({"access_ttl": GUEST_ACCESS_TTL_SECONDS})
    assert delta == timedelta(days=7)


@pytest.mark.parametrize("raw", [None, 0, -5, "abc", [], {}])
def test_access_delta_from_payload_invalid_falls_back_to_default(raw):
    assert auth_module._access_delta_from_payload({"access_ttl": raw}) is None
    assert auth_module._access_delta_from_payload({}) is None


def test_access_delta_from_payload_clamped_to_refresh_lifetime(monkeypatch):
    monkeypatch.setattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7)
    delta = auth_module._access_delta_from_payload({"access_ttl": 10**9})
    assert delta == timedelta(days=7)


# ---------------------------------------------------------------------------
# 端点行为：refresh 后访客 access 保持 7 天级
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_guest_refresh_preserves_seven_day_access_ttl(monkeypatch, guest_payload):
    user = _make_user()
    calls: list[str] = []
    _install_endpoint_mocks(monkeypatch, guest_payload, calls)

    async with AsyncClient(transport=ASGITransport(app=_build_app(user)), base_url="http://test") as ac:
        resp = await ac.post("/api/v1/auth/refresh", json={"refresh_token": "tok"})

    assert resp.status_code == 200, resp.text
    body = resp.json()

    access_payload = await _decode_token_payload(body["access_token"], monkeypatch)
    ttl = access_payload["exp"] - access_payload["iat"]
    assert access_payload.get("is_guest") is True
    # 7 天级（钳制边界允许 ±秒级误差）
    assert (
        GUEST_ACCESS_TTL_SECONDS - 5 <= ttl <= GUEST_ACCESS_TTL_SECONDS
    ), f"guest access TTL collapsed to {ttl}s (expect ~{GUEST_ACCESS_TTL_SECONDS}s)"
    # 轮换签名的新 refresh token 也带 access_ttl（访客属性跨轮次持久）
    refresh_payload = await _decode_token_payload(body["refresh_token"], monkeypatch)
    assert refresh_payload.get("access_ttl") == GUEST_ACCESS_TTL_SECONDS
    assert refresh_payload.get("type") == "refresh"
    # 轮换顺序不变量未被本改动破坏
    assert calls[0] == "revoke"


@pytest.mark.asyncio
async def test_refresh_without_access_ttl_claim_stays_default(monkeypatch):
    """向后兼容：无 access_ttl claim（存量 token）走默认 ACCESS_TOKEN_EXPIRE_MINUTES。"""
    user = _make_user()
    payload = {
        "sub": str(user.id),
        "sid": "sess-legacy",
        "jti": "refresh-jti-legacy",
        "exp": 1893456000,
        "type": "refresh",
    }
    calls: list[str] = []
    _install_endpoint_mocks(monkeypatch, payload, calls)

    async with AsyncClient(transport=ASGITransport(app=_build_app(user)), base_url="http://test") as ac:
        resp = await ac.post("/api/v1/auth/refresh", json={"refresh_token": "tok"})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    access_payload = await _decode_token_payload(body["access_token"], monkeypatch)
    expected_default = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    ttl = access_payload["exp"] - access_payload["iat"]
    assert expected_default - 5 <= ttl <= expected_default


@pytest.mark.asyncio
async def test_issue_auth_tokens_embeds_access_ttl_claim(monkeypatch):
    """签发面 pin：_issue_auth_tokens 生成的 token 对携带 access_ttl claims。

    guest 端（access_expires_delta=7d）与普通端（默认 30min）均嵌入，
    refresh 才有据可依。
    """
    user = SimpleNamespace(id=uuid4(), is_active=True)

    async def false_revoked(_jti):
        return False

    async def none_revoked_before(_uid):
        return None

    async def false_session(_sid):
        return False

    async def fake_upsert(db, *, user_id, session_id, refresh_token_jti, request):  # noqa: ANN001
        return None

    monkeypatch.setattr(security_module, "is_token_revoked", false_revoked)
    monkeypatch.setattr(security_module, "get_user_revoked_before", none_revoked_before)
    monkeypatch.setattr(security_module, "is_session_revoked", false_session)
    monkeypatch.setattr(auth_module.auth_session_service, "upsert_session", fake_upsert)

    request = SimpleNamespace(
        headers={"user-agent": "pytest"},
        client=SimpleNamespace(host="127.0.0.1"),
        url=SimpleNamespace(path="/api/v1/auth/guest"),
    )
    issued = await auth_module._issue_auth_tokens(
        db=_FakeDB(user),
        user=user,
        request=request,
        access_expires_delta=timedelta(days=7),
        extra_claims={"is_guest": True},
    )
    access_payload = await security_module.decode_token(issued["access_token"], expected_type="access")
    assert access_payload["access_ttl"] == GUEST_ACCESS_TTL_SECONDS
    assert access_payload["is_guest"] is True

    issued_default = await auth_module._issue_auth_tokens(db=_FakeDB(user), user=user, request=request)
    default_payload = await security_module.decode_token(issued_default["access_token"], expected_type="access")
    assert default_payload["access_ttl"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
