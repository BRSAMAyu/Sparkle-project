"""W-3 回归锁：空凭据登录禁止 200（engine 侧契约，不经网关）。

round-1 Web 走查（docs/competition/2026-tmall-hackathon/多端实测/web-round1.md W-3）
曾在引擎双进程旧态下观察到 ``POST /auth/login`` 空 username+空 password 返回 200。
本文件把「凭据校验缺口」钉死为可执行契约（TestClient 直连路由，不依赖网关/DB/Redis）：

- 空 username + 空 password / username+email 均空 → 400（UserLogin 模型校验拒绝，
  生产由 main.py 的 RequestValidationError handler 映射为 400 信封）
- 缺 password 字段 → 400
- 已存在用户 + 空 password → 401（verify_password 对空串恒 False，永不放行）
- 未知用户（含纯空白用户名）→ 401
- 正确凭据对照组 → 200（防修复过度把正常登录也拦掉）

红绿证据（2026-09-18）：临时注释 schemas/user.py 的 ``_validate_identifier`` 后，
test_empty_username_and_password_returns_400 转 422（红）；恢复后全绿——证明当前
栈的 400 语义确实由该校验器 + login 端点空值兜底共同保证，round-1 的 200 系
W-8 双进程旧进程假象而非现存代码缺陷。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import router as auth_router
from app.core.account_lockout import account_lockout_service
from app.core.auth_audit_service import auth_audit_service
from app.core.rate_limiting import limiter
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.user import User

EXISTING_PASSWORD = "w3_right_password_123"


class _FakeResult:
    """模拟 execute(...).scalars().first() 链。"""

    def __init__(self, value: Any) -> None:
        self._value = value

    def scalars(self) -> "_FakeResult":
        return self

    def first(self) -> Any:
        return self._value


class _FakeDb:
    """login 端点只读用户 + refresh，不需要真实会话。"""

    def __init__(self, user: User | None) -> None:
        self.user = user

    async def execute(self, *_args: Any, **_kwargs: Any) -> _FakeResult:
        return _FakeResult(self.user)

    async def refresh(self, _obj: Any) -> None:
        return None


def _build_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="w3_existing_user",
        email="w3_existing@example.com",
        nickname="W3 Existing",
        hashed_password=get_password_hash(EXISTING_PASSWORD),
        is_active=True,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
        photon_balance=0,
        status="offline",
        email_verified=False,
        password_login_enabled=True,
        avatar_status="approved",
        flame_level=1,
        flame_brightness=0.5,
        depth_preference=0.5,
        curiosity_preference=0.5,
    )


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """隔离的 auth 路由 app：关限流、mock 外围副作用、复现 400 校验映射。"""
    from fastapi.testclient import TestClient as _TC  # local import keeps fixture lazy

    user = _build_user()
    db = _FakeDb(user)

    async def _override_get_db():
        yield db

    async def _no_lockout(_user_id: str, _db: AsyncSession) -> bool:
        return False

    async def _noop_async(*_args: Any, **_kwargs: Any) -> None:
        return None

    def _noop_sync(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.setattr(
        account_lockout_service, "check_and_handle_lockout", _no_lockout
    )
    monkeypatch.setattr(account_lockout_service, "record_failed_login", _noop_async)
    monkeypatch.setattr(
        account_lockout_service, "handle_successful_login", _noop_async
    )
    monkeypatch.setattr(auth_audit_service, "schedule_log", _noop_sync)

    from app.core import security_monitor

    monkeypatch.setattr(
        security_monitor.security_monitor, "record_login_attempt", _noop_async
    )

    # 成功路径的 token 签发依赖 DB/Redis 写入；对照测试只关心 200 语义，直接桩掉。
    async def _fake_issue_tokens(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"access_token": "w3-stub-access", "refresh_token": "w3-stub-refresh"}

    from app.api.v1 import auth as auth_module

    monkeypatch.setattr(auth_module, "_issue_auth_tokens", _fake_issue_tokens)

    async def _validation_to_400(_request: Any, _exc: RequestValidationError) -> JSONResponse:
        # 与 main.py 的 validation_exception_handler 同语义（422 → 400）。
        return JSONResponse(status_code=400, content={"success": False})

    app = FastAPI()
    app.include_router(auth_router, prefix="/auth")
    app.state.limiter = limiter
    app.add_exception_handler(RequestValidationError, _validation_to_400)
    app.dependency_overrides[get_db] = _override_get_db

    client = _TC(app)
    return SimpleNamespace(client=client, db=db, user=user)


def test_empty_username_and_password_returns_400(api: SimpleNamespace) -> None:
    resp = api.client.post("/auth/login", json={"username": "", "password": ""})
    assert resp.status_code == 400, resp.text


def test_all_identifiers_null_returns_400(api: SimpleNamespace) -> None:
    resp = api.client.post(
        "/auth/login", json={"username": None, "email": None, "password": "whatever"}
    )
    assert resp.status_code == 400, resp.text


def test_missing_password_returns_400(api: SimpleNamespace) -> None:
    resp = api.client.post("/auth/login", json={"username": "some_user"})
    assert resp.status_code == 400, resp.text


def test_whitespace_username_returns_401(api: SimpleNamespace) -> None:
    api.db.user = None  # 纯空白 identifier 不会命中任何用户
    resp = api.client.post("/auth/login", json={"username": "   ", "password": "   "})
    assert resp.status_code == 401, resp.text


def test_existing_user_with_empty_password_returns_401(api: SimpleNamespace) -> None:
    resp = api.client.post(
        "/auth/login", json={"username": "w3_existing_user", "password": ""}
    )
    assert resp.status_code == 401, resp.text


def test_existing_user_with_wrong_password_returns_401(api: SimpleNamespace) -> None:
    resp = api.client.post(
        "/auth/login", json={"username": "w3_existing_user", "password": "nope-nope"}
    )
    assert resp.status_code == 401, resp.text


def test_valid_credentials_still_return_200(api: SimpleNamespace) -> None:
    resp = api.client.post(
        "/auth/login",
        json={"username": "w3_existing_user", "password": EXISTING_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"] == "w3-stub-access"
    assert body["user"]["username"] == "w3_existing_user"
