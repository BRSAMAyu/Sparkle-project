import pytest

from app.core.cache import CacheService


class _FakeRedis:
    def __init__(self):
        self.set_calls = []
        self.eval_calls = []

    async def set(self, key, value, ex=None, nx=None):
        self.set_calls.append((key, value, ex, nx))
        return True

    async def eval(self, script, numkeys, key, token):
        self.eval_calls.append((script, numkeys, key, token))
        return 1

    async def delete(self, key):
        raise AssertionError("distributed_lock should not call delete directly")


@pytest.mark.asyncio
async def test_distributed_lock_releases_with_owner_token():
    cache = CacheService()
    fake_redis = _FakeRedis()
    cache.redis = fake_redis

    async with cache.distributed_lock("plan-review", expire=30):
        pass

    assert len(fake_redis.set_calls) == 1
    key, token, expire, nx = fake_redis.set_calls[0]
    assert key == "lock:plan-review"
    assert token and token != "1"
    assert expire == 30
    assert nx is True
    assert len(fake_redis.eval_calls) == 1
    _, numkeys, released_key, released_token = fake_redis.eval_calls[0]
    assert numkeys == 1
    assert released_key == key
    assert released_token == token
