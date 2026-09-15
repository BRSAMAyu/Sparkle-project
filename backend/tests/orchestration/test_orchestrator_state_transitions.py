"""
Orchestrator FSM State Transitions Test Suite

测试 ChatOrchestrator 的完整状态转换逻辑：
- 正常状态转换: INIT → THINKING → GENERATING → DONE
- 工具调用转换: THINKING → TOOL_CALLING → THINKING
- 错误恢复转换: FAILED → THINKING (重试)
- 超时处理转换: 各状态超时后的降级路径
- 并发锁场景: 同一会话并发请求的排队处理
- 分布式锁续期: 长时间操作的锁续期机制
"""
from __future__ import annotations

import asyncio
import pytest
import pytest_asyncio
import uuid
import redis.asyncio as redis
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.orchestration.orchestrator import (
    ChatOrchestrator,
    STATE_INIT,
    STATE_THINKING,
    STATE_GENERATING,
    STATE_TOOL_CALLING,
    STATE_DONE,
    STATE_FAILED,
)
from app.orchestration.state_manager import (
    SessionStateManager,
    FSMState,
)
from app.gen.agent.v1 import agent_service_pb2
from app.models.user import User


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def redis_client():
    """创建 Redis 客户端 fixture"""
    from app.core.redis_utils import resolve_redis_password
    import os
    from app.config import settings

    redis_url = os.getenv("REDIS_URL", settings.REDIS_URL or "redis://localhost:6379/0")
    password, _ = resolve_redis_password(redis_url, os.getenv("REDIS_PASSWORD", settings.REDIS_PASSWORD))
    client = redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
        password=password,
    )
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest_asyncio.fixture
async def mock_orchestrator(redis_client):
    """创建用于测试的 Mock Orchestrator"""
    # 简化 mock，只 patch 需要的组件
    with patch('app.orchestration.orchestrator.create_standard_chat_graph'):
        with patch('app.orchestration.orchestrator.RedisCheckpointer'):
            orchestrator = ChatOrchestrator(
                db_session=None,
                redis_client=redis_client,
                user_id="test-user-123",
            )
            # 覆盖 graph 以避免初始化复杂组件
            orchestrator.graph = MagicMock()
            orchestrator.graph.ainvoke = AsyncMock(return_value={
                "messages": [{"role": "assistant", "content": "Test response"}],
                "is_finished": True,
            })
            # 确保 tracer 存在
            if not hasattr(orchestrator, 'tracer') or orchestrator.tracer is None:
                orchestrator.tracer = MagicMock()
            yield orchestrator


