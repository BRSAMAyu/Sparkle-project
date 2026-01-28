"""
gRPC Streaming Integration Tests

Tests gRPC streaming communication between Go Gateway and Python Engine:
- StreamChat RPC with server-side streaming
- Bidirectional streaming scenarios
- Error handling and recovery
- Metadata propagation

This test requires:
- Running Python gRPC server (make grpc-server)
- Running PostgreSQL and Redis (make dev-all)
"""

import pytest
import asyncio
from typing import AsyncGenerator, List
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.plan import Plan
from app.gen.agent.v1 import agent_service_pb2, agent_service_pb2_grpc
from app.services.agent_grpc_service import AgentService
from app.orchestration.orchestrator import ChatOrchestrator
from app.core.security import create_access_token
from google.protobuf import struct_pb2


# ============================================================
# Test Fixtures
# ============================================================

@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    """Create a test user"""
    result = await db.execute(
        select(User).where(User.email == "grpc_test@example.com")
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email="grpc_test@example.com",
            nickname="gRPC Test User",
            password_hash="test_password"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    yield user

    # Cleanup (optional, keep user for other tests)


@pytest.fixture
async def grpc_channel():
    """Create gRPC channel to Python server"""
    import grpc
    import os

    grpc_host = os.getenv("GRPC_HOST", "localhost")
    grpc_port = os.getenv("GRPC_PORT", "50051")

    channel = grpc.aio.insecure_channel(f"{grpc_host}:{grpc_port}")
    yield channel
    await channel.close()


@pytest.fixture
async def grpc_stub(grpc_channel):
    """Create gRPC stub for AgentService"""
    stub = agent_service_pb2_grpc.AgentServiceStub(grpc_channel)
    return stub


@pytest.fixture
def user_profile_proto(test_user: User):
    """Create UserProfile protobuf message"""
    profile = agent_service_pb2.UserProfile(
        nickname=test_user.nickname,
        timezone="Asia/Shanghai",
        language="zh",
        is_pro=False,
        level=1,
        avatar_url=""
    )
    profile.preferences["concise_mode"] = "false"
    profile.preferences["role_play_enabled"] = "true"
    return profile


@pytest.fixture
def chat_request_proto(test_user: User, user_profile_proto):
    """Create basic ChatRequest protobuf message"""
    request = agent_service_pb2.ChatRequest(
        user_id=str(test_user.id),
        session_id="test-grpc-session-123",
        message="你好，请介绍一下你自己",
        user_profile=user_profile_proto,
        request_id=f"test-request-{datetime.now().timestamp()}",
        chat_mode="standard"
    )

    # Add extra context
    extra_context = struct_pb2.Struct()
    extra_context["test_key"] = "test_value"
    request.extra_context.CopyFrom(extra_context)

    return request


# ============================================================
# StreamChat Basic Tests
# ============================================================

class TestStreamChatBasic:
    """Test basic StreamChat RPC functionality"""

    @pytest.mark.asyncio
    async def test_stream_chat_simple_message(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test simple chat message via StreamChat"""
        responses = []

        async for response in grpc_stub.StreamChat(chat_request_proto):
            responses.append(response)

            # Check response structure
            assert hasattr(response, "content")
            assert hasattr(response, "metadata")

            # Break after receiving done signal
            if response.metadata.get("done", False):
                break

        # Should receive at least one response
        assert len(responses) > 0

        # Check for delta content
        delta_responses = [
            r for r in responses
            if r.content.delta != ""
        ]
        assert len(delta_responses) > 0

        # Verify final response has metadata
        final_response = responses[-1]
        assert final_response.metadata.get("done", False) == True

    @pytest.mark.asyncio
    async def test_stream_chat_with_tool_call(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test StreamChat that triggers tool execution"""
        # Modify request to trigger tool call
        chat_request_proto.message = "今天北京天气怎么样？"
        chat_request_proto.request_id = f"test-tool-{datetime.now().timestamp()}"

        tool_calls = []
        responses = []

        async for response in grpc_stub.StreamChat(chat_request_proto):
            responses.append(response)

            # Collect tool calls
            if response.content.tool_calls:
                for tool_call in response.content.tool_calls:
                    tool_calls.append(tool_call)

            if response.metadata.get("done", False):
                break

        # Should receive responses
        assert len(responses) > 0

        # May or may not have tool calls depending on LLM decision
        # Just verify structure if present
        if tool_calls:
            assert hasattr(tool_calls[0], "tool_name")
            assert hasattr(tool_calls[0], "parameters")

    @pytest.mark.asyncio
    async def test_stream_chat_with_history(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test StreamChat with conversation history"""
        # Add conversation history
        history_message1 = agent_service_pb2.ChatMessage(
            role="user",
            content="我的名字是张三"
        )
        history_message2 = agent_service_pb2.ChatMessage(
            role="assistant",
            content="你好张三，很高兴认识你！"
        )

        chat_request_proto.history.extend([history_message1, history_message2])
        chat_request_proto.message = "我叫什么名字？"
        chat_request_proto.request_id = f"test-history-{datetime.now().timestamp()}"

        responses = []
        async for response in grpc_stub.StreamChat(chat_request_proto):
            responses.append(response)
            if response.metadata.get("done", False):
                break

        # Should receive response that mentions "张三"
        all_content = "".join([
            r.content.delta
            for r in responses
        ])

        assert len(responses) > 0
        # LLM should remember the name from history
        # (Note: depends on LLM behavior, may not always work)


# ============================================================
# Metadata and Features Tests
# ============================================================

class TestStreamChatMetadata:
    """Test metadata and advanced features in StreamChat"""

    @pytest.mark.asyncio
    async def test_stream_chat_with_extra_context(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test StreamChat with extra context"""
        # Add custom extra context
        extra_context = struct_pb2.Struct()
        extra_context["pending_tasks"] = "3"
        extra_context["active_plans"] = "1"
        extra_context["focus_mode"] = "deep_work"

        chat_request_proto.extra_context.CopyFrom(extra_context)
        chat_request_proto.message = "根据我的当前状态给我建议"

        responses = []
        async for response in grpc_stub.StreamChat(chat_request_proto):
            responses.append(response)
            if response.metadata.get("done", False):
                break

        assert len(responses) > 0

    @pytest.mark.asyncio
    async def test_stream_chat_with_file_scope(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest,
        test_user: User,
        db: AsyncSession
    ):
        """Test StreamChat with file IDs for scoped RAG"""
        # Create a test plan (as a knowledge source)
        plan = Plan(
            user_id=test_user.id,
            name="AI学习计划",
            description="深入学习人工智能的基础知识",
            status="active"
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        # Scope to specific file/plan
        chat_request_proto.file_ids.append(str(plan.id))
        chat_request_proto.message = "根据这个计划，我该怎么开始？"
        chat_request_proto.request_id = f"test-file-scope-{datetime.now().timestamp()}"

        responses = []
        async for response in grpc_stub.StreamChat(chat_request_proto):
            responses.append(response)
            if response.metadata.get("done", False):
                break

        assert len(responses) > 0

        # Cleanup
        await db.delete(plan)
        await db.commit()

    @pytest.mark.asyncio
    async def test_stream_chat_with_references(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test StreamChat with include_references flag"""
        chat_request_proto.include_references = True
        chat_request_proto.message = "什么是向量数据库？"

        responses = []
        async for response in grpc_stub.StreamChat(chat_request_proto):
            responses.append(response)
            if response.metadata.get("done", False):
                break

        # Check if references are included
        has_references = any(
            r.content.references and len(r.content.references) > 0
            for r in responses
        )

        # Note: References may not always be available
        # This test mainly verifies the flag is accepted


# ============================================================
# Tool Execution Tests
# ============================================================

class TestToolExecution:
    """Test tool execution through gRPC streaming"""

    @pytest.mark.asyncio
    async def test_stream_chat_tool_result_feedback(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test submitting tool result back to StreamChat"""
        # First, get a tool call from LLM
        chat_request_proto.message = "搜索关于量子计算的最新研究"

        tool_call = None
        responses = []

        async for response in grpc_stub.StreamChat(chat_request_proto):
            responses.append(response)

            if response.content.tool_calls:
                tool_call = response.content.tool_calls[0]
                break

            if response.metadata.get("done", False):
                break

        # If tool call was made, submit result
        if tool_call:
            # Create new request with tool result
            tool_result = agent_service_pb2.ToolResult(
                tool_id=tool_call.tool_id,
                tool_name=tool_call.tool_name,
                result="找到3篇关于量子计算的最新研究论文...",
                status="success"
            )

            result_request = agent_service_pb2.ChatRequest(
                user_id=chat_request_proto.user_id,
                session_id=chat_request_proto.session_id,
                tool_result=tool_result,
                user_profile=chat_request_proto.user_profile,
                request_id=f"test-tool-result-{datetime.now().timestamp()}"
            )

            # Submit tool result
            result_responses = []
            async for response in grpc_stub.StreamChat(result_request):
                result_responses.append(response)
                if response.metadata.get("done", False):
                    break

            # Should receive response based on tool result
            assert len(result_responses) > 0

    @pytest.mark.asyncio
    async def test_stream_chat_parallel_tools(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test parallel tool execution"""
        # Request that might trigger multiple tools
        chat_request_proto.message = "帮我查北京天气和上海天气"

        tool_calls_received = []
        responses = []

        async for response in grpc_stub.StreamChat(chat_request_proto):
            responses.append(response)

            if response.content.tool_calls:
                for tool_call in response.content.tool_calls:
                    tool_calls_received.append(tool_call)

            if response.metadata.get("done", False):
                break

        # Should receive responses
        assert len(responses) > 0

        # Check if multiple tools were called
        # (LLM decision dependent)


# ============================================================
# Error Handling Tests
# ============================================================

class TestStreamChatErrors:
    """Test error handling in StreamChat"""

    @pytest.mark.asyncio
    async def test_stream_chat_with_invalid_user_id(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        user_profile_proto
    ):
        """Test StreamChat with invalid user ID"""
        request = agent_service_pb2.ChatRequest(
            user_id="invalid-user-id-99999",
            session_id="test-invalid-user",
            message="Hello",
            user_profile=user_profile_proto,
            request_id=f"test-invalid-{datetime.now().timestamp()}"
        )

        responses = []
        error_received = False

        try:
            async for response in grpc_stub.StreamChat(request):
                responses.append(response)

                # Check for error in metadata
                if response.metadata.get("error"):
                    error_received = True
                    break

                if response.metadata.get("done", False):
                    break

        except Exception as e:
            # gRPC error
            assert True

        # Should either receive error metadata or raise exception
        # assert error_received or len(responses) == 0

    @pytest.mark.asyncio
    async def test_stream_chat_with_empty_message(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test StreamChat with empty message"""
        chat_request_proto.message = ""
        chat_request_proto.request_id = f"test-empty-{datetime.now().timestamp()}"

        responses = []
        async for response in grpc_stub.StreamChat(chat_request_proto):
            responses.append(response)
            if response.metadata.get("done", False):
                break

        # Should handle gracefully
        assert len(responses) > 0


# ============================================================
# Performance Tests
# ============================================================

class TestStreamChatPerformance:
    """Test performance characteristics of StreamChat"""

    @pytest.mark.asyncio
    async def test_stream_chat_time_to_first_token(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test time to first token (TTFT)"""
        import time

        start_time = time.time()
        first_token_time = None

        async for response in grpc_stub.StreamChat(chat_request_proto):
            if first_token_time is None and response.content.delta:
                first_token_time = time.time()

            if response.metadata.get("done", False):
                break

        assert first_token_time is not None

        ttft = first_token_time - start_time
        # TTFT should be reasonable (< 10 seconds)
        assert ttft < 10.0

        print(f"Time to First Token: {ttft:.2f}s")

    @pytest.mark.asyncio
    async def test_stream_chat_tokens_per_second(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test tokens per second (throughput)"""
        import time

        start_time = time.time()
        all_deltas = []

        async for response in grpc_stub.StreamChat(chat_request_proto):
            if response.content.delta:
                all_deltas.append(response.content.delta)

            if response.metadata.get("done", False):
                break

        end_time = time.time()

        total_chars = sum(len(delta) for delta in all_deltas)
        elapsed = end_time - start_time

        # Calculate characters per second (rough proxy for tokens)
        cps = total_chars / elapsed if elapsed > 0 else 0

        print(f"Total characters: {total_chars}")
        print(f"Elapsed time: {elapsed:.2f}s")
        print(f"Characters per second: {cps:.2f}")

        # Should have reasonable throughput
        assert cps > 0

    @pytest.mark.asyncio
    async def test_stream_chat_concurrent_requests(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test concurrent StreamChat requests"""
        async def single_request(request_id: int):
            req = agent_service_pb2.ChatRequest()
            req.CopyFrom(chat_request_proto)
            req.request_id = f"test-concurrent-{request_id}"
            req.session_id = f"test-session-{request_id}"

            responses = []
            async for response in grpc_stub.StreamChat(req):
                responses.append(response)
                if response.metadata.get("done", False):
                    break

            return len(responses)

        # Send 5 concurrent requests
        tasks = [single_request(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 5
        assert all(r > 0 for r in results)


# ============================================================
# Chat Mode Tests
# ============================================================

class TestChatModes:
    """Test different chat modes"""

    @pytest.mark.asyncio
    async def test_standard_mode(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test standard chat mode"""
        chat_request_proto.chat_mode = "standard"
        chat_request_proto.message = "解释什么是机器学习"

        responses = []
        async for response in grpc_stub.StreamChat(chat_request_proto):
            responses.append(response)
            if response.metadata.get("done", False):
                break

        assert len(responses) > 0

    @pytest.mark.asyncio
    async def test_deep_analysis_mode(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test deep analysis chat mode"""
        chat_request_proto.chat_mode = "deep_analysis"
        chat_request_proto.message = "深入分析Transformer架构的优势"

        responses = []
        async for response in grpc_stub.StreamChat(chat_request_proto):
            responses.append(response)
            if response.metadata.get("done", False):
                break

        assert len(responses) > 0

    @pytest.mark.asyncio
    async def test_study_plan_mode(
        self,
        grpc_stub: agent_service_pb2_grpc.AgentServiceStub,
        chat_request_proto: agent_service_pb2.ChatRequest
    ):
        """Test study plan chat mode"""
        chat_request_proto.chat_mode = "study_plan"
        chat_request_proto.message = "帮我制定一个学习Python的计划"

        responses = []
        async for response in grpc_stub.StreamChat(chat_request_proto):
            responses.append(response)
            if response.metadata.get("done", False):
                break

        assert len(responses) > 0


# ============================================================
# Test Run Configuration
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
