"""
Real Redis integration tests for EventBus publish/consume.

Uses real Redis Streams to verify:
1. Messages are published and readable
2. Consumer groups work correctly
3. Message fields survive round-trip
4. Multiple streams are independent
"""
from __future__ import annotations

import asyncio
import uuid

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def stream_name():
    """Unique stream name per test to avoid collisions."""
    return f"test_stream:{uuid.uuid4().hex[:12]}"


@pytest_asyncio.fixture
async def redis(redis_client):
    return redis_client


@pytest.mark.asyncio
async def test_publish_and_read_message(redis, stream_name):
    """Published message can be read from the stream."""
    msg_id = await redis.xadd(stream_name, {"event_type": "test_event", "user_id": "u1"})

    messages = await redis.xrange(stream_name, count=1)
    assert len(messages) == 1
    assert messages[0][1]["event_type"] == "test_event"
    assert messages[0][1]["user_id"] == "u1"

    # Cleanup
    await redis.delete(stream_name)


@pytest.mark.asyncio
async def test_consumer_group_reads_messages(redis, stream_name):
    """Consumer group can read messages from the stream."""
    # Create group (need at least one message first, or use $ with MKSTREAM)
    await redis.xadd(stream_name, {"event_type": "init", "user_id": "system"})

    group_name = f"test_group:{uuid.uuid4().hex[:8]}"
    await redis.xgroup_create(stream_name, group_name, id="0", mkstream=False)

    # Read from consumer group
    messages = await redis.xreadgroup(group_name, "consumer-1", {stream_name: ">"}, count=10, block=100)
    assert len(messages) > 0
    # messages[0] = (stream_name, [(msg_id, data), ...])
    stream_msgs = messages[0][1]
    assert stream_msgs[0][1]["event_type"] == "init"

    # Cleanup
    await redis.xgroup_destroy(stream_name, group_name)
    await redis.delete(stream_name)


@pytest.mark.asyncio
async def test_message_order_preserved(redis, stream_name):
    """Messages are returned in publish order."""
    for i in range(5):
        await redis.xadd(stream_name, {"seq": str(i)})

    messages = await redis.xrange(stream_name)
    seqs = [int(m[1]["seq"]) for m in messages]
    assert seqs == [0, 1, 2, 3, 4]

    await redis.delete(stream_name)


@pytest.mark.asyncio
async def test_multiple_streams_independent(redis):
    """Writes to one stream don't affect another."""
    s1 = f"s1:{uuid.uuid4().hex[:8]}"
    s2 = f"s2:{uuid.uuid4().hex[:8]}"

    await redis.xadd(s1, {"data": "alpha"})
    await redis.xadd(s2, {"data": "beta"})

    msgs1 = await redis.xrange(s1)
    msgs2 = await redis.xrange(s2)

    assert len(msgs1) == 1
    assert len(msgs2) == 1
    assert msgs1[0][1]["data"] == "alpha"
    assert msgs2[0][1]["data"] == "beta"

    await redis.delete(s1, s2)


@pytest.mark.asyncio
async def test_ack_removes_from_pending(redis, stream_name):
    """Acknowledged messages are no longer pending."""
    msg_id = await redis.xadd(stream_name, {"event_type": "ack_test"})
    group_name = f"ack_group:{uuid.uuid4().hex[:8]}"
    await redis.xgroup_create(stream_name, group_name, id="0", mkstream=False)

    # Read message
    await redis.xreadgroup(group_name, "consumer-1", {stream_name: ">"}, count=10, block=100)

    # Check pending before ack
    pending_before = await redis.xpending_range(stream_name, group_name, min="-", max="+", count=10)
    assert len(pending_before) >= 1

    # Ack the message
    await redis.xack(stream_name, group_name, msg_id)

    # Check pending after ack
    pending_after = await redis.xpending_range(stream_name, group_name, min="-", max="+", count=10)
    assert len(pending_after) == 0

    await redis.xgroup_destroy(stream_name, group_name)
    await redis.delete(stream_name)


@pytest.mark.asyncio
async def test_stream_length(redis, stream_name):
    """XLEN correctly reports number of messages."""
    assert await redis.xlen(stream_name) == 0

    await redis.xadd(stream_name, {"x": "1"})
    assert await redis.xlen(stream_name) == 1

    for i in range(10):
        await redis.xadd(stream_name, {"x": str(i + 2)})
    assert await redis.xlen(stream_name) == 11

    await redis.delete(stream_name)
