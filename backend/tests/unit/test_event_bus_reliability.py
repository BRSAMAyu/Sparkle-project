import json

import pytest

from app.core.event_bus import EventBus


class FakeRedis:
    def __init__(self):
        self.added: list[tuple[str, dict[str, str]]] = []
        self.acked: list[tuple[str, str, str]] = []

    async def xadd(self, stream: str, payload: dict[str, str], maxlen=None, approximate=True):
        # maxlen parameter added for DLQ size limit feature (C3 fix)
        self.added.append((stream, payload))
        return "1-0"

    async def xack(self, stream: str, group_name: str, message_id: str):
        self.acked.append((stream, group_name, message_id))
        return 1


@pytest.mark.asyncio
async def test_event_bus_requeues_failed_message_before_dlq():
    bus = EventBus()
    bus.redis = FakeRedis()
    bus.max_retries = 3

    await bus._handle_failed_message(
        stream="sparkle_events",
        group_name="task_event_consumer",
        consumer_name="task-1",
        message_id="123-0",
        parsed_data={"event_type": "task.completed", "user_id": "u1"},
        error=ValueError("boom"),
    )

    assert bus.redis.acked == [("sparkle_events", "task_event_consumer", "123-0")]
    assert len(bus.redis.added) == 1

    retry_stream, payload = bus.redis.added[0]
    assert retry_stream == "sparkle_events"
    assert payload["event_type"] == "task.completed"
    assert payload["_retry_count"] == "1"
    assert payload["_original_message_id"] == "123-0"


@pytest.mark.asyncio
async def test_event_bus_moves_message_to_dlq_after_max_retries():
    bus = EventBus()
    bus.redis = FakeRedis()
    bus.max_retries = 3

    await bus._handle_failed_message(
        stream="sparkle_events",
        group_name="task_event_consumer",
        consumer_name="task-1",
        message_id="123-0",
        parsed_data={
            "event_type": "task.completed",
            "user_id": "u1",
            "_retry_count": 3,
        },
        error=ValueError("boom"),
    )

    assert bus.redis.acked == [("sparkle_events", "task_event_consumer", "123-0")]
    assert len(bus.redis.added) == 1

    dlq_stream, payload = bus.redis.added[0]
    assert dlq_stream == "sparkle_events:dlq"
    body = json.loads(payload["data"])
    assert body["event"]["event_type"] == "task.completed"
    assert body["retry_count"] == 3
    assert body["message_id"] == "123-0"
