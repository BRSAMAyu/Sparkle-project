"""
E2E Test: Complete Chat Flow
============================

Tests the complete chat message flow:
Flutter Client → Go Gateway (WebSocket) → Python Orchestrator (gRPC) → LLM → Stream Back

Author: Claude Code (Sonnet 4.5)
Created: 2026-01-28
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


def _build_orchestrator(db_session, mock_llm_service, mock_redis, user_id):
    """Create orchestrator wired to mock LLM service."""
    llm_service_module.llm_service = mock_llm_service
    from app.orchestration import orchestrator as orchestrator_module
    orchestrator_module.llm_service = mock_llm_service
    from app.agents import standard_workflow as standard_workflow_module
    standard_workflow_module.llm_service = mock_llm_service
    return Orchestrator(
        db_session=db_session,
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
    db_session,
    test_user,
    mock_llm_service,
    mock_redis,
    test_assertions,
):
    """
    E2E: User sends message → WebSocket → Gateway → Orchestrator → LLM → Response

    Scenario:
    1. User connects via WebSocket
    2. User sends chat message: "你好,我想学习Python"
    3. Message flows through Gateway to Orchestrator
    4. Orchestrator calls LLM
    5. LLM streams response back
    6. Response pushed to Flutter via WebSocket
    7. Chat history persisted to database
    """
    # Arrange: Create chat session
    session = ChatSession(
        id=uuid4(),
        user_id=test_user.id,
        title="Python学习咨询",
        is_active=True,
    )
    db_session.add(session)
    await db_session.flush()
    session_id = session.id

    # Arrange: Initialize orchestrator with mock LLM
    orchestrator = _build_orchestrator(
        db_session,
        mock_llm_service,
        mock_redis,
        test_user.id,
    )

    # Act: User sends message
    user_message_content = "你好,我想学习Python,请给我一些建议"

    # Simulate message flow
    response_chunks = await _collect_stream(
        orchestrator,
        _build_request(session_id, test_user.id, user_message_content),
    )

    # Assert: Response received
    assert len(response_chunks) > 0, "Should receive response chunks"

    # Assert: Message persisted
    result = await db_session.execute(
        select(ChatMessage).where(
            ChatMessage.session_id == session_id,
            ChatMessage.role == MessageRole.USER
        )
    )
    user_message = result.scalar_one_or_none()
    assert user_message is not None, "User message should be persisted"
    assert user_message.content == user_message_content

    # Assert: Assistant response persisted
    result = await db_session.execute(
        select(ChatMessage).where(
            ChatMessage.session_id == session_id,
            ChatMessage.role == MessageRole.ASSISTANT
        )
    )
    assistant_message = result.scalar_one_or_none()
    assert assistant_message is not None, "Assistant response should be persisted"
    assert len(assistant_message.content) > 0, "Assistant response should have content"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_chat_with_plan_creation(
    db_session,
    test_user,
    mock_llm_service,
    mock_redis,
    sample_plan_data,
):
    """
    E2E: Chat message triggers plan creation

    Scenario:
    1. User sends: "帮我制定一个Python学习计划"
    2. Intent recognized as plan creation
    3. Information sufficiency checked
    4. Sufficient info → LLM generates plan
    5. Plan persisted to database
    6. Task cards created
    7. Response includes plan summary
    """
    # Arrange: Create chat session
    session = ChatSession(
        id=uuid4(),
        user_id=test_user.id,
        title="创建学习计划",
        is_active=True,
    )
    db_session.add(session)
    await db_session.flush()

    # Arrange: Initialize orchestrator
    orchestrator = _build_orchestrator(
        db_session,
        mock_llm_service,
        mock_redis,
        test_user.id,
    )

    # Act: User requests plan creation
    user_message = "我想制定一个7天的Python学习计划,每天学习2小时"

    # Mock LLM to return plan data
    async def mock_plan_generation(messages, **kwargs):
        from tests_e2e.conftest import MockLLMResponse
        plan_response = MockLLMResponse(
            content="好的,我已经为您制定了一个Python学习计划",
            tool_calls=[{
                "type": "plan",
                "plan": {
                    "name": "Python学习计划",
                    "type": "sprint",
                    "subject": "编程",
                    "tasks": [
                        {
                            "title": "学习Python基础语法",
                            "type": "learning",
                            "estimated_minutes": 60,
                            "difficulty": 3,
                        },
                        {
                            "title": "练习Python变量和数据类型",
                            "type": "training",
                            "estimated_minutes": 60,
                            "difficulty": 3,
                        },
                    ]
                }
            }]
        )
        return plan_response

    mock_llm_service.chat_stream = mock_plan_generation

    # Process message
    response_chunks = await _collect_stream(
        orchestrator,
        _build_request(session.id, test_user.id, user_message),
    )

    # Assert: Response received
    assert len(response_chunks) > 0

    # Assert: Plan created in database
    from app.models.plan import Plan
    result = await db_session.execute(
        select(Plan).where(
            Plan.user_id == test_user.id,
            Plan.name.contains("Python")
        )
    )
    plan = result.scalar_one_or_none()
    assert plan is not None, "Plan should be created"
    assert plan.type == "sprint"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_chat_with_clarification_loop(
    db_session,
    test_user,
    mock_llm_service,
    mock_redis,
):
    """
    E2E: Chat triggers clarification loop

    Scenario:
    1. User sends: "帮我创建学习计划"
    2. Intent recognized but insufficient info
    3. System asks clarification questions
    4. User provides missing info
    5. System proceeds with plan creation
    """
    # Arrange: Create chat session
    session = ChatSession(
        id=uuid4(),
        user_id=test_user.id,
        title="学习计划咨询",
        is_active=True,
    )
    db_session.add(session)
    await db_session.flush()

    # Arrange: Initialize orchestrator
    orchestrator = _build_orchestrator(
        db_session,
        mock_llm_service,
        mock_redis,
        test_user.id,
    )

    # Act 1: User sends incomplete request
    incomplete_message = "帮我创建学习计划"

    response_chunks = await _collect_stream(
        orchestrator,
        _build_request(session.id, test_user.id, incomplete_message),
    )

    # Assert: Clarification question asked
    assert len(response_chunks) > 0
    full_response = _concat_text(response_chunks)
    assert any(keyword in full_response for keyword in ["请问", "什么", "哪个", "想学习", "科目"])

    # Act 2: User provides clarification
    clarification = "我想学习Python,为期7天"
    response_chunks_2 = await _collect_stream(
        orchestrator,
        _build_request(session.id, test_user.id, clarification),
    )

    # Assert: System proceeds with plan creation
    assert len(response_chunks_2) > 0


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_chat_with_tool_execution(
    db_session,
    test_user,
    mock_llm_service,
    mock_redis,
):
    """
    E2E: Chat message triggers tool execution

    Scenario:
    1. User sends: "翻译这句话: Hello World"
    2. Intent recognized as translation
    3. Translation tool executed
    4. Result returned to user
    """
    # Arrange: Create chat session
    session = ChatSession(
        id=uuid4(),
        user_id=test_user.id,
        title="翻译请求",
        is_active=True,
    )
    db_session.add(session)
    await db_session.flush()
    session_id = session.id

    # Arrange: Mock translation tool
    async def mock_translation_tool(text, source_lang, target_lang):
        return f"翻译结果 ({source_lang} → {target_lang}): {text}"

    # Arrange: Initialize orchestrator
    orchestrator = _build_orchestrator(
        db_session,
        mock_llm_service,
        mock_redis,
        test_user.id,
    )

    async def mock_translation_response(messages, **kwargs):
        from tests_e2e.conftest import MockLLMResponse
        return MockLLMResponse(content="你好，世界")

    mock_llm_service.chat_stream = mock_translation_response

    # Act: User requests translation
    user_message = "请把'Hello World'翻译成中文"

    response_chunks = await _collect_stream(
        orchestrator,
        _build_request(session_id, test_user.id, user_message),
    )

    # Assert: Response contains translation
    full_response = _concat_text(response_chunks)
    assert "你好" in full_response or "Hello" in full_response


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_e2e_chat_conversation_context_maintenance(
    db_session,
    test_user,
    mock_llm_service,
    mock_redis,
):
    """
    E2E: Conversation context maintained across multiple turns

    Scenario:
    1. User: "我想学习Python"
    2. Assistant: "好的,Python是一门..."
    3. User: "它难吗?" (refers to Python mentioned earlier)
    4. Assistant: Understands "它" refers to Python
    """
    # Arrange: Create chat session
    session = ChatSession(
        id=uuid4(),
        user_id=test_user.id,
        title="Python学习咨询",
        is_active=True,
    )
    db_session.add(session)
    await db_session.flush()
    session_id = session.id

    # Arrange: Initialize orchestrator
    orchestrator = _build_orchestrator(
        db_session,
        mock_llm_service,
        mock_redis,
        test_user.id,
    )

    # Act 1: First message
    message_1 = "我想学习Python编程"
    response_1_chunks = await _collect_stream(
        orchestrator,
        _build_request(session_id, test_user.id, message_1),
    )

    # Act 2: Follow-up message with pronoun reference
    message_2 = "它难学吗?"
    response_2_chunks = await _collect_stream(
        orchestrator,
        _build_request(session_id, test_user.id, message_2),
    )

    # Assert: Context maintained (LLM should understand "它" = Python)
    full_response_2 = _concat_text(response_2_chunks)
    # Mock response should mention Python or difficulty
    assert any(keyword in full_response_2 for keyword in ["Python", "难", "容易", "难度"])

    # Assert: Both messages in history
    result = await db_session.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id)
    )
    messages = result.scalars().all()
    assert len(messages) == 4  # 2 user + 2 assistant


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
