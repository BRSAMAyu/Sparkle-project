import asyncio
from collections.abc import AsyncGenerator

from fastapi import HTTPException
from loguru import logger

try:
    from openai import APIError, AsyncOpenAI, Timeout
    HAS_OPENAI = True
except ImportError:
    AsyncOpenAI = None
    APIError = Exception
    Timeout = None
    HAS_OPENAI = False

from app.services.llm.base import LLMProvider
from app.services.llm.concurrency import llm_concurrency


class OpenAICompatibleProvider(LLMProvider):
    """
    Provider for OpenAI-compatible APIs (OpenAI, DeepSeek, Qwen, etc.)
    """
    def __init__(self, api_key: str, base_url: str, timeout_seconds: float = 60.0):
        if not HAS_OPENAI:
            raise HTTPException(
                status_code=501,
                detail="OpenAI client not installed. Install llm extras to enable LLM features."
            )
        if not api_key:
            logger.error(f"LLM Provider Initialization Error: api_key is empty for base_url={base_url}")
            # Do not raise here to allow fallback/demo mode to handle it, but log it clearly
            self.api_key = "MISSING_KEY"
        else:
            self.api_key = api_key
            
        self.base_url = base_url

        # Set explicit timeout:
        # - connect: 10s for initial connection
        # - read: 60s for response (covers GLM thinking mode which can take 30s+)
        # - write: 30s for request upload
        # - pool: 10s for connection pool acquisition
        timeout_config = Timeout(
            timeout=timeout_seconds,
            connect=10.0,
        ) if Timeout else None

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_config,
        )

    def _get_provider_name(self) -> str:
        """从 base_url 提取提供商名称"""
        url_lower = self.base_url.lower()
        if "bigmodel" in url_lower or "zhipu" in url_lower:
            if "/api/coding/" in url_lower:
                return "zhipu_coding"
            return "zhipu"
        elif "deepseek" in url_lower:
            return "deepseek"
        elif "xiaomi" in url_lower or "mimo" in url_lower:
            return "xiaomi"
        elif "dashscope" in url_lower or "aliyun" in url_lower:
            return "dashscope"
        elif "siliconflow" in url_lower:
            return "siliconflow"
        return "default"

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        provider = self._get_provider_name()
        try:
            async with llm_concurrency.acquire(provider):
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    **kwargs
                )
                return response.choices[0].message.content or ""
        except asyncio.TimeoutError:
            logger.error(f"[LLMConcurrency] Timeout acquiring semaphore for {provider}")
            raise HTTPException(status_code=503, detail="LLM service is busy, please try again")
        except APIError as e:
            logger.error(f"LLM API Error: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected LLM Error: {e}")
            raise e

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        provider = self._get_provider_name()
        try:
            async with llm_concurrency.acquire(provider):
                stream = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    stream=True,
                    **kwargs
                )
                async for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
        except asyncio.TimeoutError:
            logger.error(f"[LLMConcurrency] Timeout acquiring semaphore for {provider}")
            yield ""
            return
        except APIError as e:
            logger.error(f"LLM Stream API Error: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected LLM Stream Error: {e}")
            raise e
