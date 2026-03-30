"""
Unit tests for ExecutionEngineMixin.

Tests the execution, planning, and tool-handling methods.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestration.execution_engine import ExecutionEngineMixin


# Create a minimal class that includes the mixin
class MinimalOrchestrator(ExecutionEngineMixin):
    """Minimal orchestrator with ExecutionEngineMixin for testing."""
    def __init__(self, redis_client=None):
        self.redis = redis_client or MagicMock()
        self.tool_executor = MagicMock(execute_tool_call=AsyncMock())
        self.response_composer = MagicMock()
        self.dual_core_router = MagicMock()
        self._persist_assistant_message = AsyncMock()
        self._cache_response = AsyncMock()


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return MinimalOrchestrator()


@pytest.mark.asyncio
async def test_maybe_short_circuit_bridge_tool_returns_none_when_no_bridge_tool(orchestrator):
    """Test _maybe_short_circuit_bridge_tool returns None when no bridge tool is active."""
    result = await orchestrator._maybe_short_circuit_bridge_tool(
        active_tools=["create_task", "query_knowledge"],
        user_message="I want to learn Python",
        user_id="user-1",
        session_id="session-1",
        response_id="resp-1",
        request_id="req-1",
        trace_id="trace-1",
        workflow_id="workflow-1",
        prompt_version="v1",
        active_db=None,
    )

    assert result is None


@pytest.mark.asyncio
async def test_maybe_short_circuit_bridge_tool_returns_none_for_empty_message(orchestrator):
    """Test _maybe_short_circuit_bridge_tool returns None for empty message."""
    result = await orchestrator._maybe_short_circuit_bridge_tool(
        active_tools=["launch_prediction"],
        user_message="",
        user_id="user-1",
        session_id="session-1",
        response_id="resp-1",
        request_id="req-1",
        trace_id="trace-1",
        workflow_id="workflow-1",
        prompt_version="v1",
        active_db=None,
    )

    assert result is None


@pytest.mark.asyncio
async def test_maybe_short_circuit_bridge_tool_launch_prediction_builds_correct_arguments(orchestrator):
    """Test _maybe_short_circuit_bridge_tool builds correct arguments for launch_prediction."""
    orchestrator.tool_executor.execute_tool_call.return_value = MagicMock(
        success=True,
        data={"topic": "Will I succeed in learning Python?", "source_chat_session_id": "session-1"},
        model_dump=lambda: {"tool_name": "launch_prediction"},
    )

    result = await orchestrator._maybe_short_circuit_bridge_tool(
        active_tools=["launch_prediction"],
        user_message="Will I succeed in learning Python?",
        user_id="user-1",
        session_id="session-1",
        response_id="resp-1",
        request_id="req-1",
        trace_id="trace-1",
        workflow_id="workflow-1",
        prompt_version="v1",
        active_db=None,
    )

    orchestrator.tool_executor.execute_tool_call.assert_awaited_once()
    call_args = orchestrator.tool_executor.execute_tool_call.call_args
    assert call_args.kwargs["tool_name"] == "launch_prediction"
    assert call_args.kwargs["arguments"]["topic"] == "Will I succeed in learning Python?"
    assert call_args.kwargs["arguments"]["source_chat_session_id"] == "session-1"
    assert result is not None


@pytest.mark.asyncio
async def test_maybe_short_circuit_bridge_tool_run_quick_simulation_builds_arguments(orchestrator):
    """Test _maybe_short_circuit_bridge_tool builds correct arguments for run_quick_simulation."""
    orchestrator.tool_executor.execute_tool_call.return_value = MagicMock(
        success=True,
        data={"topic": "Simulate a Pomodoro session", "scenario_key": "study_group", "source_chat_session_id": "session-1"},
        model_dump=lambda: {"tool_name": "run_quick_simulation"},
    )

    result = await orchestrator._maybe_short_circuit_bridge_tool(
        active_tools=["run_quick_simulation"],
        user_message="Simulate a Pomodoro session",
        user_id="user-1",
        session_id="session-1",
        response_id="resp-1",
        request_id="req-1",
        trace_id="trace-1",
        workflow_id="workflow-1",
        prompt_version="v1",
        active_db=None,
    )

    orchestrator.tool_executor.execute_tool_call.assert_awaited_once()
    call_args = orchestrator.tool_executor.execute_tool_call.call_args
    assert call_args.kwargs["tool_name"] == "run_quick_simulation"
    assert call_args.kwargs["arguments"]["seed_topic"] == "Simulate a Pomodoro session"
    assert call_args.kwargs["arguments"]["source_chat_session_id"] == "session-1"
    assert result is not None


@pytest.mark.asyncio
async def test_maybe_short_circuit_bridge_tool_generate_learning_report_builds_arguments(orchestrator):
    """Test _maybe_short_circuit_bridge_tool builds correct arguments for generate_learning_report."""
    orchestrator.tool_executor.execute_tool_call.return_value = MagicMock(
        success=True,
        data={"report_preview": {"summary": "weekly summary"}, "source_chat_session_id": "session-1"},
        model_dump=lambda: {"tool_name": "generate_learning_report"},
    )

    result = await orchestrator._maybe_short_circuit_bridge_tool(
        active_tools=["generate_learning_report"],
        user_message="Generate my weekly report",
        user_id="user-1",
        session_id="session-1",
        response_id="resp-1",
        request_id="req-1",
        trace_id="trace-1",
        workflow_id="workflow-1",
        prompt_version="v1",
        active_db=None,
    )

    orchestrator.tool_executor.execute_tool_call.assert_awaited_once()
    call_args = orchestrator.tool_executor.execute_tool_call.call_args
    assert call_args.kwargs["tool_name"] == "generate_learning_report"
    assert call_args.kwargs["arguments"]["section_limit"] == 4
    assert call_args.kwargs["arguments"]["delivery_mode"] == "chat_bridge"
    assert call_args.kwargs["arguments"]["source_chat_session_id"] == "session-1"
    assert result is not None