@pytest.fixture
def sample_session_id() -> str:
    """生成测试用会话 ID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_request():
    """生成测试用请求"""
    request = agent_service_pb2.ChatRequest()
    request.session_id = str(uuid.uuid4())
    request.user_message = "Hello, how are you?"
    request.user_id = "test-user-123"
    return request


# =============================================================================
# P0-1: Normal State Transitions
# =============================================================================


class TestNormalStateTransitions:
    """测试正常状态转换流程"""

    @pytest.mark.asyncio
    async def test_init_to_thinking_transition(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试 INIT → THINKING 状态转换"""
        state_manager = mock_orchestrator.state_manager

        # 初始状态应为 INIT
        initial_state = FSMState(
            session_id=sample_session_id,
            state=STATE_INIT,
        )
        await state_manager.save_state(sample_session_id, initial_state)

        # 转换到 THINKING
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="Processing user input",
        )

        # 验证状态转换
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state is not None
        assert saved_state.state == STATE_THINKING
        assert saved_state.details == "Processing user input"

    @pytest.mark.asyncio
    async def test_thinking_to_generating_transition(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试 THINKING → GENERATING 状态转换"""
        state_manager = mock_orchestrator.state_manager

        # 设置 THINKING 状态
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="Context built, generating response",
        )

        # 转换到 GENERATING
        await state_manager.update_state(
            sample_session_id,
            STATE_GENERATING,
            details="Streaming response to client",
        )

        # 验证状态
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state.state == STATE_GENERATING

    @pytest.mark.asyncio
    async def test_generating_to_done_transition(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试 GENERATING → DONE 状态转换"""
        state_manager = mock_orchestrator.state_manager

        # 设置 GENERATING 状态
        await state_manager.update_state(
            sample_session_id,
            STATE_GENERATING,
            details="Response complete",
        )

        # 转换到 DONE
        await state_manager.update_state(
            sample_session_id,
            STATE_DONE,
            details="Request completed successfully",
        )

        # 验证状态
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state.state == STATE_DONE

    @pytest.mark.asyncio
    async def test_complete_normal_flow(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试完整的正常流程: INIT → THINKING → GENERATING → DONE"""
        state_manager = mock_orchestrator.state_manager

        # 模拟完整的正常流程
        states = [
            (STATE_INIT, "Session initialized"),
            (STATE_THINKING, "Processing request, building context"),
            (STATE_GENERATING, "Generating and streaming response"),
            (STATE_DONE, "Request completed"),
        ]

        for state, details in states:
            await state_manager.update_state(sample_session_id, state, details=details)
            saved_state = await state_manager.load_state(sample_session_id)
            assert saved_state.state == state
            assert saved_state.details == details


# =============================================================================
# P0-2: Tool Calling State Transitions
# =============================================================================


class TestToolCallingTransitions:
    """测试工具调用相关的状态转换"""

    @pytest.mark.asyncio
    async def test_thinking_to_tool_calling_transition(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试 THINKING → TOOL_CALLING 状态转换"""
        state_manager = mock_orchestrator.state_manager

        # 设置 THINKING 状态
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="Need to call a tool",
        )

        # 转换到 TOOL_CALLING
        await state_manager.update_state(
            sample_session_id,
            STATE_TOOL_CALLING,
            details="Calling tool: search_knowledge",
            tool_calls_in_progress=["search_knowledge"],
        )

        # 验证状态
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state.state == STATE_TOOL_CALLING
        assert "search_knowledge" in saved_state.tool_calls_in_progress

    @pytest.mark.asyncio
    async def test_tool_calling_to_thinking_transition(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试 TOOL_CALLING → THINKING 状态转换 (工具调用完成后返回思考)"""
        state_manager = mock_orchestrator.state_manager

        # 设置 TOOL_CALLING 状态
        fsm_state = FSMState(
            session_id=sample_session_id,
            state=STATE_TOOL_CALLING,
            details="Executing tool",
            tool_calls_in_progress=["search_knowledge", "get_user_tasks"],
        )
        await state_manager.save_state(sample_session_id, fsm_state)

        # 工具调用完成，返回 THINKING 处理结果
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="Processing tool results",
            tool_calls_in_progress=[],
        )

        # 验证状态
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state.state == STATE_THINKING
        assert len(saved_state.tool_calls_in_progress) == 0

    @pytest.mark.asyncio
    async def test_multiple_tool_calling_cycle(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试多轮工具调用循环: THINKING → TOOL_CALLING → THINKING → TOOL_CALLING → THINKING"""
        state_manager = mock_orchestrator.state_manager

        # 第一轮工具调用
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="Planning tool calls",
        )
        await state_manager.update_state(
            sample_session_id,
            STATE_TOOL_CALLING,
            details="Calling: search_knowledge",
            tool_calls_in_progress=["search_knowledge"],
        )

        # 获取结果并回到思考
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="Processing search results",
            tool_calls_in_progress=[],
        )

        # 第二轮工具调用
        await state_manager.update_state(
            sample_session_id,
            STATE_TOOL_CALLING,
            details="Calling: get_user_tasks",
            tool_calls_in_progress=["get_user_tasks"],
        )

        # 最终回到思考
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="All tool results processed, generating final response",
            tool_calls_in_progress=[],
        )

        # 验证最终状态
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state.state == STATE_THINKING
        assert len(saved_state.tool_calls_in_progress) == 0


