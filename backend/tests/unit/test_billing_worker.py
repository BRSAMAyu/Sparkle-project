"""Regression tests for BillingWorker (B1 timezone drift, B2 at-most-once loss)."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import pytest

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
