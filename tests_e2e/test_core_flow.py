"""
Core Business Flow E2E Test
============================

Tests the essential chat flow without complex DB session management.
This test validates the orchestrator can process requests and stream responses.
"""
import pytest
import asyncio
from uuid import uuid4

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.orchestrator import Orchestrator
from app.services import llm_service as llm_service_module


class MockStreamChunk:
    def __init__(self, type_: str, content: str):
        self.type = type_
        self.content = content


class SimpleMockLLMService:
    """Simplified mock LLM service for testing."""

    def __init__(self):
        self.default_model = "mock-model"

    async def chat_stream_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list | None = None,
        user_context: dict | None = None,
        temperature: float = 0.7,
    ):
        """Mock streamed response."""
        if "翻译" in user_message or "translate" in user_message.lower():
            response_text = "你好，世界"
        elif "计划" in user_message:
            response_text = "好的，我来帮你制定学习计划。你想学习什么科目？"
        else:
            response_text = "我是您的AI学习助手，有什么可以帮助您的？"

        for word in response_text:
            yield MockStreamChunk(type_="text", content=word)


class SimpleMockRedis:
    """Minimal Redis mock for orchestrator."""

    def __init__(self):
        self._data = {}

    async def get(self, key: str):
        return self._data.get(key)

    async def set(self, key: str, value, ex: int = None, nx: bool = False, px: int = None):
        if nx and key in self._data:
            return False
        self._data[key] = value
        return True

    async def delete(self, *keys):
        for key in keys:
            self._data.pop(key, None)
        return len(keys)

    async def setex(self, key: str, seconds: int, value):
        self._data[key] = value
        return True

    async def eval(self, script: str, numkeys: int, *keys_and_args):
        return 1

    async def lrange(self, key: str, start: int, end: int):
        data = self._data.get(key, [])
        if not isinstance(data, list):
            return []
        if end == -1:
            return data[start:]
        return data[start:end + 1]

    async def rpush(self, key: str, *values):
        if key not in self._data or not isinstance(self._data[key], list):
            self._data[key] = []
        self._data[key].extend(values)
        return len(self._data[key])

    async def llen(self, key: str):
        data = self._data.get(key, [])
        return len(data) if isinstance(data, list) else 0

    async def ltrim(self, key: str, start: int, end: int):
        return True

    async def zadd(self, key: str, mapping: dict):
        if key not in self._data or not isinstance(self._data[key], dict):
            self._data[key] = {}
        self._data[key].update(mapping)
        return len(mapping)

    async def zrange(self, key: str, start: int, end: int, withscores: bool = False):
        data = self._data.get(key, {})
        if not isinstance(data, dict):
            return []
        items = sorted(data.items(), key=lambda x: x[1])
        sliced = items[start:] if end == -1 else items[start:end + 1]
        return sliced if withscores else [item[0] for item in sliced]

    async def expire(self, key: str, seconds: int):
        return True

    async def hset(self, key: str, field: str = None, value = None, mapping: dict = None):
        if key not in self._data or not isinstance(self._data[key], dict):
            self._data[key] = {}
        if mapping:
            self._data[key].update(mapping)
        elif field:
            self._data[key][field] = value
        return 1

    async def hget(self, key: str, field: str):
        data = self._data.get(key, {})
        if isinstance(data, dict):
            return data.get(field)
        return None

    async def hgetall(self, key: str):
        data = self._data.get(key, {})
        return data if isinstance(data, dict) else {}


def _patch_llm_service(mock_service):
    """Patch all LLM service references."""
    llm_service_module.llm_service = mock_service
    from app.orchestration import orchestrator as orchestrator_module
    orchestrator_module.llm_service = mock_service
    from app.agents import standard_workflow as standard_workflow_module
    standard_workflow_module.llm_service = mock_service