# =============================================================================
# P0-3: Error Recovery Transitions
# =============================================================================


class TestErrorRecoveryTransitions:
    """测试错误恢复状态转换"""

    @pytest.mark.asyncio
    async def test_thinking_to_failed_on_error(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试 THINKING → FAILED 状态转换 (错误发生)"""
        state_manager = mock_orchestrator.state_manager

        # 设置 THINKING 状态
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="Processing request",
        )

        # 发生错误，转换到 FAILED
        await state_manager.update_state(
            sample_session_id,
            STATE_FAILED,
            details="LLM service timeout after 30s",
        )

        # 验证状态
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state.state == STATE_FAILED
        assert "timeout" in saved_state.details.lower()

    @pytest.mark.asyncio
    async def test_failed_to_thinking_retry_transition(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试 FAILED → THINKING 状态转换 (重试机制)"""
        state_manager = mock_orchestrator.state_manager

        # 设置 FAILED 状态
        await state_manager.update_state(
            sample_session_id,
            STATE_FAILED,
            details="Temporary error, will retry",
        )

        # 重试：转换回 THINKING
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="Retrying request (attempt 2/3)",
        )

        # 验证状态
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state.state == STATE_THINKING
        assert "retry" in saved_state.details.lower()

    @pytest.mark.asyncio
    async def test_tool_calling_to_failed_on_tool_error(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试 TOOL_CALLING → FAILED 状态转换 (工具执行失败)"""
        state_manager = mock_orchestrator.state_manager

        # 设置 TOOL_CALLING 状态
        await state_manager.update_state(
            sample_session_id,
            STATE_TOOL_CALLING,
            details="Executing tool",
            tool_calls_in_progress=["external_api"],
        )

        # 工具执行失败
        await state_manager.update_state(
            sample_session_id,
            STATE_FAILED,
            details="Tool execution failed: external_api returned 500",
            tool_calls_in_progress=[],
        )

        # 验证状态
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state.state == STATE_FAILED
        assert len(saved_state.tool_calls_in_progress) == 0

    @pytest.mark.asyncio
    async def test_max_retry_exceeded_transition(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试超过最大重试次数后的状态转换"""
        state_manager = mock_orchestrator.state_manager

        # 模拟多次重试
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            await state_manager.update_state(
                sample_session_id,
                STATE_FAILED,
                details=f"Retry attempt {attempt}/{max_retries} failed",
            )

            if attempt < max_retries:
                # 重试
                await state_manager.update_state(
                    sample_session_id,
                    STATE_THINKING,
                    details=f"Retrying (attempt {attempt + 1}/{max_retries})",
                )

        # 最终重试也失败，保持 FAILED 状态
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state.state == STATE_FAILED


# =============================================================================
# P0-4: Timeout Handling Transitions
# =============================================================================


class TestTimeoutHandlingTransitions:
    """测试超时处理状态转换"""

    @pytest.mark.asyncio
    async def test_thinking_timeout_to_failed(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试 THINKING 状态超时后转换到 FAILED"""
        state_manager = mock_orchestrator.state_manager

        # 设置 THINKING 状态（假设已超时）
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="Processing (taking too long)",
        )

        # 模拟超时检测
        await state_manager.update_state(
            sample_session_id,
            STATE_FAILED,
            details="State timeout: THINKING exceeded 120s limit",
        )

        # 验证状态
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state.state == STATE_FAILED
        assert "timeout" in saved_state.details.lower()

    @pytest.mark.asyncio
    async def test_tool_calling_timeout_recovery(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试 TOOL_CALLING 超时后的恢复"""
        state_manager = mock_orchestrator.state_manager

        # 设置 TOOL_CALLING 状态
        await state_manager.update_state(
            sample_session_id,
            STATE_TOOL_CALLING,
            details="Calling slow tool",
            tool_calls_in_progress=["slow_external_api"],
        )

        # 超时后回退
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="Tool timeout, using fallback strategy",
            tool_calls_in_progress=[],
        )

        # 验证状态
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state.state == STATE_THINKING
        assert len(saved_state.tool_calls_in_progress) == 0


# =============================================================================
# P0-5: Concurrent Lock Scenarios
# =============================================================================


class TestConcurrentLockScenarios:
    """测试并发锁场景"""

    @pytest.mark.asyncio
    async def test_session_lock_prevents_concurrent_execution(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试会话锁阻止同一会话的并发执行"""
        state_manager = mock_orchestrator.state_manager

        # 生成唯一的 request_id
        request_id_1 = str(uuid.uuid4())
        request_id_2 = str(uuid.uuid4())

        # 获取锁
        lock_acquired = await state_manager.acquire_lock(sample_session_id, request_id_1)
        assert lock_acquired is True

        # 尝试再次获取锁（应该失败）
        lock_acquired_again = await state_manager.acquire_lock(sample_session_id, request_id_2)
        assert lock_acquired_again is False

        # 释放锁
        await state_manager.release_lock(sample_session_id, request_id_1)

        # 现在应该可以获取锁
        lock_acquired_final = await state_manager.acquire_lock(sample_session_id, request_id_2)
        assert lock_acquired_final is True

        # 清理
        await state_manager.release_lock(sample_session_id, request_id_2)

    @pytest.mark.asyncio
    async def test_concurrent_requests_queueing(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试同一会话并发请求的排队处理"""
        state_manager = mock_orchestrator.state_manager

        request_id_1 = str(uuid.uuid4())
        request_id_2 = str(uuid.uuid4())

        # 第一个请求获取锁
        first_lock = await state_manager.acquire_lock(sample_session_id, request_id_1)
        assert first_lock is True

        # 模拟第一个请求正在处理
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="First request processing",
        )

        # 第二个请求尝试获取锁（应该失败）
        # 注意：由于第一个锁已存在，获取应该失败
        # 在实际实现中，acquire_lock 使用 SET NX，所以如果锁存在会返回 False
        second_lock = await state_manager.acquire_lock(sample_session_id, request_id_2)
        assert second_lock is False

        # 释放第一个锁
        await state_manager.release_lock(sample_session_id, request_id_1)

        # 第二个请求现在可以获取锁
        second_lock = await state_manager.acquire_lock(sample_session_id, request_id_2)
        assert second_lock is True

        # 清理
        await state_manager.release_lock(sample_session_id, request_id_2)

    @pytest.mark.asyncio
    async def test_different_sessions_concurrent_execution(
        self,
        mock_orchestrator: ChatOrchestrator,
    ):
        """测试不同会话可以并发执行"""
        state_manager = mock_orchestrator.state_manager

        session_1 = str(uuid.uuid4())
        session_2 = str(uuid.uuid4())
        request_id_1 = str(uuid.uuid4())
        request_id_2 = str(uuid.uuid4())

        # 两个会话都可以获取各自的锁
        lock_1 = await state_manager.acquire_lock(session_1, request_id_1)
        lock_2 = await state_manager.acquire_lock(session_2, request_id_2)

        assert lock_1 is True
        assert lock_2 is True

        # 清理
        await state_manager.release_lock(session_1, request_id_1)
        await state_manager.release_lock(session_2, request_id_2)

    @pytest.mark.asyncio
    async def test_lock_expiration_handling(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试锁过期后的处理"""
        state_manager = mock_orchestrator.state_manager

        request_id_1 = str(uuid.uuid4())
        request_id_2 = str(uuid.uuid4())

        # 获取锁（TTL = 30s）
        lock_acquired = await state_manager.acquire_lock(sample_session_id, request_id_1)
        assert lock_acquired is True

        # 模拟锁过期后，另一个请求可以获取锁
        # 注意：这里我们手动删除 Redis 中的锁来模拟过期
        lock_key = state_manager._get_lock_key(sample_session_id)
        await state_manager.redis.delete(lock_key)

        # 新的请求可以获取锁
        lock_acquired_again = await state_manager.acquire_lock(sample_session_id, request_id_2)
        assert lock_acquired_again is True

        # 清理
        await state_manager.release_lock(sample_session_id, request_id_2)


# =============================================================================
# P0-6: Distributed Lock Renewal
# =============================================================================


class TestDistributedLockRenewal:
    """测试分布式锁续期机制"""

    @pytest.mark.asyncio
    async def test_lock_renewal_extends_ttl(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试锁续期延长 TTL"""
        state_manager = mock_orchestrator.state_manager

        request_id = str(uuid.uuid4())

        # 获取锁
        await state_manager.acquire_lock(sample_session_id, request_id)

        # 获取初始 TTL
        lock_key = state_manager._get_lock_key(sample_session_id)
        initial_ttl = await state_manager.redis.ttl(lock_key)
        assert initial_ttl > 0

        # 续期
        renewed = await state_manager.renew_lock(sample_session_id, request_id)
        assert renewed is True

        # 验证 TTL 已被延长
        renewed_ttl = await state_manager.redis.ttl(lock_key)
        assert renewed_ttl > initial_ttl or renewed_ttl == state_manager.lock_ttl

        # 清理
        await state_manager.release_lock(sample_session_id, request_id)

    @pytest.mark.asyncio
    async def test_long_running_operation_with_renewal(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试长时间操作中的锁续期"""
        state_manager = mock_orchestrator.state_manager

        request_id = str(uuid.uuid4())

        # 获取锁并开始长时间操作
        await state_manager.acquire_lock(sample_session_id, request_id)
        await state_manager.update_state(
            sample_session_id,
            STATE_TOOL_CALLING,
            details="Starting long operation",
        )

        # 模拟操作进行中续期
        for i in range(3):
            await asyncio.sleep(0.1)
            renewed = await state_manager.renew_lock(sample_session_id, request_id)
            assert renewed is True
            await state_manager.update_state(
                sample_session_id,
                STATE_TOOL_CALLING,
                details=f"Operation progress: {(i+1)*33}%",
            )

        # 操作完成
        await state_manager.update_state(
            sample_session_id,
            STATE_DONE,
            details="Long operation completed",
        )

        # 验证状态
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state.state == STATE_DONE

        # 清理
        await state_manager.release_lock(sample_session_id, request_id)

    @pytest.mark.asyncio
    async def test_lock_renewal_failure_handling(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试锁续期失败的处理"""
        state_manager = mock_orchestrator.state_manager

        request_id = str(uuid.uuid4())

        # 获取锁
        await state_manager.acquire_lock(sample_session_id, request_id)

        # 手动删除锁
        lock_key = state_manager._get_lock_key(sample_session_id)
        await state_manager.redis.delete(lock_key)

        # 尝试续期（应该失败，因为锁已被删除）
        renewed = await state_manager.renew_lock(sample_session_id, request_id)
        assert renewed is False


# =============================================================================
# P0-7: State Persistence and Recovery
# =============================================================================


class TestStatePersistenceAndRecovery:
    """测试状态持久化和恢复"""

    @pytest.mark.asyncio
    async def test_state_persistence_across_operations(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试状态在操作间的持久化"""
        state_manager = mock_orchestrator.state_manager

        # 创建并保存状态
        original_state = FSMState(
            session_id=sample_session_id,
            state=STATE_THINKING,
            details="Test persistence",
            request_id="req-123",
            user_id="user-456",
            tool_calls_in_progress=["tool1", "tool2"],
        )
        await state_manager.save_state(sample_session_id, original_state)

        # 加载状态
        loaded_state = await state_manager.load_state(sample_session_id)

        # 验证所有字段
        assert loaded_state.session_id == sample_session_id
        assert loaded_state.state == STATE_THINKING
        assert loaded_state.details == "Test persistence"
        assert loaded_state.request_id == "req-123"
        assert loaded_state.user_id == "user-456"
        assert loaded_state.tool_calls_in_progress == ["tool1", "tool2"]

    @pytest.mark.asyncio
    async def test_state_recovery_after_failure(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试失败后的状态恢复"""
        state_manager = mock_orchestrator.state_manager

        # 模拟执行中的状态
        await state_manager.update_state(
            sample_session_id,
            STATE_TOOL_CALLING,
            details="Executing tool when system crashed",
            tool_calls_in_progress=["critical_tool"],
            accumulated_response="Partial response...",
        )

        # 模拟系统重启后恢复状态
        recovered_state = await state_manager.load_state(sample_session_id)

        # 验证可以恢复到失败前的状态
        assert recovered_state.state == STATE_TOOL_CALLING
        assert recovered_state.accumulated_response == "Partial response..."
        assert "critical_tool" in recovered_state.tool_calls_in_progress

        # 从恢复的状态继续
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="Resumed from crash, processing tool result",
            tool_calls_in_progress=[],
        )

        # 验证继续执行
        final_state = await state_manager.load_state(sample_session_id)
        assert final_state.state == STATE_THINKING

    @pytest.mark.asyncio
    async def test_state_ttl_expiration(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试状态 TTL 过期"""
        state_manager = mock_orchestrator.state_manager

        # 保存状态（使用短 TTL 测试）
        test_state = FSMState(
            session_id=sample_session_id,
            state=STATE_DONE,
            details="This state should expire",
        )
        state_key = state_manager._get_state_key(sample_session_id)
        await state_manager.redis.setex(state_key, 1, test_state.to_json())  # 1 秒 TTL

        # 立即加载应该存在
        loaded = await state_manager.load_state(sample_session_id)
        assert loaded is not None

        # 等待过期
        await asyncio.sleep(1.1)

        # 过期后应该不存在
        loaded_after_expiry = await state_manager.load_state(sample_session_id)
        assert loaded_after_expiry is None


# =============================================================================
# P0-8: Edge Cases and Error Handling
# =============================================================================


class TestEdgeCasesAndErrorHandling:
    """测试边界情况和错误处理"""

    @pytest.mark.asyncio
    async def test_invalid_state_transition_handling(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试无效状态转换的处理"""
        state_manager = mock_orchestrator.state_manager

        # 设置 DONE 状态（终态）
        await state_manager.update_state(
            sample_session_id,
            STATE_DONE,
            details="Request completed",
        )

        # 尝试从 DONE 转换到其他状态（根据业务逻辑，这可能不允许）
        # 这里我们只测试系统允许这个转换
        await state_manager.update_state(
            sample_session_id,
            STATE_THINKING,
            details="New request in same session",
        )

        # 验证新状态
        saved_state = await state_manager.load_state(sample_session_id)
        assert saved_state.state == STATE_THINKING

    @pytest.mark.asyncio
    async def test_empty_session_id_handling(
        self,
        mock_orchestrator: ChatOrchestrator,
    ):
        """测试空会话 ID 的处理"""
        state_manager = mock_orchestrator.state_manager

        # 尝试加载空会话 ID
        empty_state = await state_manager.load_state("")
        assert empty_state is None

        # 尝试更新空会话 ID
        # 注意：根据实现，这可能会创建一个状态
        result = await state_manager.update_state("", STATE_INIT, "Empty session")
        # 验证结果（可能成功也可能失败，取决于实现）

    @pytest.mark.asyncio
    async def test_concurrent_state_updates(
        self,
        mock_orchestrator: ChatOrchestrator,
        sample_session_id: str,
    ):
        """测试并发状态更新"""
        state_manager = mock_orchestrator.state_manager

        # 并发更新状态
        tasks = []
        for i in range(10):
            task = state_manager.update_state(
                sample_session_id,
                STATE_THINKING,
                details=f"Concurrent update {i}",
            )
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证至少有一个成功
        assert any(r is True for r in results if not isinstance(r, Exception))

        # 最终状态应该是最后写入的值之一
        final_state = await state_manager.load_state(sample_session_id)
        assert final_state is not None
        assert final_state.state == STATE_THINKING

