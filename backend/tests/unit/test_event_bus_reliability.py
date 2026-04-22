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
async def test_consumer_failure_moves_to_dlq_without_ack(monkeypatch: pytest.MonkeyPatch) -> None:
    bus = EventBus()
    bus.redis = SimpleNamespace(xack=AsyncMock())
    move_to_dlq = AsyncMock()
    monkeypatch.setattr(bus, "_move_to_dlq", move_to_dlq)
    monkeypatch.setattr(bus, "_get_idempotency_store", AsyncMock(return_value=_FakeIdempotencyStore()))

    async def failing_callback(event: dict) -> None:
        raise RuntimeError("consumer failed")

    await bus._process_stream_message(
        stream="sparkle_events",
        group_name="test_group",
        consumer_name="consumer-a",
        callback=failing_callback,
        message_id="1-0",
        data={"event_type": "task.completed", "user_id": "user-1"},
    )

    bus.redis.xack.assert_not_awaited()
    move_to_dlq.assert_awaited_once()


@pytest.mark.asyncio
async def test_galaxy_handle_event_surfaces_callback_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    consumer = GalaxyEventConsumer(event_bus=SimpleNamespace())

    async def fail(event: dict) -> None:
        raise RuntimeError("bridge failed")

    monkeypatch.setattr(consumer, "_handle_error_created", fail)

    with pytest.raises(RuntimeError, match="bridge failed"):
        await consumer.handle_event({"event_type": "error_created", "user_id": "u-1"})