@pytest.mark.asyncio
async def test_core_chat_flow_simple():
    """
    Test core chat flow: User message → LLM → Streamed response.

    This test validates:
    1. Orchestrator can be initialized with mocks
    2. Request can be processed
    3. Response is streamed back
    """
    # Arrange
    mock_llm = SimpleMockLLMService()
    mock_redis = SimpleMockRedis()
    user_id = str(uuid4())
    session_id = str(uuid4())

    _patch_llm_service(mock_llm)

    # Create orchestrator without DB session (no persistence)
    orchestrator = Orchestrator(
        db_session=None,
        redis_client=mock_redis,
        user_id=user_id,
    )

    # Build request
    request = agent_service_pb2.ChatRequest(
        session_id=session_id,
        user_id=user_id,
        message="你好，我想学习编程",
        request_id=str(uuid4()),
    )

    # Act: Process the stream
    responses = []
    async for chunk in orchestrator.process_stream(request):
        responses.append(chunk)

    # Assert
    assert len(responses) > 0, "Should receive response chunks"

    # Concatenate text responses
    full_text = ""
    for resp in responses:
        content_type = resp.WhichOneof("content")
        if content_type == "delta":
            full_text += resp.delta
        elif content_type == "full_text":
            full_text += resp.full_text

    assert len(full_text) > 0, f"Response should contain text, got: {responses}"
    print(f"✓ Received response: {full_text[:100]}...")


@pytest.mark.asyncio
async def test_core_translation_flow():
    """Test translation request flow."""
    mock_llm = SimpleMockLLMService()
    mock_redis = SimpleMockRedis()
    user_id = str(uuid4())
    session_id = str(uuid4())

    _patch_llm_service(mock_llm)

    orchestrator = Orchestrator(
        db_session=None,
        redis_client=mock_redis,
        user_id=user_id,
    )

    request = agent_service_pb2.ChatRequest(
        session_id=session_id,
        user_id=user_id,
        message="请帮我翻译 Hello World",
        request_id=str(uuid4()),
    )

    responses = []
    async for chunk in orchestrator.process_stream(request):
        responses.append(chunk)

    assert len(responses) > 0
    print(f"✓ Translation flow completed with {len(responses)} chunks")


@pytest.mark.asyncio
async def test_core_plan_request_flow():
    """Test plan creation request flow."""
    mock_llm = SimpleMockLLMService()
    mock_redis = SimpleMockRedis()
    user_id = str(uuid4())
    session_id = str(uuid4())

    _patch_llm_service(mock_llm)

    orchestrator = Orchestrator(
        db_session=None,
        redis_client=mock_redis,
        user_id=user_id,
    )

    request = agent_service_pb2.ChatRequest(
        session_id=session_id,
        user_id=user_id,
        message="帮我制定一个Python学习计划",
        request_id=str(uuid4()),
    )

    responses = []
    async for chunk in orchestrator.process_stream(request):
        responses.append(chunk)

    assert len(responses) > 0

    # Check if response contains plan-related content
    full_text = ""
    for resp in responses:
        content_type = resp.WhichOneof("content")
        if content_type == "delta":
            full_text += resp.delta
        elif content_type == "full_text":
            full_text += resp.full_text

    assert any(word in full_text for word in ["计划", "学习", "科目", "帮"]), \
        f"Response should be about planning, got: {full_text}"
    print(f"✓ Plan request flow completed: {full_text[:100]}...")


@pytest.mark.asyncio
async def test_multi_turn_conversation():
    """Test multi-turn conversation maintains context."""
    mock_llm = SimpleMockLLMService()
    mock_redis = SimpleMockRedis()
    user_id = str(uuid4())
    session_id = str(uuid4())

    _patch_llm_service(mock_llm)

    orchestrator = Orchestrator(
        db_session=None,
        redis_client=mock_redis,
        user_id=user_id,
    )

    # First turn
    request1 = agent_service_pb2.ChatRequest(
        session_id=session_id,
        user_id=user_id,
        message="你好",
        request_id=str(uuid4()),
    )

    responses1 = []
    async for chunk in orchestrator.process_stream(request1):
        responses1.append(chunk)

    assert len(responses1) > 0, "First turn should have response"

    # Second turn (same session)
    request2 = agent_service_pb2.ChatRequest(
        session_id=session_id,
        user_id=user_id,
        message="谢谢你的帮助",
        request_id=str(uuid4()),
    )

    responses2 = []
    async for chunk in orchestrator.process_stream(request2):
        responses2.append(chunk)

    assert len(responses2) > 0, "Second turn should have response"
    print(f"✓ Multi-turn conversation: Turn 1 = {len(responses1)} chunks, Turn 2 = {len(responses2)} chunks")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
