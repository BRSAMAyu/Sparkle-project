from __future__ import annotations

import hashlib

from google.protobuf import struct_pb2

from app.gen.agent.v1 import agent_service_pb2


def _struct(data: dict) -> struct_pb2.Struct:
    message = struct_pb2.Struct()
    message.update(data)
    return message


def test_chat_request_deterministic_serialization():
    request = agent_service_pb2.ChatRequest(
        user_id="user-1",
        session_id="session-1",
        message="hello",
        user_profile=agent_service_pb2.UserProfile(
            nickname="Sparkle",
            timezone="Asia/Shanghai",
            language="zh-CN",
            is_pro=True,
            preferences={"tone": "concise", "mode": "coach"},
            extra_context='{"focus":"algorithms"}',
            level=7,
            avatar_url="https://example.com/avatar.png",
        ),
        extra_context=_struct({"client": "flutter", "build": "2026.03"}),
        history=[
            agent_service_pb2.ChatMessage(
                role="user",
                content="previous question",
                metadata={"session": "warm"},
            )
        ],
        config=agent_service_pb2.ChatConfig(
            model="gpt-5.4",
            temperature=0.2,
            max_tokens=1024,
            tools_enabled=True,
        ),
        request_id="req-1",
        file_ids=["file-1", "file-2"],
        include_references=True,
        active_tools=["search", "plan"],
        chat_mode="standard",
    )

    serialized = request.SerializeToString(deterministic=True)
    digest = hashlib.sha256(serialized).hexdigest()
    restored = agent_service_pb2.ChatRequest()
    restored.ParseFromString(serialized)

    assert serialized
    assert len(digest) == 64
    assert restored == request


def test_chat_response_all_oneofs_serialize():
    variants = [
        agent_service_pb2.ChatResponse(delta="hello"),
        agent_service_pb2.ChatResponse(
            tool_call=agent_service_pb2.ToolCall(id="tool-1", name="search", arguments='{"q":"llm"}')
        ),
        agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING,
                details="thinking",
            )
        ),
        agent_service_pb2.ChatResponse(full_text="full answer"),
        agent_service_pb2.ChatResponse(
            error=agent_service_pb2.Error(
                message="timeout",
                retryable=True,
                error_code=agent_service_pb2.ERROR_CODE_TIMEOUT,
            )
        ),
        agent_service_pb2.ChatResponse(
            usage=agent_service_pb2.Usage(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
                cost_micro_usd=120,
            )
        ),
        agent_service_pb2.ChatResponse(
            citations=agent_service_pb2.CitationBlock(
                citations=[
                    agent_service_pb2.Citation(
                        id="c1",
                        title="Doc",
                        content="snippet",
                        source_type="document",
                    )
                ]
            )
        ),
        agent_service_pb2.ChatResponse(
            tool_result=agent_service_pb2.ToolResultPayload(
                tool_name="search",
                success=True,
                data=_struct({"items": 2}),
                widget_type="execution_summary",
                widget_data=_struct({"status": "success"}),
                tool_call_id="tool-1",
            )
        ),
        agent_service_pb2.ChatResponse(
            intervention=agent_service_pb2.InterventionPayload(
                request=agent_service_pb2.InterventionRequest(
                    id="int-1",
                    topic="review",
                    content=_struct({"title": "Review now"}),
                )
            )
        ),
    ]

    for response in variants:
        assert response.SerializeToString(deterministic=True)


def test_chat_response_oneof_deserialization():
    response = agent_service_pb2.ChatResponse(delta="hello")

    serialized = response.SerializeToString(deterministic=True)
    restored = agent_service_pb2.ChatResponse()
    restored.ParseFromString(serialized)

    assert restored.WhichOneof("content") == "delta"
    assert restored.delta == "hello"


def test_user_profile_map_serialization():
    profile = agent_service_pb2.UserProfile(
        nickname="Ada",
        preferences={
            "tone": "warm",
            "format": "checklist",
        },
    )

    serialized = profile.SerializeToString(deterministic=True)
    restored = agent_service_pb2.UserProfile()
    restored.ParseFromString(serialized)

    assert dict(restored.preferences) == {
        "tone": "warm",
        "format": "checklist",
    }


def test_chat_request_tool_result_oneof():
    request = agent_service_pb2.ChatRequest(
        user_id="user-1",
        session_id="session-1",
        tool_result=agent_service_pb2.ToolResult(
            tool_call_id="tool-1",
            tool_name="search",
            result_json='{"items":1}',
            is_error=False,
        ),
    )

    restored = agent_service_pb2.ChatRequest()
    restored.ParseFromString(request.SerializeToString(deterministic=True))

    assert restored.WhichOneof("input") == "tool_result"
    assert restored.tool_result.tool_name == "search"
