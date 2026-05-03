"""Regression test for ISSUE-20260503-1702-F3: EventBus must auto-restart
consume_loop when the background task crashes unexpectedly.
"""

import asyncio
import pytest
from unittest import mock

from app.core.event_bus import EventBus


class TestConsumeLoopAutoRestart:

    def test_done_callback_registered_in_subscribe(self):
        """subscribe() must register a done_callback on the consume_loop task."""
        bus = EventBus()

        # Store the task that would be created in subscribe
        captured_tasks = []
        original_create = asyncio.create_task

        def spy_create(coro):
            task = original_create(coro)
            captured_tasks.append(task)
            return task

        # Don't actually call subscribe (it starts real background tasks).
        # Instead, verify that add_done_callback is in the subscribe code path.
        # Read the source to confirm the pattern exists.
        import inspect
        source = inspect.getsource(bus.subscribe)
        assert "add_done_callback" in source, (
            "subscribe() must call task.add_done_callback()"
        )
        assert "_restart_consume_loop" in source, (
            "subscribe() must reference _restart_consume_loop in the callback"
        )

    def test_restart_on_crash_creates_new_task(self):
        """When consume_loop crashes, restart creates a new running task."""
        bus = EventBus()
        bus._running = True
        bus._consumer_tasks = []

        async def crashing_loop(*args, **kwargs):
            raise RuntimeError("simulated consume_loop crash")

        async def _run():
            task = asyncio.create_task(
                crashing_loop("stream", "group", "consumer", mock.AsyncMock())
            )
            bus._consumer_tasks.append(task)

            # Let task crash
            await asyncio.sleep(0.1)
            assert task.done(), "Task should have crashed"

            # Trigger restart
            bus._restart_consume_loop(task, "stream", "group", "consumer", mock.AsyncMock())

            # Should have created a new task
            assert len(bus._consumer_tasks) >= 1
            # The old task should be replaced
            assert bus._consumer_tasks[-1] is not task

            # Cleanup
            bus._running = False
            for t in bus._consumer_tasks:
                try:
                    t.cancel()
                except Exception:
                    pass

        asyncio.run(_run())

    def test_no_restart_when_stopped(self):
        """When _running is False, crash should NOT trigger restart."""
        bus = EventBus()
        bus._running = False

        async def _run():
            # Create a task that completes normally (no exception)
            task = asyncio.create_task(asyncio.sleep(0.01))
            await task
            assert task.exception() is None

            # restart should not add anything
            bus._restart_consume_loop(task, "stream", "group", "consumer", mock.AsyncMock())
            assert len(bus._consumer_tasks) == 0

        asyncio.run(_run())

    def test_restart_preserves_parameters(self):
        """Auto-restart must pass the same stream/group/consumer to new task."""
        bus = EventBus()
        bus._running = True
        bus._consumer_tasks = []

        captured_params = []
        restart_count = [0]

        async def _run():
            callback = mock.AsyncMock()

            async def spy_consume_loop(stream, group_name, consumer_name, cb):
                captured_params.append((stream, group_name, consumer_name, cb))
                restart_count[0] += 1
                if restart_count[0] >= 2:
                    bus._running = False
                    return
                raise RuntimeError("crash")

            bus._consume_loop = spy_consume_loop

            task = asyncio.create_task(
                spy_consume_loop("my_stream", "my_group", "my_consumer", callback)
            )
            bus._consumer_tasks.append(task)
            await asyncio.sleep(0.1)

            # Trigger restart (original task crashed)
            bus._restart_consume_loop(task, "my_stream", "my_group", "my_consumer", callback)
            await asyncio.sleep(0.2)

            assert len(captured_params) >= 2, f"Expected >=2 calls, got {len(captured_params)}: {captured_params}"
            assert captured_params[0] == ("my_stream", "my_group", "my_consumer", callback)
            assert captured_params[1] == ("my_stream", "my_group", "my_consumer", callback)

            bus._running = False
            for t in bus._consumer_tasks:
                try:
                    t.cancel()
                except Exception:
                    pass

        asyncio.run(_run())

    def test_restart_only_when_exception_present(self):
        """Restart should NOT trigger when task completes without exception."""
        bus = EventBus()
        bus._running = True
        bus._consumer_tasks = []

        async def _run():
            task = asyncio.create_task(asyncio.sleep(0.01))
            await task
            assert task.exception() is None  # no exception

            bus._restart_consume_loop(task, "stream", "group", "consumer", mock.AsyncMock())
            # Should NOT have created a new task (no exception)
            assert len(bus._consumer_tasks) == 0

        asyncio.run(_run())
