import time

import pytest

from app.core.cache import CacheService


@pytest.mark.asyncio
async def test_local_cache_cleanup_removes_expired_entries():
    cache = CacheService()
    cache.redis = None
    cache._local_cache_cleanup_interval = 1

    cache._local_cache["expired"] = ("old", time.time() - 1)
    cache._local_cache["live"] = ("new", time.time() + 60)

    value = await cache.get("live")

    assert value == "new"
    assert "expired" not in cache._local_cache


@pytest.mark.asyncio
async def test_local_cache_cleanup_enforces_max_entries():
    cache = CacheService()
    cache.redis = None
    cache._local_cache_cleanup_interval = 1
    cache._max_local_cache_entries = 2

    await cache.set("k1", 1, ttl=60)
    await cache.set("k2", 2, ttl=60)
    await cache.set("k3", 3, ttl=60)

    assert len(cache._local_cache) == 2
    assert "k3" in cache._local_cache
