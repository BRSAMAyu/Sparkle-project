"""Regression test for ISSUE-20260505-1100-D4.

Verifies that tool result continuation errors are sanitized through
build_safe_chat_error instead of leaking raw exception details.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.gen.agent.v1 import agent_service_pb2


def _make_request():
    req = agent_service_pb2.ChatRequest()
    req.tool_result.tool_call_id = "tc1"
    req.tool_result.tool_name = "test_tool"
    req.tool_result.result_json = "{}"
    return req


def _make_engine():
    from app.orchestration.execution_engine import ExecutionEngineMixin

    engine = ExecutionEngineMixin.__new__(ExecutionEngineMixin)
    engine._build_routing_history = lambda ctx: []
    engine._coerce_tool_result_payload = lambda payload: "{}"
    return engine


@pytest.mark.asyncio
async def test_tool_result_continuation_error_uses_safe_message():
    """Tool result continuation error must NOT contain raw exception details."""
    engine = _make_engine()

    raw_exc = Exception("HTTPStatusError('429 Rate Limit', url='https://internal-llm-endpoint/v1/chat')")

    mock_llm = MagicMock()
    mock_llm.continue_with_tool_results = AsyncMock(side_effect=raw_exc)

    with patch("app.orchestration.execution_engine.llm_service", mock_llm):
        responses = []
        async for resp in engine._continue_after_tool_result(
            request=_make_request(),
            active_db=None,
            user_id="test-user",
            session_id="test-session",
            response_id="test-resp",
            request_id="test-req",
            trace_id="test-trace",
            workflow_id="test-wf",
            prompt_version="1",
            user_context_payload=None,
            conversation_context=None,
        ):
            responses.append(resp)

    assert len(responses) == 1
    error_msg = responses[0].error.message
    assert "internal-llm-endpoint" not in error_msg, (
        f"Error message leaks internal endpoint: {error_msg}"
    )
    assert "429" not in error_msg, (
        f"Error message leaks HTTP status code: {error_msg}"
    )
    assert "HTTPStatusError" not in error_msg, (
        f"Error message leaks exception type: {error_msg}"
    )


@pytest.mark.asyncio
async def test_tool_result_continuation_still_logs_raw_error():
    """Raw exception must still be logged for observability."""
    engine = _make_engine()
    raw_exc = RuntimeError("DB connection lost: postgres://internal-host:5432")

    mock_llm = MagicMock()
    mock_llm.continue_with_tool_results = AsyncMock(side_effect=raw_exc)

    with patch("app.orchestration.execution_engine.llm_service", mock_llm), \
         patch("app.orchestration.execution_engine.logger") as mock_logger:
        async for _ in engine._continue_after_tool_result(
            request=_make_request(),
            active_db=None,
            user_id="test-user",
            session_id="test-session",
            response_id="test-resp",
            request_id="test-req",
            trace_id="test-trace",
            workflow_id="test-wf",
            prompt_version="1",
            user_context_payload=None,
            conversation_context=None,
        ):
            pass

        mock_logger.error.assert_called_once()
        logged_msg = mock_logger.error.call_args[0][0]
        assert "postgres://internal-host" in logged_msg, (
            f"Raw exception should be logged, got: {logged_msg}"
        )
