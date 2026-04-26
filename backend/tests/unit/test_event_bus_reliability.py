from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.event_bus import EventBus
from app.services.galaxy_event_consumer import GalaxyEventConsumer


class _FakeIdempotencyStore:
    def __init__(self) -> None:
        self.locked = False

    async def get(self, key: str):
        return None

    async def lock(self, key: str) -> bool:
        self.locked = True
        return True

    async def set(self, key: str, value, ttl: int) -> None:
        self.locked = False

    async def unlock(self, key: str) -> None:
        self.locked = False


@pytest.mark.asyncio
async def test_publish_retries_until_success() -> None:
    bus = EventBus()
    bus.redis = SimpleNamespace(xadd=AsyncMock(side_effect=[RuntimeError("boom-1"), RuntimeError("boom-2"), "123-0"]))

    message_id = await bus.publish("task.completed", {"user_id": "u-1"})

    assert message_id == "123-0"
    assert bus.redis.xadd.await_count == 3


@pytest.mark.asyncio
async def test_consumer_failure_requeues_then_later_success_acks(monkeypatch: pytest.MonkeyPatch) -> None:
    bus = EventBus()
    bus.consumer_retry_base_delay_ms = 0
    bus.redis = SimpleNamespace(xack=AsyncMock(), xadd=AsyncMock(return_value="2-0"))
    move_to_dlq = AsyncMock()
    monkeypatch.setattr(bus, "_move_to_dlq", move_to_dlq)
    monkeypatch.setattr(bus, "_get_idempotency_store", AsyncMock(return_value=_FakeIdempotencyStore()))

    attempts = 0

    async def failing_callback(event: dict) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("consumer failed")

    await bus._process_stream_message(
        stream="sparkle_events",
        group_name="test_group",
        consumer_name="consumer-a",
        callback=failing_callback,
        message_id="1-0",
        data={"event_type": "task.completed", "user_id": "user-1"},
    )

    bus.redis.xadd.assert_awaited_once()
    bus.redis.xack.assert_awaited_once_with("sparkle_events", "test_group", "1-0")
    move_to_dlq.assert_not_awaited()

    await bus._process_stream_message(
        stream="sparkle_events",
        group_name="test_group",
        consumer_name="consumer-a",
        callback=failing_callback,
        message_id="2-0",
        data={"event_type": "task.completed", "user_id": "user-1", "_retry_count": "1"},
    )

    assert attempts == 2
    assert bus.redis.xack.await_count == 2
    move_to_dlq.assert_not_awaited()


@pytest.mark.asyncio
async def test_consumer_failure_moves_to_dlq_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    bus = EventBus()
    bus.consumer_retry_base_delay_ms = 0
    bus.redis = SimpleNamespace(xack=AsyncMock(), xadd=AsyncMock())
    move_to_dlq = AsyncMock()
    monkeypatch.setattr(bus, "_move_to_dlq", move_to_dlq)
    monkeypatch.setattr(bus, "_get_idempotency_store", AsyncMock(return_value=_FakeIdempotencyStore()))

    async def failing_callback(event: dict) -> None:
        raise RuntimeError("consumer failed")

    for retry_count in range(bus.max_retries):
        await bus._process_stream_message(
            stream="sparkle_events",
            group_name="test_group",
            consumer_name="consumer-a",
            callback=failing_callback,
            message_id=f"{retry_count + 1}-0",
            data={
                "event_type": "task.completed",
                "user_id": "user-1",
                "_retry_count": str(retry_count),
            },
        )

    assert bus.redis.xadd.await_count == bus.max_retries
    assert bus.redis.xack.await_count == bus.max_retries
    move_to_dlq.assert_not_awaited()

    await bus._process_stream_message(
        stream="sparkle_events",
        group_name="test_group",
        consumer_name="consumer-a",
        callback=failing_callback,
        message_id=f"{bus.max_retries + 1}-0",
        data={
            "event_type": "task.completed",
            "user_id": "user-1",
            "_retry_count": str(bus.max_retries),
        },
    )

    assert bus.redis.xadd.await_count == bus.max_retries
    move_to_dlq.assert_awaited_once()


@pytest.mark.asyncio
async def test_galaxy_handle_event_surfaces_callback_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    consumer = GalaxyEventConsumer(event_bus=SimpleNamespace())

    async def fail(event: dict) -> None:
        raise RuntimeError("bridge failed")

    monkeypatch.setattr(consumer, "_handle_error_created", fail)

    with pytest.raises(RuntimeError, match="bridge failed"):
        await consumer.handle_event({"event_type": "error_created", "user_id": "u-1"})
