"""AUTH-FOLLOWUP #1：token_revocation_service 退役后的等价性回归。

深审报告（v3-output/AUTH-DEEP）A2-2：旧 token_revocation_service 把拉黑写进
错置的黑名单命名空间（decode_token 与 Go 网关只读 token_blacklist 前缀，
拉黑对 gRPC/SSE/STT/网关不可见），且 logout 曾把 exp 绝对值当时长传入
（TTL ≈ 55 年）。67042121 已把 logout 切到 security.blacklist_token；
本卡删除整个服务并把 deps.py 两处读点切到 security.is_token_revoked。

钉三件事：
1. 退役模块不再可导入（防复活）；
2. deps.py 不再引用退役服务的读口（AST 级 import pin）；
3. 拉黑可见性等价：security.blacklist_token 写入的 jti 对 deps 鉴权路径可见
   （401），TTL 语义为「剩余寿命」而非绝对 exp。
"""

from __future__ import annotations

import ast
import importlib
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from jose import jwt as jose_jwt

from app.api import deps as deps_module
from app.config import settings
from app.core import security as security_module
from app.core.cache import cache_service
from app.core.security import (
    TOKEN_BLACKLIST_PREFIX,
    blacklist_token,
    create_access_token,
    is_token_revoked,
)


def _access_token_with_jti(sub: str, sid: str, jti: str) -> str:
    """手工签发带指定 jti 的 access token（create_access_token 会覆写 jti）。"""
    now = datetime.now(UTC)
    return jose_jwt.encode(
        {
            "sub": sub,
            "sid": sid,
            "jti": jti,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )


class _StubRedis:
    """cache_service JSON 线格式兼容的最小异步 redis 替身。"""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int | None] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = value
        self.ttls[key] = ex
        return True

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if self.store.pop(key, None) is not None:
                removed += 1
        return removed


@pytest.fixture
def stub_redis(monkeypatch):
    stub = _StubRedis()
    monkeypatch.setattr(cache_service, "redis", stub)
    return stub


def test_token_revocation_module_is_retired():
    """退役模块必须不可导入（防止双命名空间复活）。"""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("app.core.token_revocation")


def test_deps_no_longer_import_retired_service():
    """AST pin：deps.py 不得再从 app.core.token_revocation 导入任何名字。"""
    source = Path(deps_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "app.core.token_revocation", "deps.py 重新引入了已退役的 token_revocation 服务"
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "app.core.token_revocation"
    # 旧读口方法名不得出现
    assert "is_token_blacklisted" not in source


@pytest.mark.asyncio
async def test_blacklisted_jti_is_visible_to_deps_auth_path(stub_redis, monkeypatch):
    """logout 拉黑的 jti 必须对 deps 鉴权路径可见（401）——命名空间等价。"""
    jti = f"jti-{uuid4().hex}"
    exp = int(time.time()) + 1800
    token = create_access_token(data={"sub": "user-1", "sid": "sess-1"})
    await blacklist_token(jti, exp)

    # 同一 jti 写入的是 token_blacklist: 命名空间，is_token_revoked 立即可见
    assert await is_token_revoked(jti) is True
    assert TOKEN_BLACKLIST_PREFIX + jti in stub_redis.store

    # deps 路径：被拉黑的 jti 出现在 token 里必须 401
    tampered = _access_token_with_jti("user-1", "sess-1", jti)

    async def fake_revoked_before(user_id):
        return None

    async def fake_session_revoked(session_id):
        return False

    monkeypatch.setattr(security_module, "get_user_revoked_before", fake_revoked_before)
    monkeypatch.setattr(security_module, "is_session_revoked", fake_session_revoked)

    request = SimpleNamespace(state=SimpleNamespace())
    credentials = SimpleNamespace(credentials=tampered)
    with pytest.raises(HTTPException) as exc_info:
        await deps_module.get_current_user_id(request, credentials)
    assert exc_info.value.status_code == 401

    # 未拉黑的等价 token 正常放行，返回 sub
    request = SimpleNamespace(state=SimpleNamespace())
    credentials = SimpleNamespace(credentials=token)
    user_id = await deps_module.get_current_user_id(request, credentials)
    assert user_id == "user-1"


@pytest.mark.asyncio
async def test_blacklist_ttl_is_remaining_lifetime_not_absolute_exp(stub_redis):
    """TTL 语义 pin：写入的是 exp−now（秒），且过期 token 不写 key。

    旧实现的 bug：第二参当「时长」，logout 传绝对 exp → TTL ≈ 55 年。
    """
    jti = f"jti-{uuid4().hex}"
    now = int(time.time())
    await blacklist_token(jti, now + 3600)
    stored_ttl = stub_redis.ttls[TOKEN_BLACKLIST_PREFIX + jti]
    assert 3590 <= stored_ttl <= 3600, f"expected remaining-lifetime TTL, got {stored_ttl}"

    # 已过期的 token：ttl<=0 跳过写入
    stale_jti = f"jti-{uuid4().hex}"
    await blacklist_token(stale_jti, now - 10)
    assert TOKEN_BLACKLIST_PREFIX + stale_jti not in stub_redis.store
