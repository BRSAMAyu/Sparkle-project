"""
Phase 2: Event Bus End-to-End Integration Tests

Uses real Redis Streams to verify publish/subscribe, retry, and
message ordering behavior.

Requires: Redis running (docker compose up -d redis)
"""

import json

import pytest
import pytest_asyncio

from app.core.event_bus import EventBus


@pytest.fixture(autouse=True)
def _skip_without_redis(redis_client):
    """Auto-skip if Redis is unavailable (handled by redis_client fixture)."""


@pytest.fixture
async def bus(redis_client):
    """Create an EventBus connected to the real Redis instance."""
    return EventBus(redis_url=redis_client.connection_pool.connection_kwargs.get("url", "redis://localhost:6379/0"))


@pytest.fixture
def unique_stream(redis_client):
    """Generate a unique stream name for test isolation."""
    import uuid
    return f"test_bus:{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
class TestEventBusPublishSubscribe:
    """Verify basic publish/subscribe with real Redis Streams."""

    async def test_publish_returns_message_id(self, bus, unique_stream):
        """Publishing an event should return a Redis stream message ID."""
        msg_id = await bus.publish("test_event", {"key": "value"}, stream=unique_stream)
        assert msg_id is not None
        assert "-" in msg_id

    async def test_published_message_readable_from_stream(self, redis_client, bus, unique_stream):
        """Published messages should be readable from the Redis stream."""
        await bus.publish("test_event", {"hello": "world"}, stream=unique_stream)

        # Read from stream directly
        messages = await redis_client.xrange(unique_stream, count=10)
        assert len(messages) >= 1

        # EventBus flattens payload into top-level stream fields
        _, data = messages[-1]
        assert data.get("hello") == "world"
        assert data.get("event_type") == "test_event"

    async def test_multiple_publishes_ordered(self, bus, redis_client, unique_stream):
        """Messages should be ordered in the stream by publish time."""
        for i in range(5):
            await bus.publish("test_event", {"index": str(i)}, stream=unique_stream)

        messages = await redis_client.xrange(unique_stream, count=10)
        assert len(messages) >= 5

        # Verify ordering — EventBus stores simple values as strings
        indices = []
        for _, data in messages[-5:]:
            indices.append(int(data.get("index", "-1")))
        assert indices == [0, 1, 2, 3, 4]

    async def test_publish_with_event_type_field(self, bus, redis_client, unique_stream):
        """Published messages should include event_type in the stream entry."""
        await bus.publish("user.registered", {"user_id": "u123"}, stream=unique_stream)

        messages = await redis_client.xrange(unique_stream, count=1)
        _, data = messages[0]
        assert data.get("event_type") == "user.registered"
        assert data.get("user_id") == "u123"


@pytest.mark.asyncio
class TestEventBusConsumerGroups:
    """Verify consumer group behavior."""

    async def test_consumer_group_creation(self, bus, redis_client, unique_stream):
        """Publishing should auto-create the stream; consumer groups can be created."""
        await bus.publish("test_event", {"data": "init"}, stream=unique_stream)

        try:
            await redis_client.xgroup_create(unique_stream, "test_group", id="0", mkstream=True)
        except Exception:
            pass

        groups = await redis_client.xinfo_groups(unique_stream)
        group_names = [g["name"] for g in groups]
        assert "test_group" in group_names

    async def test_consumer_reads_unread_messages(self, redis_client, unique_stream):
        """A consumer should be able to read unread messages from the group."""
        for i in range(3):
            await redis_client.xadd(
                unique_stream,
                {"event_type": "test", "payload": json.dumps({"i": i})},
            )

        try:
            await redis_client.xgroup_create(unique_stream, "test_group_2", id="0", mkstream=True)
        except Exception:
            pass

        results = await redis_client.xreadgroup(
            "test_group_2",
            "consumer_1",
            {unique_stream: ">"},
            count=10,
            block=1000,
        )

        assert len(results) > 0
        stream_name, entries = results[0]
        assert stream_name == unique_stream
        assert len(entries) >= 3


@pytest.mark.asyncio
class TestEventBusPayloadIntegrity:
    """Verify payload integrity through publish/consume cycles."""

    async def test_large_payload_survives_round_trip(self, bus, redis_client, unique_stream):
        """Large JSON payloads should survive the Redis round trip."""
        # EventBus serializes dict/list values as JSON strings
        items = [{"id": i, "name": f"item_{i}" * 50} for i in range(100)]
        await bus.publish("bulk_event", {"items": items}, stream=unique_stream)

        messages = await redis_client.xrange(unique_stream, count=1)
        _, data = messages[0]
        # Dict values are JSON-serialized by _serialize_stream_body
        recovered_items = json.loads(data["items"])
        assert len(recovered_items) == 100
        assert recovered_items[50]["id"] == 50

    async def test_unicode_payload_survives(self, bus, redis_client, unique_stream):
        """Unicode content (Chinese, emoji) should survive the round trip."""
        await bus.publish("unicode_event", {
            "message": "你好世界 🌍",
            "description": "测试事件总线的一致性",
        }, stream=unique_stream)

        messages = await redis_client.xrange(unique_stream, count=1)
        _, data = messages[0]
        # Simple string values are stored as-is
        assert data["message"] == "你好世界 🌍"
        assert data["description"] == "测试事件总线的一致性"

    async def test_special_characters_in_payload(self, bus, redis_client, unique_stream):
        """Special characters (quotes, newlines, etc.) should survive."""
        await bus.publish("special_event", {
            "content": 'He said "hello"\nNew line\tTab',
            "path": "/api/v1/users?id=1&type=admin",
        }, stream=unique_stream)

        messages = await redis_client.xrange(unique_stream, count=1)
        _, data = messages[0]
        assert 'He said "hello"' in data["content"]
        assert "\n" in data["content"]
        assert "id=1" in data["path"]
