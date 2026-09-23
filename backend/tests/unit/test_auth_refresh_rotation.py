"""COMMUNITY-401 regression: /auth/refresh rotation must not poison the token.

Field evidence (V13-RETEST residual Major-2): the refresh handler called
``auth_session_service.revoke_session(str(session_id))`` — a TypeError
(missing db/session/ttl_seconds) raised AFTER ``blacklist_token`` had already
run. Every client refresh therefore returned 401 while the presented refresh
JTI stayed blacklisted, so the mobile client's retry hit "Token revoked" and
force-logged-out — the app-wide auth death that surfaced as the community
tab's permanent 401s after an app restart.

Pins three properties:
1. the broken ``revoke_session(...)`` call never comes back (the by-id
   variant with explicit user/session/ttl is the only wired path);
2. the refresh JTI is blacklisted only AFTER session revocation succeeded
   (a revocation failure must not consume the presented token);
3. a happy-path refresh returns 200 with fresh tokens.
"""

from __future__ import annotations

import inspect
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1 import auth as auth_module
from app.core.rate_limiting import setup_rate_limiting


def _source() -> str:
    return inspect.getsource(auth_module.refresh_token)


def test_refresh_never_calls_bare_revoke_session():
    """The broken 1-arg revoke_session(str) call must stay dead."""
    code_lines = [
        line
        for line in _source().splitlines()
        if not line.strip().startswith("#")
    ]
    src = "\n".join(code_lines)
    assert "revoke_session(str(session_id))" not in src
    assert "revoke_session_by_id(" in src


def test_refresh_blacklists_only_after_session_revocation():
    """Order pin: revoke_session_by_id appears before blacklist_token."""
    src = _source()
    revoke_at = src.index("revoke_session_by_id(")
    blacklist_at = src.index("blacklist_token(")
    assert revoke_at < blacklist_at


class _FakeDB:
    def __init__(self, user: object) -> None:
        self.user = user

    async def get(self, model, key):  # noqa: ANN001
        return self.user


@pytest.mark.asyncio
async def test_refresh_happy_path_rotates_and_returns_200(monkeypatch):
    user = SimpleNamespace(
        id=uuid4(),
        is_active=True,
        agreed_to_tos_at=datetime(2026, 1, 1),
    )
    calls: list[str] = []

    async def fake_decode(token, expected_type=None, **kwargs):  # noqa: ANN001
        return {
            "sub": str(user.id),
            "sid": "sess-1",
            "jti": "refresh-jti-1",
            "exp": 1893456000,
            "type": "refresh",
        }

    async def fake_revoke_by_id(db, *, user_id, session_id, ttl_seconds):  # noqa: ANN001
        calls.append(f"revoke:{user_id}:{session_id}:{ttl_seconds}")
        return None

    async def fake_blacklist(jti, exp):  # noqa: ANN001
        calls.append(f"blacklist:{jti}")

    async def fake_upsert(db, *, user_id, session_id, refresh_token_jti, request):  # noqa: ANN001
        calls.append("upsert")
        return None

    monkeypatch.setattr(auth_module, "decode_token", fake_decode)
    monkeypatch.setattr(
        auth_module.auth_session_service, "revoke_session_by_id", fake_revoke_by_id
    )
    monkeypatch.setattr(auth_module, "blacklist_token", fake_blacklist)
    monkeypatch.setattr(
        auth_module.auth_session_service, "upsert_session", fake_upsert
    )

    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(auth_module.router, prefix="/api/v1/auth")

    async def override_db():
        yield _FakeDB(user)

    app.dependency_overrides[auth_module.get_db] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/auth/refresh", json={"refresh_token": "tok"}
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]

    # session revocation happened with the by-id variant and full args
    assert any(c.startswith("revoke:") for c in calls), calls
    assert not any(c.startswith("revoke:") and c.count(":") != 3 for c in calls)
    # the presented refresh JTI is blacklisted AFTER revocation, and only once
    assert calls.index("blacklist:refresh-jti-1") > calls.index(
        [c for c in calls if c.startswith("revoke:")][0]
    )


@pytest.mark.asyncio
async def test_refresh_survives_revocation_failure_without_poisoning_token(
    monkeypatch,
):
    """If session revocation fails, the token must NOT be blacklisted."""
    user = SimpleNamespace(id=uuid4(), is_active=True)
    blacklisted: list[str] = []

    async def fake_decode(token, expected_type=None, **kwargs):  # noqa: ANN001
        return {"sub": str(user.id), "sid": "sess-1", "jti": "j-2", "exp": 1}

    async def failing_revoke(db, **kwargs):  # noqa: ANN001
        raise RuntimeError("db down")

    async def fake_blacklist(jti, exp):  # noqa: ANN001
        blacklisted.append(jti)

    async def fake_upsert(db, **kwargs):  # noqa: ANN001
        return None

    monkeypatch.setattr(auth_module, "decode_token", fake_decode)
    monkeypatch.setattr(
        auth_module.auth_session_service, "revoke_session_by_id", failing_revoke
    )
    monkeypatch.setattr(auth_module, "blacklist_token", fake_blacklist)
    monkeypatch.setattr(
        auth_module.auth_session_service, "upsert_session", fake_upsert
    )

    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(auth_module.router, prefix="/api/v1/auth")

    async def override_db():
        yield _FakeDB(user)

    app.dependency_overrides[auth_module.get_db] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/auth/refresh", json={"refresh_token": "tok"}
        )

    assert resp.status_code == 401
    # the presented token stays usable for a retry — nothing was blacklisted
    assert blacklisted == []


def test_issue_auth_tokens_skips_session_revocation_self_check():
    """The issuer must not run the session-revocation check on its own token.

    2026-09-23 live probe: rotation revokes the session (Redis mark set) and
    then re-issues under the SAME sid; the issuer's internal decode_token
    hit that stale mark and raised "Session revoked" on every refresh —
    unit tests missed it because they mocked the cache layer.
    """
    src = inspect.getsource(auth_module._issue_auth_tokens)
    assert "check_session_revocation=False" in src


@pytest.mark.asyncio
async def test_decode_token_session_check_semantics(monkeypatch):
    """Default decode rejects a revoked sid; the skip flag bypasses only that."""
    from app.core import security as security_module

    user_id = str(uuid4())

    async def fake_is_session_revoked(sid: str) -> bool:
        return sid == "sess-stale"

    async def fake_is_token_revoked(jti: str) -> bool:
        return False

    async def fake_revoked_before(uid: str):
        return None

    monkeypatch.setattr(security_module, "is_session_revoked", fake_is_session_revoked)
    monkeypatch.setattr(security_module, "is_token_revoked", fake_is_token_revoked)
    monkeypatch.setattr(security_module, "get_user_revoked_before", fake_revoked_before)

    claims = {"sub": user_id, "sid": "sess-stale", "type": "refresh"}
    token = security_module.create_refresh_token(data=claims)

    with pytest.raises(Exception, match="Session revoked"):
        await security_module.decode_token(token, expected_type="refresh")

    payload = await security_module.decode_token(
        token, expected_type="refresh", check_session_revocation=False
    )
    assert payload["sid"] == "sess-stale"
