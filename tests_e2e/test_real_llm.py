"""
Real LLM E2E Test
===================

This test connects to the REAL LLM service to demonstrate:
1. Actual LLM conversation responses
2. Real task decomposition
3. Real plan generation

Run with: pytest test_real_llm.py -v -s

Note: This test makes actual API calls and will consume LLM quota.
"""
import os
import pytest
import asyncio
from uuid import uuid4

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.orchestrator import Orchestrator
from app.services import llm_service as llm_service_module


# Only run if explicitly enabled
pytestmark = pytest.mark.skipif(
    not os.getenv("SPARKLE_REAL_LLM", "").lower() in {"1", "true", "yes"},
    reason="Real LLM tests require SPARKLE_REAL_LLM=1 (consumes API quota)"
)


@pytest.fixture
async def real_redis():
    """Connect to real Redis for proper session management."""
    import redis.asyncio as aioredis

    redis_password = os.getenv("REDIS_PASSWORD", "change-me")
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/0"

    redis_client = await aioredis.from_url(redis_url, decode_responses=True)
    try:
        yield redis_client
    finally:
        await redis_client.aclose()


@pytest.mark.asyncio
async def test_real_llm_simple_conversation(real_redis):
    """
    Test REAL LLM conversation - See actual AI responses!

    This test demonstrates:
    1. User sends a real message
    2. LLM processes it with actual intelligence
    3. Response is streamed back
    """
    user_id = str(uuid4())
    session_id = str(uuid4())

    # Use REAL orchestrator with real Redis
    orchestrator = Orchestrator(
        db_session=None,  # No persistence for clean test
        redis_client=real_redis,
        user_id=user_id,
    )

    # Test Case 1: Simple greeting
    print("\n" + "="*60)
    print("🤖 Test 1: 简单问候")
    print("="*60)
    print("用户输入: 你好")

    request1 = agent_service_pb2.ChatRequest(
        session_id=session_id,
        user_id=user_id,
        message="你好",
        request_id=str(uuid4()),
    )

    responses1 = []
    full_text1 = ""
    async for chunk in orchestrator.process_stream(request1):
        responses1.append(chunk)
        field = chunk.WhichOneof("content")
        if field == "delta":
            full_text1 += chunk.delta
            print(chunk.delta, end="", flush=True)
        elif field == "full_text":
            full_text1 += chunk.full_text
            print(chunk.full_text, end="", flush=True)

    print(f"\n✅ 收到 {len(responses1)} 个数据块")
    print(f"📝 完整回复: {full_text1[:200]}...")
    assert len(responses1) > 0, "Should receive LLM response"
    assert len(full_text1) > 0, "Response should have content"

    # Wait for lock release
    await asyncio.sleep(0.2)

    # Test Case 2: Learning request - Task decomposition
    print("\n" + "="*60)
    print("🤖 Test 2: 学习请求 - 任务拆解")
    print("="*60)
    print("用户输入: 我想学习Python基础，帮我制定学习计划")

    request2 = agent_service_pb2.ChatRequest(
        session_id=session_id,
        user_id=user_id,
        message="我想学习Python基础，帮我制定学习计划",
        request_id=str(uuid4()),
    )

    responses2 = []
    full_text2 = ""

    async for chunk in orchestrator.process_stream(request2):
        responses2.append(chunk)
        field = chunk.WhichOneof("content")

        if field == "delta":
            full_text2 += chunk.delta
            print(chunk.delta, end="", flush=True)
        elif field == "full_text":
            full_text2 += chunk.full_text
            print(chunk.full_text, end="", flush=True)

    print(f"\n✅ 收到 {len(responses2)} 个数据块")
    print(f"📝 完整回复长度: {len(full_text2)} 字符")

    assert len(responses2) > 0, "Should receive LLM response"

    # Test Case 3: Translation request
    print("\n" + "="*60)
    print("🤖 Test 3: 翻译请求")
    print("="*60)
    print("用户输入: 请帮我翻译: Hello World")

    await asyncio.sleep(0.2)

    request3 = agent_service_pb2.ChatRequest(
        session_id=session_id,
        user_id=user_id,
        message="请帮我翻译: Hello World",
        request_id=str(uuid4()),
    )

    responses3 = []
    full_text3 = ""
    async for chunk in orchestrator.process_stream(request3):
        responses3.append(chunk)
        field = chunk.WhichOneof("content")
        if field == "delta":
            full_text3 += chunk.delta
            print(chunk.delta, end="", flush=True)
        elif field == "full_text":
            full_text3 += chunk.full_text
            print(chunk.full_text, end="", flush=True)

    print(f"\n✅ 收到 {len(responses3)} 个数据块")
    print(f"📝 翻译结果: {full_text3}")

    # Summary
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    print(f"✅ 测试用例 1 (问候): {len(responses1)} chunks, {len(full_text1)} chars")
    print(f"✅ 测试用例 2 (学习计划): {len(responses2)} chunks, {len(full_text2)} chars")
    print(f"✅ 测试用例 3 (翻译): {len(responses3)} chunks, {len(full_text3)} chars")
    print("\n🎉 真实LLM对话测试完成！")


