import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.orchestrator import ChatOrchestrator


class _FakeTool:
    def __init__(self, name: str):
        self.name = name

    def to_openai_schema(self) -> dict:
        return {"type": "function", "function": {"name": self.name}}


@pytest.mark.asyncio
async def test_get_tools_schema_respects_active_tools():
    orchestrator = object.__new__(ChatOrchestrator)

    with patch(
        "app.orchestration.orchestrator.dynamic_tool_registry.get_all_tools",
        return_value=[_FakeTool("tool_alpha"), _FakeTool("tool_beta")],
    ):
        tools = await orchestrator._get_tools_schema(
            active_tools=["tool_beta", "missing_tool", "tool_alpha", "tool_beta"],
        )

    assert [tool["function"]["name"] for tool in tools] == ["tool_beta", "tool_alpha"]


def test_merge_request_history_preserves_db_history_and_dedupes_overlap():
    orchestrator = object.__new__(ChatOrchestrator)
    conversation_context = {
        "messages": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ],
        "summary": None,
    }
    request_history = [
        agent_service_pb2.ChatMessage(role="user", content="hello"),
        agent_service_pb2.ChatMessage(role="assistant", content="hi there"),
        agent_service_pb2.ChatMessage(role="tool", content='{"ok": true}', tool_call_id="call-1"),
    ]

    merged = orchestrator._merge_request_history_into_conversation_context(
        conversation_context,
        request_history,
    )

    assert merged["messages"] == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
        {"role": "tool", "content": '{"ok": true}', "tool_call_id": "call-1"},
    ]


@pytest.mark.asyncio
async def test_continue_after_tool_result_uses_structured_history():
    orchestrator = object.__new__(ChatOrchestrator)
    orchestrator._persist_assistant_message = AsyncMock()
    orchestrator._record_decision = AsyncMock()
    orchestrator._cache_response = AsyncMock()
    orchestrator._emit_system_updates = AsyncMock(return_value=[])
    orchestrator._extract_llm_profile_meta = lambda _ctx: {"verbosity_target": "balanced"}

    request = agent_service_pb2.ChatRequest(
        user_id="user-1",
        session_id="session-1",
        request_id="req-1",
        tool_result=agent_service_pb2.ToolResult(
            tool_call_id="call-1",
            tool_name="search_docs",
            result_json='{"answer": "42"}',
        ),
        history=[
            agent_service_pb2.ChatMessage(
                role="assistant",
                content="Calling tool",
                metadata={
                    "tool_calls": json.dumps(
                        [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {"name": "search_docs", "arguments": '{"query":"life"}'},
                            }
                        ]
                    )
                },
            )
        ],
    )

    conversation_context = orchestrator._merge_request_history_into_conversation_context(
        {"messages": [], "summary": None},
        list(request.history),
    )

    with patch(
        "app.orchestration.orchestrator.llm_service.continue_with_tool_results",
        AsyncMock(return_value=SimpleNamespace(content="Structured continuation response")),
    ) as mock_continue:
        responses = [
            response
            async for response in orchestrator._continue_after_tool_result(
                request=request,
                active_db=None,
                user_id="user-1",
                session_id="session-1",
                response_id="resp-1",
                request_id="req-1",
                trace_id="trace-1",
                workflow_id="standard_chat",
                prompt_version="v1",
                user_context_payload={},
                conversation_context=conversation_context,
            )
        ]

    mock_continue.assert_awaited_once()
    call_kwargs = mock_continue.await_args.kwargs
    assert call_kwargs["conversation_history"][0]["tool_calls"][0]["id"] == "call-1"
    assert call_kwargs["tool_results"][0]["tool_call_id"] == "call-1"
    assert call_kwargs["tool_results"][0]["result"] == {"answer": "42"}
    assert responses[-1].full_text == "Structured continuation response"
    assert responses[-1].finish_reason == agent_service_pb2.STOP
