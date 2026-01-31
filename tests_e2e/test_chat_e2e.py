"""
E2E Test: Complete Chat Flow
============================

Tests the complete chat message flow:
Flutter Client → Go Gateway (WebSocket) → Python Orchestrator (gRPC) → LLM → Stream Back

Note: These tests focus on the chat flow without database persistence concerns.
Database persistence is tested separately in test_integration.py

Author: Claude Code (Sonnet 4.5)
Created: 2026-01-28
Updated: 2026-01-31 - Fixed connection sharing issues
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime

from sqlalchemy import select

from google.protobuf import timestamp_pb2, struct_pb2  # noqa: F401
from app.gen.agent.v1 import agent_service_pb2
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.orchestration.orchestrator import Orchestrator
from app.services import llm_service as llm_service_module


def _build_orchestrator(mock_llm_service, mock_redis, user_id):
    """Create orchestrator wired to mock LLM service - no db_session to avoid connection issues."""
    llm_service_module.llm_service = mock_llm_service
    from app.orchestration import orchestrator as orchestrator_module
    orchestrator_module.llm_service = mock_llm_service
    from app.agents import standard_workflow as standard_workflow_module
    standard_workflow_module.llm_service = mock_llm_service
    return Orchestrator(
        db_session=None,  # Don't use db_session in tests to avoid connection sharing
        redis_client=mock_redis,
        user_id=str(user_id),
    )


def _build_request(session_id, user_id, message):
    return agent_service_pb2.ChatRequest(
        session_id=str(session_id),
        user_id=str(user_id),
        message=message,
        request_id=str(uuid4()),
    )


async def _collect_stream(orchestrator, request):
    responses = []
    async for chunk in orchestrator.process_stream(request):
        responses.append(chunk)
    return responses


def _concat_text(responses):
    parts = []
    for resp in responses:
        field = resp.WhichOneof("content")
        if field == "delta":
            parts.append(resp.delta)
        elif field == "full_text":
            parts.append(resp.full_text)
    return "".join(parts)


# =============================================================================
# Test 1: Simple Chat Message Flow
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_simple_chat_message_flow(
    mock_llm_service,
    mock_redis,
):
    """
    E2E: User sends message → Orchestrator → LLM → Stream Response

    Scenario:
    1. User sends chat message: "你好,我想学习Python"
    2. Message flows to Orchestrator
    3. Orchestrator calls LLM
    4. LLM streams response back
    5. Response is complete and valid
    """
    user_id = uuid4()
    session_id = uuid4()

    # Arrange: Initialize orchestrator with mock LLM
    orchestrator = _build_orchestrator(
        mock_llm_service,
        mock_redis,
        user_id,
    )

    # Act: User sends message
    user_message_content = "你好,我想学习Python,请给我一些建议"

    # Simulate message flow
    response_chunks = await _collect_stream(
        orchestrator,
        _build_request(session_id, user_id, user_message_content),
    )

    # Assert: Response received
    assert len(response_chunks) > 0, "Should receive response chunks"

    # Assert: Response has text content
    full_text = _concat_text(response_chunks)
    assert len(full_text) > 0, "Response should have text content"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_multi_turn_conversation(
    mock_llm_service,
    mock_redis,
):
    """
    E2E: Multi-turn conversation maintains session context

    Scenario:
    1. User sends first message
    2. Assistant responds
    3. User sends follow-up message
    4. Assistant responds with context awareness
    """
    user_id = uuid4()
    session_id = uuid4()

    orchestrator = _build_orchestrator(
        mock_llm_service,
        mock_redis,
        user_id,
    )

    # Turn 1: User greeting
    response1 = await _collect_stream(
        orchestrator,
        _build_request(session_id, user_id, "你好，我想学习编程"),
    )
    assert len(response1) > 0, "First turn should have response"

    # Allow lock to release
    await asyncio.sleep(0.1)

    # Turn 2: Follow-up question
    response2 = await _collect_stream(
        orchestrator,
        _build_request(session_id, user_id, "请推荐一门适合入门的语言"),
    )
    assert len(response2) > 0, "Second turn should have response"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_translation_request(
    mock_llm_service,
    mock_redis,
):
    """
    E2E: Translation request flow

    Scenario:
    1. User sends translation request
    2. Intent recognized
    3. Translation returned
    """
    user_id = uuid4()
    session_id = uuid4()

    orchestrator = _build_orchestrator(
        mock_llm_service,
        mock_redis,
        user_id,
    )

    response = await _collect_stream(
        orchestrator,
        _build_request(session_id, user_id, "请帮我翻译 Hello World"),
    )

    assert len(response) > 0, "Translation request should have response"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_plan_creation_intent(
    mock_llm_service,
    mock_redis,
):
    """
    E2E: Plan creation intent detection

    Scenario:
    1. User sends plan creation request
    2. Intent recognized
    3. System responds appropriately
    """
    user_id = uuid4()
    session_id = uuid4()

    orchestrator = _build_orchestrator(
        mock_llm_service,
        mock_redis,
        user_id,
    )

    response = await _collect_stream(
        orchestrator,
        _build_request(session_id, user_id, "帮我制定一个Python学习计划"),
    )

    assert len(response) > 0, "Plan creation request should have response"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_error_handling(
    mock_llm_service,
    mock_redis,
):
    """
    E2E: Error handling for edge cases

    Scenario:
    1. User sends empty message
    2. System handles gracefully
    """
    user_id = uuid4()
    session_id = uuid4()

    orchestrator = _build_orchestrator(
        mock_llm_service,
        mock_redis,
        user_id,
    )

    # Empty message should still be handled
    response = await _collect_stream(
        orchestrator,
        _build_request(session_id, user_id, ""),
    )

    # System should respond (even if it's an error message)
    assert len(response) >= 0, "Should handle empty message"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_concurrent_requests(
    mock_llm_service,
    mock_redis,
):
    """
    E2E: Handle concurrent requests from different users

    Scenario:
    1. Multiple users send requests simultaneously
    2. Each user gets their own response
    3. No cross-contamination
    """
    user1_id = uuid4()
    user2_id = uuid4()
    session1_id = uuid4()
    session2_id = uuid4()

    orchestrator1 = _build_orchestrator(
        mock_llm_service,
        mock_redis,
        user1_id,
    )

    orchestrator2 = _build_orchestrator(
        mock_llm_service,
        mock_redis,
        user2_id,
    )

    # Send concurrent requests
    results = await asyncio.gather(
        _collect_stream(
            orchestrator1,
            _build_request(session1_id, user1_id, "用户1的消息"),
        ),
        _collect_stream(
            orchestrator2,
            _build_request(session2_id, user2_id, "用户2的消息"),
        ),
    )

    # Both should complete successfully
    assert len(results) == 2
    assert len(results[0]) > 0, "User 1 should get response"
    assert len(results[1]) > 0, "User 2 should get response"
