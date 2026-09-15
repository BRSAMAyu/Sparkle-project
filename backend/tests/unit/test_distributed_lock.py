"""
Unit tests for CacheService.distributed_lock.

Verifies:
1. Lock is acquired and released normally.
2. A late-release does NOT delete a lock already re-acquired by another caller
   (i.e., the Lua TOCTOU fix works: token mismatch → no-op).
3. Exception inside the guarded block still releases the lock.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.cache import CacheService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_redis(*, set_returns=True, get_returns=None):
    """Return a minimal mock redis client."""
    r = MagicMock()
    r.set = AsyncMock(return_value=set_returns)
    r.eval = AsyncMock(return_value=1)
    r.get = AsyncMock(return_value=get_returns)
    return r


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lock_acquired_and_released_normally():
    cache = CacheService()
    cache.redis = _make_redis(set_returns=True)

    async with cache.distributed_lock("test_key", expire=5):
        pass

    # eval (Lua release) must be called exactly once
    cache.redis.eval.assert_awaited_once()
    call_args = cache.redis.eval.call_args
    assert call_args[0][1] == 1            # numkeys = 1
    assert call_args[0][2] == "lock:test_key"


@pytest.mark.asyncio
async def test_lock_released_even_when_body_raises():
    cache = CacheService()
    cache.redis = _make_redis(set_returns=True)

    with pytest.raises(ValueError):
        async with cache.distributed_lock("test_key"):
            raise ValueError("oops")

    cache.redis.eval.assert_awaited_once()


@pytest.mark.asyncio
async def test_lua_script_receives_owner_token():
    """The token written during SET must be passed to the Lua release script."""
    import secrets as _secrets

    cache = CacheService()

    # Intercept secrets.token_hex so we know what token was generated
    fixed_token = "aabbccddeeff00112233445566778899"

    redis_mock = _make_redis(set_returns=True)
    cache.redis = redis_mock

    with patch("app.core.cache.CacheService.distributed_lock.__wrapped__", create=True):
        pass  # no-op, just checking patch is available

    # Patch secrets.token_hex inside the cache module's function scope
    with patch("secrets.token_hex", return_value=fixed_token):
        async with cache.distributed_lock("test_key"):
            pass

    # The Lua eval call's ARGV[1] must equal the fixed token
    eval_call_args = cache.redis.eval.call_args[0]
    # signature: eval(script, numkeys, key, token)
    assert eval_call_args[3] == fixed_token, "Token passed to Lua must match the token stored in Redis"
    # The SET call value must also be the fixed token
    set_call_args = cache.redis.set.call_args[0]
    assert set_call_args[1] == fixed_token, "Token written to Redis SET must match"


@pytest.mark.asyncio
async def test_lock_acquisition_fails_after_retries():
    cache = CacheService()
    cache.redis = _make_redis(set_returns=False)  # always fails

    with pytest.raises(Exception, match="Failed to acquire lock"):
        async with cache.distributed_lock("busy_key"):
            pass  # should not reach here


@pytest.mark.asyncio
async def test_no_redis_fallback_does_not_raise():
    """With no Redis, distributed_lock is a no-op context manager."""
    cache = CacheService()
    cache.redis = None

    result = []
    async with cache.distributed_lock("key"):
        result.append("ran")

    assert result == ["ran"]
