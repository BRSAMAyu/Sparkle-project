"""Regression tests for daily-quota Lua scripts (Q1: sliding TTL breaks "daily" semantics)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import redis.asyncio as aioredis

from app.config import settings
from app.core.redis_utils import resolve_redis_password

_LUA_DIR = Path(__file__).resolve().parents[2] / "app" / "services" / "lua"
_KEY_PREFIX = "test:quota:q1"


def _redis_url() -> str:
    raw = os.getenv("REDIS_URL", settings.REDIS_URL or "redis://localhost:6379/1")
    password, _source = resolve_redis_password(raw, os.getenv("REDIS_PASSWORD", settings.REDIS_PASSWORD))
    return raw, password


async def _make_client():
    raw, password = _redis_url()
    client = aioredis.from_url(raw, decode_responses=True, password=password, socket_connect_timeout=2)
    try:
        await client.ping()
    except Exception:
        await client.aclose()
        pytest.skip(f"Redis unavailable for quota lua test: {raw}")
    return client


def _load_script(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_check_and_decr_does_not_slide_daily_ttl():
    """Q1: 重复消费不得滑动续期日配额 TTL（否则 key 永不过期，日配额不重置）。"""
    client = await _make_client()
    key = f"{_KEY_PREFIX}:incr"
    try:
        incr_script = _load_script(_LUA_DIR / "rate_limit.lua")
        sha = await client.script_load(incr_script)
        allowed, current = await client.evalsha(sha, 1, key, 1000, 10, 86400)
        assert int(allowed) == 1
        assert await client.ttl(key) > 0

        # 模拟时间推进：TTL 剩余 1000s，后续消费不得把它续回 86400
        await client.expire(key, 1000)
        for _ in range(3):
            allowed, current = await client.evalsha(sha, 1, key, 1000, 10, 86400)
            assert int(allowed) == 1

        ttl_after = await client.ttl(key)
        assert 0 < ttl_after <= 1000, f"daily quota TTL slid to {ttl_after}, fixed window broken"
    finally:
        await client.delete(key)
        await client.aclose()


@pytest.mark.asyncio
async def test_refund_preserves_ttl_without_sliding():
    """Q1: refund 不得清掉或续长 TTL（SET 会隐式清 TTL，需 KEEPTTL 语义）。"""
    client = await _make_client()
    key = f"{_KEY_PREFIX}:refund"
    try:
        incr_script = _load_script(_LUA_DIR / "rate_limit.lua")
        refund_script = _load_script(_LUA_DIR / "rate_limit_refund.lua")
        incr_sha = await client.script_load(incr_script)
        refund_sha = await client.script_load(refund_script)

        await client.evalsha(incr_sha, 1, key, 1000, 100, 86400)
        await client.expire(key, 500)
        new_val = await client.evalsha(refund_sha, 1, key, 40, 86400)
        assert int(new_val) == 60

        ttl_after = await client.ttl(key)
        assert 0 < ttl_after <= 500, f"refund left TTL at {ttl_after} (cleared or slid)"
    finally:
        await client.delete(key)
        await client.aclose()
