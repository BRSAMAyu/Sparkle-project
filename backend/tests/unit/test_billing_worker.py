"""Regression tests for BillingWorker (B1 timezone drift, B2 at-most-once loss, V3-FIX-530 redis outage resilience)."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any

import pytest
import redis.exceptions

from app.services.billing_worker import BillingWorker


def _record(request_id: str = "req-1") -> dict[str, Any]:
    return {
        "user_id": "user-1",
        "session_id": "sess-1",
        "request_id": request_id,
        "model": "test-model",
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "cost": 0.01,
        "timestamp": 1700000000.0,
    }


class _FakeRedis:
    def __init__(self) -> None:
        self.pushed: list[tuple[str, str]] = []

    async def blpop(self, key: str, timeout: int = 1):
        await asyncio.sleep(0)
        return None

    async def lpush(self, key: str, data: str) -> int:
        self.pushed.append((key, data))
        return 1

    async def rpush(self, key: str, data: str) -> int:
        self.pushed.append((key, data))
        return 1

    async def aclose(self) -> None:
        return None


def _make_worker() -> BillingWorker:
    worker = BillingWorker(db_url="sqlite+aiosqlite://")
    worker.redis = _FakeRedis()
    return worker


def test_to_stmt_data_converts_timestamp_as_utc():
    """B1: timestamp 落库必须按 UTC 换算，不得漂移到本地时区。"""
    worker = _make_worker()
    ts = 1700000000.0
    expected = datetime.fromtimestamp(ts, tz=UTC).replace(tzinfo=None)

    data = worker._to_stmt_data(_record())

    assert data["timestamp"] == expected


@pytest.mark.asyncio
async def test_start_survives_flush_failure_and_requeues_batch():
    """B2: 批量 flush 与逐条重试均失败时，worker 不得退出，记录须回退队列。"""
    worker = _make_worker()
    worker._flush_retry_backoff = 0
    worker._batch = [_record("req-1"), _record("req-2")]
    flush_calls = 0

    async def _boom() -> None:
        nonlocal flush_calls
        flush_calls += 1
        raise RuntimeError("db down")

    worker._flush_to_db = _boom  # type: ignore[method-assign]

    task = asyncio.create_task(worker.start())
    await asyncio.sleep(0.05)
    worker.stop()
    await asyncio.wait_for(task, timeout=5)

    assert flush_calls >= 1
    assert worker.is_running is False
    requeued = [json.loads(data) for key, data in worker.redis.pushed if key == "queue:billing"]
    assert sorted(r["request_id"] for r in requeued) == ["req-1", "req-2"]


@pytest.mark.asyncio
async def test_exhausted_attempts_move_to_dead_letter():
    """B2: 重试耗尽的记录转死信队列而非无限回环。"""
    worker = _make_worker()
    worker._flush_retry_backoff = 0
    record = _record("req-dead")
    record[BillingWorker.RETRY_METADATA_KEY] = BillingWorker.MAX_RECORD_ATTEMPTS
    worker._batch = [record]

    await worker._recover_failed_batch(RuntimeError("db still down"))

    dead = [json.loads(data) for key, data in worker.redis.pushed if key == worker._dead_letter_queue]
    assert len(dead) == 1
    assert dead[0]["record"]["request_id"] == "req-dead"
    assert worker._batch == []


class _ConnectionResetFakeRedis(_FakeRedis):
    """V3-FIX-530：模拟 Redis 瞬时断连后恢复的 fake。

    前 `reset_failures` 次 blpop 抛出断连异常（默认复刻 2026-09-28 03:02 实录
    `redis.exceptions.ConnectionError: Error while reading from 127.0.0.1:6379 :
    (54, 'Connection reset by peer')`），此后恢复正常返回 None（队列空轮询）。
    """

    def __init__(self, reset_failures: int, error: Exception | None = None) -> None:
        self._pending_resets = reset_failures
        self._error = error or redis.exceptions.ConnectionError(
            "Error while reading from 127.0.0.1:6379 : (54, 'Connection reset by peer')"
        )
        self.blpop_calls = 0

    async def blpop(self, key: str, timeout: int = 1):
        self.blpop_calls += 1
        await asyncio.sleep(0)
        if self._pending_resets > 0:
            self._pending_resets -= 1
            raise self._error
        return None


@pytest.mark.asyncio
async def test_start_survives_redis_connection_reset_v3_fix_530():
    """V3-FIX-530: Redis 瞬时断连（Connection reset by peer）不得杀死 worker 进程。

    修复前：blpop ConnectionError 经 `except Exception: raise` 上抛 → task 携
    ConnectionError 死亡 → main.py lifespan `await billing_worker_task` 再上抛 →
    "Application shutdown failed. Exiting" 整进程退出（2026-09-28 03:02 实录）。
    修复后：循环内退避重连，断连恢复后继续消费，stop() 正常退出。
    """
    worker = _make_worker()
    worker._reconnect_backoff_seconds = (0.0, 0.0, 0.0)  # 测试加速退避
    fake = _ConnectionResetFakeRedis(reset_failures=3)
    worker.redis = fake

    task: asyncio.Task[None] = asyncio.create_task(worker.start())
    try:
        # 等 fake 吃满 3 次断连且 worker 仍活着继续消费（第 4 次 blpop 到位）
        deadline = time.monotonic() + 2.0
        while fake.blpop_calls < 4 and time.monotonic() < deadline and not task.done():
            await asyncio.sleep(0.01)

        assert not task.done(), "worker task must survive redis connection resets"
        assert worker.is_running is True
        assert fake.blpop_calls >= 4
    finally:
        worker.stop()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5)
        except (TimeoutError, asyncio.CancelledError):
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_reconnect_backoff_sequence_caps_at_max_v3_fix_530():
    """V3-FIX-530: 重连退避序列 1s/5s/30s，末位封顶；空序列退化为 0。"""
    backoff = BillingWorker.REDIS_RECONNECT_BACKOFF_SECONDS
    assert backoff == (1.0, 5.0, 30.0)
    assert BillingWorker._reconnect_delay(backoff, 1) == 1.0
    assert BillingWorker._reconnect_delay(backoff, 2) == 5.0
    assert BillingWorker._reconnect_delay(backoff, 3) == 30.0
    assert BillingWorker._reconnect_delay(backoff, 99) == 30.0
    assert BillingWorker._reconnect_delay((), 1) == 0.0


@pytest.mark.asyncio
async def test_reconnect_backoff_resets_after_successful_poll_v3_fix_530():
    """V3-FIX-530: 断连恢复成功消费后，连续失败计数归零（下次断连重新从 1s 起步）。"""
    worker = _make_worker()
    worker._reconnect_backoff_seconds = (0.0, 0.0, 0.0)
    fake = _ConnectionResetFakeRedis(reset_failures=2)
    worker.redis = fake

    task: asyncio.Task[None] = asyncio.create_task(worker.start())
    try:
        deadline = time.monotonic() + 2.0
        # 第 4 次 blpop = 2 次断连 + 1 次成功轮询 + 1 次成功后的常规轮询
        while fake.blpop_calls < 4 and time.monotonic() < deadline and not task.done():
            await asyncio.sleep(0.01)

        assert not task.done(), "worker task must survive redis connection resets"
        assert worker._reconnect_failures == 0
    finally:
        worker.stop()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5)
        except (TimeoutError, asyncio.CancelledError):
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_unexpected_loop_exception_does_not_kill_worker_v3_fix_530():
    """V3-FIX-530: 循环内非预期异常兜底记录，同样不杀进程。"""
    worker = _make_worker()
    worker._reconnect_backoff_seconds = (0.0, 0.0, 0.0)
    fake = _ConnectionResetFakeRedis(reset_failures=2, error=RuntimeError("unexpected boom"))
    worker.redis = fake

    task: asyncio.Task[None] = asyncio.create_task(worker.start())
    try:
        deadline = time.monotonic() + 2.0
        while fake.blpop_calls < 4 and time.monotonic() < deadline and not task.done():
            await asyncio.sleep(0.01)

        assert not task.done(), "worker task must survive unexpected loop errors"
        assert worker.is_running is True
    finally:
        worker.stop()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5)
        except (TimeoutError, asyncio.CancelledError):
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
