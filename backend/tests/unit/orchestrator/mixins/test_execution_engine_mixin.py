"""
Unit tests for ExecutionEngineMixin.

Tests the execution, planning, and tool-handling methods.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.execution_intent import ExecutionIntentStatus
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


@pytest.mark.asyncio
async def test_maybe_short_circuit_openclaw_chat_control_returns_none_for_explanatory_prompt(orchestrator):
    result = await orchestrator._maybe_short_circuit_openclaw_chat_control(
        active_tools=[],
        user_message="解释一下 git rebase 是什么",
        request_extra_context={},
        user_id="3b3f4d7e-7544-41d2-b17a-f3cd0ba8f2a1",
        session_id="session-1",
        response_id="resp-1",
        request_id="req-1",
        trace_id="trace-1",
        workflow_id="workflow-1",
        prompt_version="v1",
        active_db=MagicMock(),
    )

    assert result is None


@pytest.mark.asyncio
async def test_maybe_short_circuit_openclaw_chat_control_emits_tool_result(orchestrator, monkeypatch):
    intent = MagicMock(
        id="intent-1",
        status=ExecutionIntentStatus.SUCCEEDED,
        error_message=None,
        target_env=None,
    )
    record = MagicMock(
        id="record-1",
        error_message=None,
        parsed_output={"summary": "workspace clean"},
        approval_requested=0,
        raw_response={
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary":"workspace clean"}',
                        }
                    ],
                }
            ]
        },
    )

    service_instance = MagicMock()
    service_instance.handoff_chat_control = AsyncMock(return_value=(intent, record))

    monkeypatch.setattr(
        "app.orchestration.execution_engine.ExecutionService",
        MagicMock(return_value=service_instance),
    )

    responses = await orchestrator._maybe_short_circuit_openclaw_chat_control(
        active_tools=[],
        user_message="在我的电脑上运行 git status",
        request_extra_context={},
        user_id="3b3f4d7e-7544-41d2-b17a-f3cd0ba8f2a1",
        session_id="session-1",
        response_id="resp-1",
        request_id="req-1",
        trace_id="trace-1",
        workflow_id="workflow-1",
        prompt_version="v1",
        active_db=MagicMock(),
    )

    assert responses is not None
    assert any(response.HasField("tool_result") for response in responses)
    service_instance.handoff_chat_control.assert_awaited_once()


@pytest.mark.asyncio
async def test_stream_openclaw_chat_control_emits_live_status_updates(orchestrator, monkeypatch):
    intent = MagicMock(
        id="intent-1",
        status=ExecutionIntentStatus.SUCCEEDED,
        error_message=None,
        target_env=None,
    )
    record = MagicMock(
        id="record-1",
        error_message=None,
        parsed_output={"summary": "workspace clean"},
        approval_requested=0,
        raw_response={
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary":"workspace clean"}',
                        }
                    ],
                }
            ]
        },
    )

    async def _handoff_chat_control(**kwargs):
        stream_sink = kwargs["stream_sink"]
        await stream_sink(
            "execution_lifecycle",
            {"message": "正在连接你的 OpenClaw 并启动执行", "progress_hint": 0.35},
        )
        await stream_sink(
            "execution_tool_call",
            {"message": "正在访问目标网页（https://example.com）", "progress_hint": 0.55},
        )
        await stream_sink(
            "execution_delta",
            {"text": "页面标题：Example Domain", "progress_hint": 0.7},
        )
        return intent, record

    service_instance = MagicMock()
    service_instance.handoff_chat_control = AsyncMock(side_effect=_handoff_chat_control)

    monkeypatch.setattr(
        "app.orchestration.execution_engine.ExecutionService",
        MagicMock(return_value=service_instance),
    )

    responses = [
        response
        async for response in orchestrator._stream_openclaw_chat_control(
            active_tools=[],
            user_message="在我的电脑上打开浏览器访问 example.com",
            request_extra_context={"openclaw_chat_control": True},
            user_id="3b3f4d7e-7544-41d2-b17a-f3cd0ba8f2a1",
            session_id="session-1",
            response_id="resp-1",
            request_id="req-1",
            trace_id="trace-1",
            workflow_id="workflow-1",
            prompt_version="v1",
            active_db=MagicMock(),
        )
    ]

    status_details = [
        response.status_update.details
        for response in responses
        if response.HasField("status_update")
    ]
    assert any("正在连接你的 OpenClaw" in details for details in status_details)
    assert any("正在访问目标网页" in details for details in status_details)
    assert any("页面标题：Example Domain" in details for details in status_details)
    assert any(response.HasField("tool_result") for response in responses)


@pytest.mark.asyncio
async def test_stream_openclaw_chat_control_gracefully_degrades_to_manual_steps(orchestrator, monkeypatch):
    service_instance = MagicMock()
    service_instance.handoff_chat_control = AsyncMock(side_effect=ValueError("pairing required"))
    service_instance._infer_chat_control_target_env.return_value = None
    service_instance.build_manual_fallback = AsyncMock(
        return_value={
            "suggestion": "当前连接不可用，我先给你一份手动步骤。",
            "manual_only": True,
            "manual_steps": [
                {"title": "打开终端", "description": "在你的电脑上先打开终端。"},
            ],
        }
    )

    monkeypatch.setattr(
        "app.orchestration.execution_engine.ExecutionService",
        MagicMock(return_value=service_instance),
    )

    responses = [
        response
        async for response in orchestrator._stream_openclaw_chat_control(
            active_tools=[],
            user_message="在我的电脑上运行 git status",
            request_extra_context={"openclaw_chat_control": True},
            user_id="3b3f4d7e-7544-41d2-b17a-f3cd0ba8f2a1",
            session_id="session-1",
            response_id="resp-1",
            request_id="req-1",
            trace_id="trace-1",
            workflow_id="workflow-1",
            prompt_version="v1",
            active_db=MagicMock(),
        )
    ]

    tool_result = next(response.tool_result for response in responses if response.HasField("tool_result"))
    assert tool_result.data.fields["status"].string_value == "degraded"
