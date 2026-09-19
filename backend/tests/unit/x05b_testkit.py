"""X-05B · 真实 Redis 总线测试工具（F6 首部署 + e2e 执行投影共用）.

纪律（卡面）：本地 sparkle_redis 只做总线语义测试，**独立 stream key 前缀
``x05b:test:*``，用后删净**——绝不 flushdb（dev Redis 共享）；EventBus 的
幂等去重store 注入内存实现（不在共享 Redis 落 ``idempotency:*`` 键）；
``_persist_dlq_entry`` 实例级中和（失败也不写 dev DB 的 event_bus_dlq）。
"""

from __future__ import annotations

import asyncio
import time
from uuid import uuid4

import pytest
import redis.asyncio as redis

from app.core.event_bus import EventBus
from app.core.idempotency import MemoryIdempotencyStore
from app.core.redis_utils import resolve_redis_password
from tests.conftest import _normalize_test_redis_url

X05B_STREAM_PREFIX = "x05b:test:"


async def make_x05b_redis():
    """独立 redis 客户端（不可用则 skip，与 conftest.redis_client 同判定）。"""
    import os

    from app.config import settings

    url = _normalize_test_redis_url(
        os.getenv("REDIS_URL", settings.REDIS_URL or "redis://localhost:6379/0")
    )
    # 与 conftest.redis_client fixture 完全同形的密码解析（URL 内嵌优先，
    # 其次 REDIS_PASSWORD env / settings——本地 sparkle_redis 带 requirepass，
    # 漏 env 层会让带密码部署永远 skip）。
    password, _ = resolve_redis_password(url, os.getenv("REDIS_PASSWORD", settings.REDIS_PASSWORD))
    client = redis.from_url(url, encoding="utf-8", decode_responses=True, password=password)
    try:
        await client.ping()
    except Exception as exc:
        if hasattr(client, "aclose"):
            await client.aclose()
        else:
            await client.close()
        pytest.skip(f"Redis unavailable for x05b bus tests: {exc}")
    return client


def make_x05b_bus(redis_client) -> EventBus:
    """真实 EventBus：直连给定客户端；幂等内存化；DLQ DB 落档中和。"""
    bus = EventBus()
    bus.redis = redis_client
    bus._idempotency = MemoryIdempotencyStore()

    async def _noop_persist_dlq(**kwargs):
        return None

    bus._persist_dlq_entry = _noop_persist_dlq
    return bus


async def cleanup_x05b_keys(redis_client) -> None:
    """只删 ``x05b:test:*`` 前缀键（流/组/DLQ 随键删除），绝不动其他键。"""
    cursor = 0
    doomed: list[str] = []
    while True:
        cursor, keys = await redis_client.scan(cursor, match=f"{X05B_STREAM_PREFIX}*", count=200)
        doomed.extend(keys)
        if cursor == 0:
            break
    for key in doomed:
        await redis_client.delete(key)


class StreamScopedBus:
    """把模块级全局 event_bus 引用重定向到隔离流（publish 缺省流改写）。

    生产者（execution_service._publish_status_event /
    execution_run_producer.publish_execution_step_event）都以模块全局
    ``event_bus`` 引用发布且不带 stream 参数；e2e 用本包装替换全局引用，
    其余真实路径全部保留。
    """

    def __init__(self, bus: EventBus, stream: str):
        self._bus = bus
        self._stream = stream

    async def publish(self, event_type: str, payload: dict, stream: str | None = None):
        return await self._bus.publish(event_type, payload, stream=self._stream)

    async def connect(self):
        await self._bus.connect()

    async def subscribe(self, *args, **kwargs):
        return await self._bus.subscribe(*args, **kwargs)


def x05b_stream(label: str) -> str:
    return f"{X05B_STREAM_PREFIX}{label}:{uuid4().hex[:10]}"


def x05b_group(label: str) -> str:
    return f"{X05B_STREAM_PREFIX}{label}:grp-{uuid4().hex[:10]}"


async def wait_until(cond, timeout: float = 15.0, interval: float = 0.15) -> bool:
    """轮询等待异步条件成立（消费循环投递延迟用）。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if await cond() if asyncio.iscoroutinefunction(cond) else cond():
            return True
        await asyncio.sleep(interval)
    return False
