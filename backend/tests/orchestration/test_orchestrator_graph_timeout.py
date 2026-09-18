"""RB-02 regression tests: the graph 300s timeout path must terminate the stream.

Before the fix, when `_execute_graph` timed out, `process_stream` neither yielded a
STOP nor an ERROR terminal frame, silently dropped every already-generated delta,
recorded `status="success"`, and left the FSM stuck short of DONE/FAILED.
"""

from __future__ import annotations

import asyncio
import importlib
from unittest.mock import AsyncMock

import pytest

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.schemas import RouteDecision
from tests.orchestration.test_orchestrator_process_stream_integration import (
    _install_import_stubs,
    _make_request,
    orchestrator_factory,  # noqa: F401 — pytest fixture re-export
)

STATE_FAILED = "FAILED"


class _HangingGraph:
    """Graph stub that never finishes until the test releases it."""

    def __init__(self) -> None:
        self.released = False

    async def invoke(self, state, **kwargs):
        while not self.released:
            await asyncio.sleep(0.01)
        return state


@pytest.mark.asyncio
async def test_graph_timeout_yields_error_terminal_frame_and_fails_fsm(orchestrator_factory, monkeypatch):  # noqa: F811
    _install_import_stubs()
    execution_engine_module = importlib.import_module("app.orchestration.execution_engine")
    monkeypatch.setattr(execution_engine_module, "GRAPH_TIMEOUT_SECONDS", 0.05)

    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request()

    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low"), None)
    )
    orchestrator._plan_and_validate = AsyncMock(
        side_effect=lambda **kwargs: (kwargs["route_decision"], None, None, False)
    )

    graph = _HangingGraph()
    orchestrator.graph = graph
    orchestrator._build_final_response = AsyncMock(
        side_effect=AssertionError("final response must not be built on timeout")
    )

    try:
        responses = [response async for response in orchestrator.process_stream(request)]
    finally:
        graph.released = True
        await asyncio.sleep(0.05)

    terminal_frames = [
        response
        for response in responses
        if response.finish_reason in (agent_service_pb2.STOP, agent_service_pb2.ERROR)
    ]

    assert len(terminal_frames) == 1, "timeout path must yield exactly one terminal frame"
    terminal = terminal_frames[0]
    assert terminal.finish_reason == agent_service_pb2.ERROR
    assert terminal.error.error_code == agent_service_pb2.ERROR_CODE_TIMEOUT
    assert terminal.error.retryable is True

    final_state = await orchestrator.state_manager.load_state(request.session_id)
    assert final_state is not None
    assert final_state.state == STATE_FAILED, f"FSM must leave the generating phase, got {final_state.state}"
    assert any(next_state == STATE_FAILED for next_state, _ in state_updates)

    orchestrator._build_final_response.assert_not_called()


@pytest.mark.asyncio
async def test_graph_timeout_drains_already_generated_deltas(orchestrator_factory, monkeypatch):  # noqa: F811
    _install_import_stubs()
    execution_engine_module = importlib.import_module("app.orchestration.execution_engine")
    monkeypatch.setattr(execution_engine_module, "GRAPH_TIMEOUT_SECONDS", 0.05)

    orchestrator, _, _ = orchestrator_factory()
    request = _make_request()

    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low"), None)
    )
    orchestrator._plan_and_validate = AsyncMock(
        side_effect=lambda **kwargs: (kwargs["route_decision"], None, None, False)
    )

    graph = _HangingGraph()
    orchestrator.graph = graph

    real_execute_graph = orchestrator._execute_graph

    async def execute_graph_with_pending_delta(*, state, user_id, queue, result_holder):
        # Emulate one delta the graph already produced before the timeout fired.
        await orchestrator._enqueue_stream_response(queue, agent_service_pb2.ChatResponse(delta="已生成的部分内容"))
        async for item in real_execute_graph(state=state, user_id=user_id, queue=queue, result_holder=result_holder):
            yield item

    orchestrator._execute_graph = execute_graph_with_pending_delta

    try:
        responses = [response async for response in orchestrator.process_stream(request)]
    finally:
        graph.released = True
        await asyncio.sleep(0.05)

    assert any(
        response.delta == "已生成的部分内容" for response in responses
    ), "already-generated deltas must be drained before the terminal frame"
    assert responses[-1].finish_reason == agent_service_pb2.ERROR
