import asyncio

import pytest

from app.core.event_bus import EventBus


@pytest.mark.asyncio
async def test_close_cancels_consumer_tasks():
    bus = EventBus()
    started = asyncio.Event()

    async def sleeper():
        started.set()
        await asyncio.sleep(10)

    task = asyncio.create_task(sleeper())
    await started.wait()
    bus._consumer_tasks.append(task)
    bus._running = True

    await bus.close()

    assert task.cancelled()
    assert bus._consumer_tasks == []
    assert bus._running is False
