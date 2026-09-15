#!/usr/bin/env python3
"""
AI Chain Connectivity Test Script

Tests connectivity to all AI services:
- Zhipu LLM (primary)
- DeepSeek LLM
- DashScope Embedding
- Zhipu STT (availability check)
"""

import asyncio
import httpx
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_zhipu_llm():
    """Test Zhipu GLM API connectivity"""
    try:
        from app.config import settings

        api_key = settings.ZHIPU_API_KEY
        if not api_key:
            return False, "API key not configured"

        base_url = settings.ZHIPU_BASE_URL or "https://open.bigmodel.cn/api/paas/v4"
        model = settings.ZHIPU_CHAT_MODEL or "glm-4.7"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say 'test' in one word"}],
                    "max_tokens": 10,
                },
            )

            if response.status_code == 200:
                return True, "Connected"
            elif response.status_code == 401:
                return False, "Invalid API key"
            elif response.status_code == 403:
                return False, "Access forbidden - check permissions"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"
    except Exception as e:
        return False, str(e)


async def test_deepseek_llm():
    """Test DeepSeek API connectivity"""
    try:
        from app.config import settings

        api_key = settings.DEEPSEEK_API_KEY
        if not api_key:
            return False, "API key not configured"

        base_url = settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com"
        model = settings.DEEPSEEK_CHAT_MODEL or "deepseek-v4-flash"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say 'test' in one word"}],
                    "max_tokens": 10,
                },
            )

            if response.status_code == 200:
                return True, "Connected"
            elif response.status_code == 401:
                return False, "Invalid API key"
            elif response.status_code == 403:
                return False, "Access forbidden"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"
    except Exception as e:
        return False, str(e)


async def test_dashscope_embedding():
    """Test DashScope Embedding API connectivity using the SDK"""
    try:
        from app.config import settings

        api_key = settings.DASHSCOPE_API_KEY
        if not api_key:
            return False, "API key not configured"

        model = settings.DASHSCOPE_EMBEDDING_MODEL or "text-embedding-v4"
        base_url = settings.DASHSCOPE_BASE_HTTP_API_URL or "https://dashscope.aliyuncs.com/api/v1"

        # Use the DashScope SDK's TextEmbedding
        try:
            import dashscope
            from dashscope import TextEmbedding
        except ImportError:
            return False, "dashscope package not installed"

        dashscope.api_key = api_key
        if base_url:
            dashscope.base_http_api_url = base_url

        # Call the embedding API synchronously in a thread
        resp = await asyncio.to_thread(TextEmbedding.call, model=model, input="test string for embedding")

        if resp.status_code == 200:
            return True, "Connected"
        elif resp.status_code == 401:
            return False, "Invalid API key"
        elif resp.status_code == 403:
            return False, "Access forbidden"
        else:
            return False, f"HTTP {resp.status_code}: {getattr(resp, 'message', 'unknown error')}"
    except Exception as e:
        return False, str(e)


def check_stt_service():
    """Check if Zhipu STT service is configured and available"""
    try:
        from app.config import settings

        api_key = settings.ZHIPU_API_KEY
        asr_base_url = settings.ZHIPU_ASR_BASE_URL

        if not api_key:
            return False, "Zhipu API key not configured"

        if not asr_base_url:
            return False, "ASR base URL not configured"

        # Check if provider module can be imported
        try:
            from app.services.stt.providers.zhipu_provider import ZhipuProvider

            provider = ZhipuProvider()
            if not provider.api_key:
                return False, "ZhipuProvider initialized but API key is empty"
            return True, "Available (provider module can be imported)"
        except ImportError as e:
            return False, f"Cannot import ZhipuProvider: {e}"
    except Exception as e:
        return False, str(e)


async def main():
    print("=" * 60)
    print("AI Chain Connectivity Test")
    print("=" * 60)
    print()

    # Run tests concurrently
    results = await asyncio.gather(
        test_zhipu_llm(),
        test_deepseek_llm(),
        test_dashscope_embedding(),
    )

    zhipu_status, zhipu_msg = results[0]
    deepseek_status, deepseek_msg = results[1]
    dashscope_status, dashscope_msg = results[2]
    stt_available, stt_msg = check_stt_service()

    # Format results
    def format_status(connected, msg):
        status = "CONNECTED" if connected else "FAILED"
        return f"[{status}] {msg}"

    print("Test Results:")
    print("-" * 60)
    print(f"Zhipu LLM:         {format_status(zhipu_status, zhipu_msg)}")
    print(f"DeepSeek LLM:      {format_status(deepseek_status, deepseek_msg)}")
    print(f"DashScope Embedding: {format_status(dashscope_status, dashscope_msg)}")
    print(f"Zhipu STT:         {'AVAILABLE' if stt_available else 'NOT_CONFIGURED'} - {stt_msg}")
    print("-" * 60)

    # Overall status
    connected_count = sum([zhipu_status, deepseek_status, dashscope_status])
    all_stt_ready = stt_available

    print()
    if connected_count == 3 and all_stt_ready:
        overall = "ALL_WORKING"
    elif connected_count > 0:
        overall = "PARTIAL"
    else:
        overall = "FAILED"

    print(f"Overall: {overall} ({connected_count}/3 LLM services connected)")
    print()

    # Return exit code
    return 0 if overall == "ALL_WORKING" else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
