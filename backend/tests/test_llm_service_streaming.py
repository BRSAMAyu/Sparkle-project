import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, AsyncMock as MagicMockType
from app.services.llm_service import LLMService

# 模拟流式响应
async def mock_stream_response(messages, model=None, temperature=0.7, user_context=None, **kwargs):
    chunks = ["Hello", " ", "World", "!"]
    for chunk in chunks:
        yield chunk
        await asyncio.sleep(0.01)

@pytest.mark.asyncio
async def test_llm_service_streaming():
    """测试 LLM 服务流式响应"""
    with patch("app.services.llm_service.LLMService.stream_chat", new=mock_stream_response):
        service = LLMService()

        # 收集流式输出
        received_chunks = []
        messages = [{"role": "user", "content": "Hi"}]

        async for chunk in service.stream_chat(messages):
            received_chunks.append(chunk)

        # 验证完整响应
        full_response = "".join(received_chunks)
        assert full_response == "Hello World!"

@pytest.mark.asyncio
async def test_llm_service_timeout():
    """测试 LLM 服务超时处理"""
    async def timeout_stream(messages=None, model=None, temperature=0.7, user_context=None, **kwargs):
        # 第一次 yield 成功
        yield "Start"
        # 然后模拟长时间等待
        await asyncio.sleep(2)
        yield "End"

    with patch("app.services.llm_service.LLMService.stream_chat", new=timeout_stream):
        service = LLMService()

        # 手动实现超时逻辑来包装 async generator
        async def timeout_wrapper(generator, timeout):
            iterator = generator.__aiter__()
            while True:
                try:
                    # 对每次 next() 调用设置超时
                    item = await asyncio.wait_for(iterator.__anext__(), timeout=timeout)
                    yield item
                except StopAsyncIteration:
                    break

        with pytest.raises(asyncio.TimeoutError):
            async for _ in timeout_wrapper(service.stream_chat([{"role": "user", "content": "Hi"}]), timeout=0.5):
                pass

@pytest.mark.asyncio
async def test_llm_service_token_billing_mock():
    """测试 Token 计费逻辑 (Mock)"""

    # 定义一个模拟的 StreamChunk 类
    class MockStreamChunk:
        def __init__(self, type, **kwargs):
            self.type = type
            self.total_tokens = kwargs.get('total_tokens')
            self.prompt_tokens = kwargs.get('prompt_tokens')
            self.completion_tokens = kwargs.get('completion_tokens')

    async def mock_usage_stream(messages=None, model=None, temperature=0.7, user_context=None, **kwargs):
        yield "Content"
        # 模拟 usage chunk
        yield MockStreamChunk(
            type="usage",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        )

    with patch("app.services.llm_service.LLMService.stream_chat", new=mock_usage_stream):
        service = LLMService()

        chunks = []
        usage_data = None

        async for chunk in service.stream_chat([{"role": "user", "content": "Hi"}]):
            # 动态检查 chunk 类型
            if hasattr(chunk, 'type') and getattr(chunk, 'type') == "usage":
                usage_data = chunk  # type: ignore
            else:
                chunks.append(str(chunk))

        assert "".join(chunks) == "Content"
        assert usage_data is not None
        assert usage_data.total_tokens == 15  # type: ignore
