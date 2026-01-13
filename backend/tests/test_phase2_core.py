"""
Phase 2 核心组件单元测试
测试 Redis 状态管理、工具注册、验证器等核心功能
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from uuid import uuid4
import json

# 测试状态管理器
@pytest.mark.asyncio
async def test_state_manager_basic():
    """测试状态管理器基本功能"""
    from app.orchestration.state_manager import SessionStateManager, FSMState
    
    # Mock Redis
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.get = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.eval = AsyncMock(return_value=1)
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.ttl = AsyncMock(return_value=3600)
    
    manager = SessionStateManager(redis_mock)
    
    # 测试保存状态
    state = FSMState(
        session_id="test-session",
        state="INIT",
        details="Test details",
        request_id="req-123",
        user_id="user-456"
    )
    
    await manager.save_state("test-session", state)
    redis_mock.setex.assert_called_once()
    
    # 测试加载状态
    redis_mock.get.return_value = state.to_json()
    loaded = await manager.load_state("test-session")
    assert loaded is not None
    assert loaded.state == "INIT"
    assert loaded.session_id == "test-session"
    
    print("✅ State Manager test passed")


@pytest.mark.asyncio
async def test_dynamic_tool_registry():
    """测试动态工具注册表"""
    from app.orchestration.dynamic_tool_registry import DynamicToolRegistry
    from app.tools.base import BaseTool, ToolCategory
    from pydantic import BaseModel
    
    # 创建测试工具
    class TestParams(BaseModel):
        name: str
        value: int
    
    class TestTool(BaseTool):
        name = "test_tool"
        description = "A test tool"
        category = ToolCategory.TASK
        parameters_schema = TestParams
        
        async def execute(self, params, user_id, db_session):
            from app.tools.base import ToolResult
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"result": f"Executed with {params.name}"}
            )
    
    registry = DynamicToolRegistry()
    
    # 注册工具
    tool = TestTool()
    registry.register_tool(tool)
    
    # 验证注册
    assert registry.get_tool("test_tool") is not None
    assert len(registry.get_all_tools()) == 1
    
    # 验证 OpenAI schema
    schema = registry.get_openai_tools_schema()
    assert len(schema) == 1
    assert schema[0]["function"]["name"] == "test_tool"
    
    print("✅ Dynamic Tool Registry test passed")


@pytest.mark.asyncio
async def test_request_validator():
    """测试请求验证器"""
    from app.orchestration.validator import RequestValidator
    from app.gen.agent.v1 import agent_service_pb2
    
    validator = RequestValidator()
    
    # 创建有效请求
    request = agent_service_pb2.ChatRequest(
        user_id="user-123",
        session_id="session-456",
        request_id="req-789",
        message="Hello, world!"
    )
    
    result = await validator.validate_chat_request(request)
    assert result.is_valid is True
    
    # 测试无效用户 ID
    request_invalid = agent_service_pb2.ChatRequest(
        user_id="",  # 空用户 ID
        session_id="session-456",
        request_id="req-789",
        message="Hello"
    )
    
    result = await validator.validate_chat_request(request_invalid)
    assert result.is_valid is False
    assert "user_id is required" in result.error_message
    
    # 测试消息长度限制
    long_message = "a" * 3000  # 超过 2000 限制
    request_long = agent_service_pb2.ChatRequest(
        user_id="user-123",
        session_id="session-456",
        request_id="req-789",
        message=long_message
    )
    
    result = await validator.validate_chat_request(request_long)
    assert result.is_valid is False
    
    print("✅ Request Validator test passed")


@pytest.mark.asyncio
async def test_user_service():
    """测试用户服务"""
    from app.services.user_service import UserService
    from sqlalchemy.ext.asyncio import AsyncSession
    from unittest.mock import MagicMock
    
    # Mock DB session
    db_mock = MagicMock(spec=AsyncSession)
    db_mock.execute = AsyncMock()
    
    # Mock user query result
    mock_user = MagicMock()
    mock_user.id = uuid4()
    mock_user.username = "testuser"
    mock_user.nickname = "Test User"
    mock_user.email = "test@example.com"
    mock_user.depth_preference = 0.6
    mock_user.curiosity_preference = 0.8
    mock_user.flame_level = 3
    mock_user.flame_brightness = 0.7
    mock_user.is_active = True
    mock_user.last_login_at = None
    mock_user.registration_source = "email"
    
    # Mock the execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    db_mock.execute.return_value = mock_result
    
    user_service = UserService(db_mock)
    user_service._get_push_preference = AsyncMock(return_value=None)
    
    # Test get_context
    user_id = uuid4()
    context = await user_service.get_context(user_id)
    
    assert context is not None
    assert context.user_id == str(user_id)
    assert context.nickname == "Test User"
    assert context.is_pro is True  # flame_level >= 3
    
    print("✅ User Service test passed")


@pytest.mark.asyncio
async def test_response_composer():
    """测试响应组装器"""
    from app.orchestration.composer import ResponseComposer
    from app.tools.base import ToolResult
    
    composer = ResponseComposer()
    
    # 测试纯文本响应
    result = composer.compose_response(
        llm_text="Hello, this is a response",
        tool_results=[],
        requires_confirmation=False
    )
    
    assert result["message"] == "Hello, this is a response"
    assert result["has_errors"] is False
    assert len(result["widgets"]) == 0
    
    # 测试带工具结果的响应
    tool_results = [
        ToolResult(
            success=True,
            tool_name="create_task",
            data={"task_id": "123"},
            widget_type="task_card",
            widget_data={"title": "New Task", "status": "pending"}
        )
    ]
    
    result = composer.compose_response(
        llm_text="Task created successfully",
        tool_results=tool_results,
        requires_confirmation=False
    )
    
    assert result["has_errors"] is False
    assert len(result["widgets"]) == 1
    assert result["widgets"][0]["type"] == "task_card"
    
    # 测试带错误的响应
    error_tool_results = [
        ToolResult(
            success=False,
            tool_name="failing_tool",
            error_message="Something went wrong",
            suggestion="Try again later"
        )
    ]
    
    result = composer.compose_response(
        llm_text="An error occurred",
        tool_results=error_tool_results,
        requires_confirmation=False
    )
    
    assert result["has_errors"] is True
    assert len(result["errors"]) == 1
    assert result["errors"][0]["tool"] == "failing_tool"
    
    print("✅ Response Composer test passed")


@pytest.mark.asyncio
async def test_orchestrator_integration():
    """测试 Orchestrator 集成"""
    from app.orchestration.orchestrator import ChatOrchestrator
    from app.gen.agent.v1 import agent_service_pb2
    from unittest.mock import MagicMock, AsyncMock
    
    # Mock Redis
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)  # No cache
    redis_mock.set = AsyncMock(return_value=True)  # Lock acquired
    redis_mock.eval = AsyncMock(return_value=1)  # Lock released
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.ttl = AsyncMock(return_value=3600)
    
    # Mock DB
    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    
    # Create orchestrator
    orchestrator = ChatOrchestrator(db_session=db_mock, redis_client=redis_mock)
    
    # Verify components are initialized
    assert orchestrator.state_manager is not None
    assert orchestrator.validator is not None
    assert orchestrator.response_composer is not None
    
    # Create test request
    request = agent_service_pb2.ChatRequest(
        user_id="user-123",
        session_id="session-456",
        request_id="req-789",
        message="Test message"
    )
    
    # Mock the LLM service to avoid actual calls
    from app.services.llm_service import llm_service, StreamChunk
    original_chat_stream = llm_service.chat_stream_with_tools
    
    async def mock_chat_stream(*args, **kwargs):
        # Yield a text chunk
        yield StreamChunk(type="text", content="Test response")
    
    llm_service.chat_stream_with_tools = mock_chat_stream
    
    try:
        # Process stream
        responses = []
        async for response in orchestrator.process_stream(request, db_session=db_mock):
            responses.append(response)
        
        # Verify we got responses
        assert len(responses) > 0
        
        # Verify state transitions were logged
        # (In real implementation, we'd check Redis calls)
        
        print("✅ Orchestrator Integration test passed")
        
    finally:
        # Restore original
        llm_service.chat_stream_with_tools = original_chat_stream


# Run all tests
if __name__ == "__main__":
    print("\n" + "="*60)
    print("Running Phase 2 Core Component Tests")
    print("="*60 + "\n")
    
    asyncio.run(test_state_manager_basic())
    asyncio.run(test_dynamic_tool_registry())
    asyncio.run(test_request_validator())
    asyncio.run(test_user_service())
    asyncio.run(test_response_composer())
    asyncio.run(test_orchestrator_integration())
    
    print("\n" + "="*60)
    print("All Phase 2 Tests Passed! ✅")
    print("="*60 + "\n")