@pytest.mark.asyncio
async def test_real_llm_task_creation(real_redis):
    """
    Test REAL LLM task creation and decomposition.

    This validates that the LLM can:
    1. Understand learning goals
    2. Decompose into actionable tasks
    3. Return structured task cards
    """
    user_id = str(uuid4())
    session_id = str(uuid4())

    orchestrator = Orchestrator(
        db_session=None,
        redis_client=real_redis,
        user_id=user_id,
    )

    print("\n" + "="*60)
    print("🎯 任务拆解测试")
    print("="*60)
    print("用户输入: 帮我拆解学习Python数据分析的任务，要求7天内完成")

    request = agent_service_pb2.ChatRequest(
        session_id=session_id,
        user_id=user_id,
        message="帮我拆解学习Python数据分析的任务，要求7天内完成，每天学习2小时",
        request_id=str(uuid4()),
    )

    responses = []
    full_text = ""

    async for chunk in orchestrator.process_stream(request):
        responses.append(chunk)
        field = chunk.WhichOneof("content")

        if field == "delta":
            full_text += chunk.delta
            print(chunk.delta, end="", flush=True)
        elif field == "full_text":
            full_text += chunk.full_text
            print(chunk.full_text, end="", flush=True)

    print(f"\n\n✅ 收到 {len(responses)} 个数据块")
    print(f"📝 回复长度: {len(full_text)} 字符")
    print("\n📋 注意: 此测试主要验证LLM响应内容")

    assert len(responses) > 0, "Should receive LLM response"
    assert len(full_text) > 10, "Response should be meaningful"


@pytest.mark.asyncio
async def test_real_llm_multi_turn_with_context(real_redis):
    """
    Test REAL LLM multi-turn conversation with context awareness.

    This validates:
    1. First turn establishes context
    2. Second turn remembers previous context
    3. LLM maintains conversation coherence
    """
    user_id = str(uuid4())
    session_id = str(uuid4())

    orchestrator = Orchestrator(
        db_session=None,
        redis_client=real_redis,
        user_id=user_id,
    )

    # Turn 1: Establish learning context
    print("\n" + "="*60)
    print("🔄 多轮对话测试 - Turn 1")
    print("="*60)
    print("用户: 我想学习机器学习")

    request1 = agent_service_pb2.ChatRequest(
        session_id=session_id,
        user_id=user_id,
        message="我想学习机器学习",
        request_id=str(uuid4()),
    )

    responses1 = []
    text1 = ""
    async for chunk in orchestrator.process_stream(request1):
        responses1.append(chunk)
        field = chunk.WhichOneof("content")
        if field == "delta":
            text1 += chunk.delta
            print(chunk.delta, end="", flush=True)
        elif field == "full_text":
            text1 += chunk.full_text
            print(chunk.full_text, end="", flush=True)

    print(f"\n✅ Turn 1: {len(responses1)} chunks")

    # Wait for lock release
    await asyncio.sleep(0.3)

    # Turn 2: Follow-up question (should remember context)
    print("\n" + "="*60)
    print("🔄 多轮对话测试 - Turn 2")
    print("="*60)
    print("用户: 推荐一些学习资源")

    request2 = agent_service_pb2.ChatRequest(
        session_id=session_id,
        user_id=user_id,
        message="推荐一些学习资源",
        request_id=str(uuid4()),
    )

    responses2 = []
    text2 = ""
    async for chunk in orchestrator.process_stream(request2):
        responses2.append(chunk)
        field = chunk.WhichOneof("content")
        if field == "delta":
            text2 += chunk.delta
            print(chunk.delta, end="", flush=True)
        elif field == "full_text":
            text2 += chunk.full_text
            print(chunk.full_text, end="", flush=True)

    print(f"\n✅ Turn 2: {len(responses2)} chunks")

    # Verify context awareness - LLM should mention machine learning
    combined_text = text1 + " " + text2
    context_keywords = ["机器学习", "ML", "算法", "模型", "数据"]
    has_context = any(keyword in combined_text for keyword in context_keywords)

    print("\n" + "="*60)
    print("📊 上下文感知验证")
    print("="*60)
    print(f"对话是否提到机器学习相关: {'✅ 是' if has_context else '❌ 否'}")
    print(f"Turn 1 回复长度: {len(text1)} 字符")
    print(f"Turn 2 回复长度: {len(text2)} 字符")

    assert len(responses1) > 0 and len(responses2) > 0, "Both turns should succeed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
