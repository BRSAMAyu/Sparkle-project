"""AUTH-FOLLOWUP #2：cache_service 安全前缀禁用进程内兜底（fail-closed）。

深审报告（v3-output/AUTH-DEEP）A-2 专项发现 P1：init_redis 失败时
cache_service.redis=None，黑名单/水位/吊销标记的读写全部落进程内 dict——
多 worker 互不可见（实例 A 拉黑的 token 在实例 B 有效），且本地路径不抛
异常使 prod fail-closed 永不触发（静默 fail-open）。

修复语义（cache.py SECURITY_KEY_PREFIXES）：
- redis=None 且非测试环境：三个安全前缀的读抛 CacheUnavailableError
  （交由调用方既有 fail-closed 语义裁决），写直接抛错；
- 业务缓存前缀保持本地兜底不变；
- 测试环境（ENVIRONMENT ∈ {test, testing}，conftest 置 "test"）豁免。
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.core.cache import (
    SECURITY_KEY_PREFIXES,
    CacheUnavailableError,
    cache_service,
)
from app.core.security import (
    TOKEN_BLACKLIST_PREFIX,
    USER_REVOKED_BEFORE_PREFIX,
    is_token_revoked,
)
from app.services.auth_session_service import SESSION_REVOKED_PREFIX


@pytest.fixture(autouse=True)
def _no_redis_and_clean_local(monkeypatch):
    """强制 redis=None（init 失败形态）并隔离全局单例的本地 dict。"""
    monkeypatch.setattr(cache_service, "redis", None)
    monkeypatch.setattr(cache_service, "_local_cache", {})
    yield


@pytest.fixture(autouse=True)
def _development_env(monkeypatch):
    """默认挂在 development（守卫激活、调用方 fail-open）下；各用例可覆写。"""
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")


def test_security_prefix_constants_match_owners():
    """漂移 pin：cache.py 的安全前缀与三个定义点字面一致。"""
    for prefix in (TOKEN_BLACKLIST_PREFIX, USER_REVOKED_BEFORE_PREFIX, SESSION_REVOKED_PREFIX):
        assert prefix in SECURITY_KEY_PREFIXES, f"missing security prefix: {prefix}"


@pytest.mark.asyncio
async def test_security_key_read_raises_when_redis_absent():
    for prefix in (TOKEN_BLACKLIST_PREFIX, SESSION_REVOKED_PREFIX, USER_REVOKED_BEFORE_PREFIX):
        with pytest.raises(CacheUnavailableError):
            await cache_service.get(f"{prefix}whatever")


@pytest.mark.asyncio
async def test_security_key_write_raises_when_redis_absent():
    for prefix in (TOKEN_BLACKLIST_PREFIX, SESSION_REVOKED_PREFIX, USER_REVOKED_BEFORE_PREFIX):
        with pytest.raises(CacheUnavailableError):
            await cache_service.set(f"{prefix}whatever", "1", ttl=60)
    # 本地 dict 必须保持干净——假吊销绝不落进程内
    assert cache_service._local_cache == {}


@pytest.mark.asyncio
async def test_business_prefix_keeps_local_fallback():
    """业务缓存前缀行为不变：本地兜底可写可读。"""
    await cache_service.set("sparkle:view:some_view:abc", {"v": 1}, ttl=60)
    assert await cache_service.get("sparkle:view:some_view:abc") == {"v": 1}
    assert await cache_service.get("sparkle:view:missing:xyz") is None


@pytest.mark.asyncio
async def test_testing_env_is_exempt_from_guard(monkeypatch):
    """单测环境豁免：ENVIRONMENT=test 时安全键仍走本地兜底（既有用例不红）。"""
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    await cache_service.set(f"{SESSION_REVOKED_PREFIX}s-1", "1", ttl=60)
    assert await cache_service.get(f"{SESSION_REVOKED_PREFIX}s-1") == "1"
    monkeypatch.setattr(settings, "ENVIRONMENT", "testing")
    await cache_service.set(f"{TOKEN_BLACKLIST_PREFIX}j-1", "revoked", ttl=60)
    assert await cache_service.get(f"{TOKEN_BLACKLIST_PREFIX}j-1") == "revoked"


@pytest.mark.asyncio
async def test_is_token_revoked_fail_closed_in_prod_when_redis_absent(monkeypatch):
    """核心目标：Redis 缺席时 prod 的 fail-closed 必须真正触发（原先永不触发）。"""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert await is_token_revoked("some-jti") is True

    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    # 非 prod 保持既有 fail-open 语义（异常被 is_token_revoked 捕获后返回 False）
    assert await is_token_revoked("some-jti") is False


def test_cache_unavailable_error_is_retryable_infra_error():
    """继承 ConnectionError：refresh 端点的基础设施分级（→503）天然接住，
    不会伪装成 401 触发移动端清 token 强登出。"""
    assert issubclass(CacheUnavailableError, ConnectionError)
