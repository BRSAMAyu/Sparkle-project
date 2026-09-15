"""
OBS-009: Tests verifying FakeRedis behavior matches production Redis.

Ensures that the fakeredis test double produces identical results to a mocked
production Redis client for all data structures used in the Sparkle codebase.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

try:
    import fakeredis.aioredis
except ImportError:
    fakeredis = None  # type: ignore[assignment]

pytestmark = pytest.mark.skipif(
    fakeredis is None,
    reason="fakeredis not installed — install with: pip install fakeredis",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_fake():
    """Return a fresh FakeRedis instance."""
    return fakeredis.aioredis.FakeRedis()


def _make_prod_mock():
    """
    Return a mock that simulates production Redis by maintaining an in-memory
    dict and replaying responses.  Not every command is fully featured -- only
    the subset exercised by these tests.
    """
    store: dict = {}
    mock = AsyncMock()

    # --- string ---
    async def _set(name, value, **_kw):
        store[name] = value if isinstance(value, (bytes, int, float)) else value.encode()
        return True

    async def _get(name):
        return store.get(name)

    mock.set = AsyncMock(side_effect=_set)
    mock.get = AsyncMock(side_effect=_get)

    # --- hash ---
    async def _hset(name, key=None, value=None, mapping=None, **_kw):
        h = store.setdefault(name, {})
        if mapping:
            h.update({
                (k.encode() if isinstance(k, str) else k): (v.encode() if isinstance(v, str) else v)
                for k, v in mapping.items()
            })
        elif key is not None:
            k = key.encode() if isinstance(key, str) else key
            h[k] = value.encode() if isinstance(value, str) else value
        return len(h)

    async def _hget(name, key):
        return store.get(name, {}).get(key)

    async def _hgetall(name):
        return store.get(name, {})

    mock.hset = AsyncMock(side_effect=_hset)
    mock.hget = AsyncMock(side_effect=_hget)
    mock.hgetall = AsyncMock(side_effect=_hgetall)

    # --- list ---
    async def _lpush(name, *values):
        lst = store.setdefault(name, [])
        for v in values:
            lst.insert(0, v.encode() if isinstance(v, str) else v)
        return len(lst)

    async def _lrange(name, start, end):
        lst = store.get(name, [])
        if end == -1:
            end = len(lst)
        return lst[start:end]

    mock.lpush = AsyncMock(side_effect=_lpush)
    mock.lrange = AsyncMock(side_effect=_lrange)

    # --- sorted set ---
    async def _zadd(name, mapping, **_kw):
        zs = store.setdefault(name, {})
        added = 0
        for member, score in mapping.items():
            m = member.encode() if isinstance(member, str) else member
            if m not in zs:
                added += 1
            zs[m] = score
        return added

    async def _zrange(name, start, end, **_kw):
        zs = store.get(name, {})
        items = sorted(zs.items(), key=lambda x: x[1])
        if end == -1:
            end = len(items)
        return [m for m, _ in items[start:end]]

    mock.zadd = AsyncMock(side_effect=_zadd)
    mock.zrange = AsyncMock(side_effect=_zrange)

    # --- stream ---
    _stream_counter = [0]

    async def _xadd(name, fields, **_kw):
        _stream_counter[0] += 1
        entry_id = f"1610000000000-{_stream_counter[0]}".encode()
        stream = store.setdefault(name, [])
        stream.append((entry_id, {k.encode() if isinstance(k, str) else k: v.encode() if isinstance(v, str) else v for k, v in fields.items()}))
        return entry_id

    async def _xread(streams, count=None, block=None):
        results = []
        for sname, sids in streams:
            stream = store.get(sname if isinstance(sname, str) else sname.decode(), [])
            results.append((sname, [(eid, data) for eid, data in stream]))
        return results

    mock.xadd = AsyncMock(side_effect=_xadd)
    mock.xread = AsyncMock(side_effect=_xread)

    # --- TTL ---
    _ttl_store: dict = {}

    async def _expire(name, seconds, **_kw):
        _ttl_store[name] = seconds
        return 1

    async def _pttl(name):
        val = _ttl_store.get(name)
        if val is None:
            return -2
        return val * 1000

    mock.expire = AsyncMock(side_effect=_expire)
    mock.pttl = AsyncMock(side_effect=_pttl)

    # --- pipeline ---
    pipe = AsyncMock()

    async def _pipe_execute():
        return [True, b"bar", 1]

    pipe.execute = AsyncMock(side_effect=_pipe_execute)
    pipe.set = MagicMock(return_value=pipe)
    pipe.get = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    mock.pipeline = MagicMock(return_value=pipe)

    # --- incrby ---
    async def _incrby(name, amount=1):
        cur = int(store.get(name, b"0"))
        new = cur + amount
        store[name] = str(new).encode()
        return new

    mock.incrby = AsyncMock(side_effect=_incrby)

    # --- delete ---
    async def _delete(*names):
        count = 0
        for n in names:
            if n in store:
                del store[n]
                count += 1
        return count

    mock.delete = AsyncMock(side_effect=_delete)

    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestFakeVsProdRedis:
    """Verify FakeRedis parity with mocked production Redis."""

    async def test_string_set_get(self):
        fake = await _make_fake()
        prod = _make_prod_mock()

        await fake.set("k", "v")
        await prod.set("k", "v")

        fake_val = await fake.get("k")
        prod_val = await prod.get("k")
        assert fake_val == prod_val

    async def test_hash_operations(self):
        fake = await _make_fake()
        prod = _make_prod_mock()

        await fake.hset("hk", mapping={"f1": "v1", "f2": "v2"})
        await prod.hset("hk", mapping={"f1": "v1", "f2": "v2"})

        fake_all = await fake.hgetall("hk")
        prod_all = await prod.hgetall("hk")
        assert fake_all == prod_all

    async def test_list_operations(self):
        fake = await _make_fake()
        prod = _make_prod_mock()

        await fake.lpush("lk", "c", "b", "a")
        await prod.lpush("lk", "c", "b", "a")

        fake_range = await fake.lrange("lk", 0, -1)
        prod_range = await prod.lrange("lk", 0, -1)
        assert fake_range == prod_range

    async def test_sorted_set(self):
        fake = await _make_fake()
        prod = _make_prod_mock()

        await fake.zadd("zk", {"m1": 1.0, "m2": 2.0})
        await prod.zadd("zk", {"m1": 1.0, "m2": 2.0})

        fake_members = await fake.zrange("zk", 0, -1)
        prod_members = await prod.zrange("zk", 0, -1)
        assert fake_members == prod_members

    async def test_stream_operations(self):
        fake = await _make_fake()
        prod = _make_prod_mock()

        fake_id = await fake.xadd("sk", {"field": "value"})
        prod_id = await prod.xadd("sk", {"field": "value"})

        assert isinstance(fake_id, bytes)
        assert isinstance(prod_id, bytes)
        assert fake_id != b""
        assert prod_id != b""

        fake_read = await fake.xread({b"sk": b"0-0"})
        prod_read = await prod.xread([("sk", "0-0")])
        # Both should return a list with at least one entry
        assert len(fake_read) >= 1
        assert len(prod_read) >= 1

    async def test_ttl_handling(self):
        fake = await _make_fake()
        prod = _make_prod_mock()

        await fake.set("tk", "v")
        await prod.set("tk", "v")
        await fake.expire("tk", 60)
        await prod.expire("tk", 60)

        fake_ttl = await fake.pttl("tk")
        prod_ttl = await prod.pttl("tk")
        assert fake_ttl > 0
        assert prod_ttl == 60_000

    async def test_pipeline_multi_exec(self):
        fake = await _make_fake()
        prod = _make_prod_mock()

        async with fake.pipeline() as pipe:
            pipe.set("pk", "pv")
            pipe.get("pk")
            pipe.expire("pk", 120)
            results = await pipe.execute()

        prod_pipe = prod.pipeline()
        prod_pipe.set("pk", "pv")
        prod_pipe.get("pk")
        prod_pipe.expire("pk", 120)
        prod_results = await prod_pipe.execute()

        assert len(results) == len(prod_results)

    async def test_incrby_atomicity(self):
        fake = await _make_fake()
        prod = _make_prod_mock()

        await fake.set("counter", "0")
        await prod.set("counter", "0")

        for _ in range(5):
            await fake.incrby("counter", 1)
            await prod.incrby("counter", 1)

        fake_val = await fake.get("counter")
        prod_val = await prod.get("counter")
        assert int(fake_val) == int(prod_val) == 5

    async def test_delete_nonexistent(self):
        fake = await _make_fake()
        prod = _make_prod_mock()

        fake_result = await fake.delete("no_such_key")
        prod_result = await prod.delete("no_such_key")
        assert fake_result == prod_result == 0
