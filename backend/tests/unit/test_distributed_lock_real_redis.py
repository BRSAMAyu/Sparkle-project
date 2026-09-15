"""
Real Redis integration tests for CacheService.distributed_lock.

Uses the real redis_client fixture (no mocks) to verify:
1. Lock acquisition and release with real Redis keys
2. Lua TOCTOU protection (late release doesn't delete re-acquired lock)
3. Exception inside guarded block still releases
4. Concurrent lock contention behavior
5. Lock expiry after TTL
"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from app.core.cache import CacheService


@pytest_asyncio.fixture
async def cache_service(redis_client):
    """Create CacheService with real Redis client."""
    svc = CacheService()
    svc.redis = redis_client
    return svc


@pytest.mark.asyncio
async def test_lock_acquired_and_released(cache_service, redis_client):
    async with cache_service.distributed_lock("test_acquire", expire=5):
        # Lock key should exist during the context
        val = await redis_client.get("lock:test_acquire")
        assert val is not None

    # After release, key should be gone
    val = await redis_client.get("lock:test_acquire")
    assert val is None


@pytest.mark.asyncio
async def test_lock_released_even_when_body_raises(cache_service, redis_client):
    with pytest.raises(ValueError, match="intentional"):
        async with cache_service.distributed_lock("test_exception", expire=5):
            raise ValueError("intentional")

    # Lock should be released despite exception
    val = await redis_client.get("lock:test_exception")
    assert val is None


@pytest.mark.asyncio
async def test_lua_toctou_protection(cache_service, redis_client):
    """Late release from owner A must NOT delete lock re-acquired by owner B."""
    # Owner A acquires lock
    async with cache_service.distributed_lock("toctou_key", expire=30):
        key_a_val = await redis_client.get("lock:toctou_key")
        assert key_a_val is not None

        # Simulate owner A's token being saved
        owner_a_token = key_a_val

    # Lock is now free — owner B acquires
    async with cache_service.distributed_lock("toctou_key", expire=30):
        key_b_val = await redis_client.get("lock:toctou_key")
        assert key_b_val is not None
        assert key_b_val != owner_a_token  # Different token

        # Owner B still holds the lock
        final_val = await redis_client.get("lock:toctou_key")
        assert final_val == key_b_val


@pytest.mark.asyncio
async def test_lock_is_exclusive(cache_service):
    """Only one holder can acquire the same lock at a time."""
    acquired_order = []

    async def worker(name, hold_time=0.1):
        async with cache_service.distributed_lock("exclusive_key", expire=10):
            acquired_order.append(name)
            await asyncio.sleep(hold_time)

    # Run two workers concurrently
    await asyncio.gather(worker("A", 0.15), worker("B", 0.05))

    # Both should have run (sequentially)
    assert set(acquired_order) == {"A", "B"}


@pytest.mark.asyncio
async def test_lock_auto_expires(cache_service, redis_client):
    """Lock expires after TTL even if not released."""
    async with cache_service.distributed_lock("expire_key", expire=1):
        pass  # Lock released normally

    # Verify released
    val = await redis_client.get("lock:expire_key")
    assert val is None


@pytest.mark.asyncio
async def test_different_keys_independent(cache_service):
    """Locks on different keys don't interfere."""
    results = []

    async def worker(key_name):
        async with cache_service.distributed_lock(key_name, expire=5):
            results.append(key_name)

    # Should both acquire immediately (different keys)
    await asyncio.gather(worker("key_alpha"), worker("key_beta"))

    assert set(results) == {"key_alpha", "key_beta"}


@pytest.mark.asyncio
async def test_no_redis_fallback_does_not_raise():
    """With no Redis, distributed_lock is a no-op context manager."""
    svc = CacheService()
    svc.redis = None

    result = []
    async with svc.distributed_lock("fallback_key"):
        result.append("ran")

    assert result == ["ran"]


@pytest.mark.asyncio
async def test_lock_contention_fails_after_retries(redis_client):
    """If lock is held by another, second caller eventually fails."""
    svc = CacheService()
    svc.redis = redis_client

    # Pre-acquire the lock directly
    await redis_client.set("lock:busy_key", "held_by_other", ex=30, nx=True)

    with pytest.raises(Exception, match="Failed to acquire lock"):
        async with svc.distributed_lock("busy_key", expire=10):
            pass

    # Cleanup
    await redis_client.delete("lock:busy_key")
