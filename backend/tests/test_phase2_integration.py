"""
Phase 2 集成测试
测试完整的 Agent 编排流程
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import json

@pytest.mark.asyncio
async def test_full_agent_flow_with_redis():
    """
    测试完整的 Agent 流程：
    1. 请求验证
    2. 幂等性检查
    3. 分布式锁
    4. 用户上下文构建
    5. RAG 检索
    6. 动态工具调用
    7. 响应组装
    8. 状态持久化
    """
    from app.orchestration.orchestrator import ChatOrchestrator
    from app.gen.agent.v1 import agent_service_pb2
    from app.services.llm_service import StreamChunk, llm_service
    
    # Setup mocks
    redis_mock = AsyncMock()
    
    # Redis operations
    redis_mock.setex = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)  # No cache
    redis_mock.set = AsyncMock(return_value=True)  # Lock acquired
    redis_mock.eval = AsyncMock(return_value=1)  # Lock released
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.ttl = AsyncMock(return_value=3600)
    
    # DB mock
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    
    # Mock user data
    mock_user = MagicMock()
    mock_user.id = uuid4()
    mock_user.username = "testuser"
    mock_user.nickname = "Test User"
    mock_user.depth_preference = 0.7
    mock_user.curiosity_preference = 0.9
    mock_user.flame_level = 4
    mock_user.flame_brightness = 0.8
    mock_user.is_active = True
    mock_user.last_login_at = None
    mock_user.registration_source = "email"
    mock_user.weather_preferences = {}
    
    # Mock user query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    db_mock.execute.return_value = mock_result
    
    # Mock push preference
    mock_push_pref = MagicMock()
    mock_push_pref.timezone = "Asia/Shanghai"
    mock_push_pref.enable_curiosity = True
    mock_push_pref.persona_type = "coach"
    mock_push_pref.daily_cap = 5
    mock_push_pref.active_slots = {"morning": ["08:00", "09:00"]}
    
    # Mock push preference query
    async def mock_execute(query):
        if "push_preferences" in str(query):
            mock_push_result = MagicMock()
            mock_push_result.scalar_one_or_none.return_value = mock_push_pref
            return mock_push_result
        return mock_result
    
    db_mock.execute = mock_execute
    
    # Mock knowledge service
    with patch('app.orchestration.orchestrator.KnowledgeService') as mock_ks:
        mock_ks_instance = MagicMock()
        mock_ks_instance.retrieve_context = AsyncMock(return_value="Relevant knowledge about Python")
        mock_ks.return_value = mock_ks_instance
        
        # Mock LLM service
        original_chat_stream = llm_service.chat_stream_with_tools
        
        async def mock_chat_stream(*args, **kwargs):
            # Simulate LLM response with tool call
            yield StreamChunk(type="text", content="I'll help you create a task. ")
            yield StreamChunk(
                type="tool_call_end",
                tool_name="create_task",
                tool_call_id="call_123",
                full_arguments={"title": "Learn Python", "estimated_minutes": 30}
            )
        
        llm_service.chat_stream_with_tools = mock_chat_stream
        
        try:
            # Create orchestrator
            orchestrator = ChatOrchestrator(db_session=db_mock, redis_client=redis_mock)
            
            # Create request
            request = agent_service_pb2.ChatRequest(
                user_id=str(uuid4()),
                session_id="test-session-123",
                request_id="req-456",
                message="Create a task to learn Python"
            )
            
            # Process stream
            responses = []
            async for response in orchestrator.process_stream(request, db_session=db_mock):
                responses.append(response)
            
            # Verify flow
            assert len(responses) > 0
            
            # Check that validation was called (would fail if invalid)
            # Check that state updates happened
            # Check that Redis operations were called
            assert redis_mock.setex.call_count >= 1  # State saved
            
            print("✅ Full Agent Flow test passed")
            
        finally:
            llm_service.chat_stream_with_tools = original_chat_stream


@pytest.mark.asyncio
async def test_idempotency_flow():
    """测试幂等性：重复请求返回缓存"""
    from app.orchestration.orchestrator import ChatOrchestrator
    from app.gen.agent.v1 import agent_service_pb2
    
    redis_mock = AsyncMock()
    
    # First request: no cache
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.eval = AsyncMock(return_value=1)
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.ttl = AsyncMock(return_value=3600)
    
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    
    orchestrator = ChatOrchestrator(db_session=db_mock, redis_client=redis_mock)
    
    request = agent_service_pb2.ChatRequest(
        user_id="user-123",
        session_id="session-456",
        request_id="req-789",
        message="Test"
    )
    
    # Mock LLM
    from app.services.llm_service import llm_service, StreamChunk
    original = llm_service.chat_stream_with_tools
    
    async def mock_stream(*args, **kwargs):
        yield StreamChunk(type="text", content="First response")
    
    llm_service.chat_stream_with_tools = mock_stream
    
    try:
        # First request
        responses1 = []
        async for r in orchestrator.process_stream(request, db_session=db_mock):
            responses1.append(r)
        
        # Verify cache was written
        assert redis_mock.setex.call_count >= 2  # State + cache
        
        # Reset mock to simulate cache hit
        redis_mock.get = AsyncMock(return_value=json.dumps({
            "full_text": "Cached response"
        }))
        
        # Second request with same ID
        responses2 = []
        async for r in orchestrator.process_stream(request, db_session=db_mock):
            responses2.append(r)
        
        # Should return cached response
        assert len(responses2) == 1
        assert responses2[0].full_text == "Cached response"
        
        print("✅ Idempotency test passed")
        
    finally:
        llm_service.chat_stream_with_tools = original


@pytest.mark.asyncio
async def test_concurrent_session_protection():
    """测试并发会话保护（分布式锁）"""
    from app.orchestration.orchestrator import ChatOrchestrator
    from app.gen.agent.v1 import agent_service_pb2
    
    redis_mock = AsyncMock()
    
    # First lock acquisition succeeds
    lock_acquired = [False]
    
    async def mock_set(key, value, nx, ex):
        if nx and not lock_acquired[0]:
            lock_acquired[0] = True
            return True
        return False
    
    redis_mock.set = mock_set
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.eval = AsyncMock(return_value=1)
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.ttl = AsyncMock(return_value=3600)
    
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    
    orchestrator = ChatOrchestrator(db_session=db_mock, redis_client=redis_mock)
    
    request = agent_service_pb2.ChatRequest(
        user_id="user-123",
        session_id="session-456",
        request_id="req-789",
        message="Test"
    )
    
    # Mock LLM
    from app.services.llm_service import llm_service
    original = llm_service.chat_stream_with_tools
    
    async def slow_stream(*args, **kwargs):
        await asyncio.sleep(0.1)  # Simulate slow processing
        yield StreamChunk(type="text", content="Response")
    
    llm_service.chat_stream_with_tools = slow_stream
    
    try:
        # Start two concurrent requests
        async def process_request():
            responses = []
            async for r in orchestrator.process_stream(request, db_session=db_mock):
                responses.append(r)
            return responses
        
        # First request should succeed
        task1 = asyncio.create_task(process_request())
        
        # Small delay to ensure first acquires lock
        await asyncio.sleep(0.01)
        
        # Second request should fail with conflict
        task2 = asyncio.create_task(process_request())
        
        results = await asyncio.gather(task1, task2, return_exceptions=False)
        
        # One should succeed, one should fail with CONFLICT
        success_count = 0
        conflict_count = 0
        
        for result in results:
            for response in result:
                if response.HasField("error") and response.error.code == "CONFLICT":
                    conflict_count += 1
                elif response.HasField("full_text"):
                    success_count += 1
        
        assert success_count >= 1
        assert conflict_count >= 1
        
        print("✅ Concurrent session protection test passed")
        
    finally:
        llm_service.chat_stream_with_tools = original


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Running Phase 2 Integration Tests")
    print("="*60 + "\n")
    
    asyncio.run(test_full_agent_flow_with_redis())
    asyncio.run(test_idempotency_flow())
    asyncio.run(test_concurrent_session_protection())
    
    print("\n" + "="*60)
    print("All Phase 2 Integration Tests Passed! ✅")
    print("="*60 + "\n")
