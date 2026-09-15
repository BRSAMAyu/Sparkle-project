"""Regression test for ISSUE-20260503-1700-F1: EventBus.subscribe() must raise
on non-BUSYGROUP ResponseError instead of silently returning.
"""

import asyncio
import pytest
from unittest import mock
from redis.exceptions import ResponseError

from app.core.event_bus import EventBus


class TestEventBusSubscribeRaiseOnNonBusygroup:

    def test_non_busygroup_responseerror_raises(self):
        """Core regression: subscribe() must raise ResponseError when
        xgroup_create fails with non-BUSYGROUP error. Was silently returning,
        which skipped _running=True + asyncio.create_task(_consume_loop)."""
        bus = EventBus()

        async def fake_xgroup_create(stream, group, id="0", mkstream=True):
            raise ResponseError("WRONGTYPE Operation against a key holding the wrong kind of value")

        bus.redis = mock.AsyncMock()
        bus.redis.xgroup_create = fake_xgroup_create

        async def _run():
            with pytest.raises(ResponseError, match="WRONGTYPE"):
                await bus.subscribe(
                    stream="test_stream",
                    group_name="test_group",
                    consumer_name="test_consumer",
                    callback=mock.AsyncMock(),
                )
            assert not bus._running

        asyncio.run(_run())

    def test_busygroup_proceeds_to_consume_loop(self):
        """BUSYGROUP error must not raise; subscribe must proceed to set
        _running=True and create the consume_loop task."""
        bus = EventBus()

        async def fake_xgroup_create(stream, group, id="0", mkstream=True):
            raise ResponseError("BUSYGROUP Consumer Group name already exists")

        bus.redis = mock.AsyncMock()
        bus.redis.xgroup_create = fake_xgroup_create

        async def _run():
            try:
                await bus.subscribe(
                    stream="test_stream",
                    group_name="test_group",
                    consumer_name="test_consumer",
                    callback=mock.AsyncMock(),
                )
            except ResponseError as e:
                if "BUSYGROUP" in str(e):
                    pytest.fail("BUSYGROUP should not propagate out of subscribe")
            except Exception:
                pass
            assert bus._running is True
            assert len(bus._consumer_tasks) == 1

        asyncio.run(_run())

    def test_consumer_pattern_receives_exception(self):
        """Verify that a non-BUSYGROUP error is receivable by the consumer
        retry loop."""
        bus = EventBus()
        call_count = [0]

        async def fake_xgroup_create(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ResponseError("NOGROUP No such key")
            raise ResponseError("BUSYGROUP Consumer Group name already exists")

        bus.redis = mock.AsyncMock()
        bus.redis.xgroup_create = fake_xgroup_create

        retry_count = 0
        got_response_error = False

        async def _run():
            nonlocal retry_count, got_response_error
            max_retries = 3
            while retry_count < max_retries:
                try:
                    await bus.subscribe(
                        stream="test_stream",
                        group_name="test_group",
                        consumer_name="test_consumer",
                        callback=mock.AsyncMock(),
                    )
                    break
                except ResponseError as e:
                    if "NOGROUP" in str(e):
                        retry_count += 1
                        got_response_error = True
                        continue
                    if "BUSYGROUP" in str(e):
                        pytest.fail("BUSYGROUP should not propagate")
                    raise
                except Exception:
                    break

            assert got_response_error, "Consumer should have caught a ResponseError"
            assert retry_count == 1, "Should have retried exactly once"

        asyncio.run(_run())
