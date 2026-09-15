from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.orchestration.circuit_breaker import circuit_breaker_registry
from app.orchestration.orchestrator import ChatOrchestrator


class FakeTask:
    def __init__(self):
        self.callbacks = []
        self.cancelled = False

    def add_done_callback(self, callback):
        self.callbacks.append(callback)

    def cancel(self):
        self.cancelled = True

    def __await__(self):
        async def _noop():
            return None

        return _noop().__await__()


@pytest.fixture
def orchestrator():
    circuit_breaker_registry._breakers.pop("langgraph_planner", None)
    fake_task = FakeTask()

    def fake_create_task(coro):
        coro.close()
        return fake_task

    with (
        patch("app.orchestration.orchestrator.create_standard_chat_graph", return_value=MagicMock()),
        patch("app.orchestration.orchestrator.asyncio.create_task", side_effect=fake_create_task),
    ):
        instance = ChatOrchestrator(db_session=MagicMock(), redis_client=MagicMock())
    return instance, fake_task


def test_orchestrator_registers_and_injects_langgraph_breaker(orchestrator):
    instance, _ = orchestrator

    assert instance.lang_graph_planner.circuit_breaker is instance.langgraph_breaker
    assert circuit_breaker_registry.get("langgraph_planner") is instance.langgraph_breaker


def test_orchestrator_tracks_background_initialization_task(orchestrator):
    instance, fake_task = orchestrator

    assert fake_task in instance._bg_tasks
    assert len(fake_task.callbacks) == 1


@pytest.mark.asyncio
async def test_shutdown_cancels_tracked_background_tasks(orchestrator):
    instance, fake_task = orchestrator
    second_task = FakeTask()
    instance._track_task(second_task)

    await instance.shutdown()

    assert fake_task.cancelled is True
    assert second_task.cancelled is True
    assert instance._bg_tasks == set()
