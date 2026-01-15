from typing import AsyncGenerator, List, Dict, Any
from fastapi import HTTPException
from loguru import logger

try:
    from openai import AsyncOpenAI, APIError
    HAS_OPENAI = True
except ImportError:
    AsyncOpenAI = None
    APIError = Exception
    HAS_OPENAI = False

from app.services.llm.base import LLMProvider

class OpenAICompatibleProvider(LLMProvider):
    """
    Provider for OpenAI-compatible APIs (OpenAI, DeepSeek, Qwen, etc.)
    """
    def __init__(self, api_key: str, base_url: str):
        if not HAS_OPENAI:
            raise HTTPException(
                status_code=501,
                detail="OpenAI client not installed. Install llm extras to enable LLM features."
            )
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        model: str,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                **kwargs
            )
            return response.choices[0].message.content or ""
        except APIError as e:
            logger.error(f"LLM API Error: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected LLM Error: {e}")
            raise e

    async def stream_chat(
        self, 
        messages: List[Dict[str, str]], 
        model: str,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        try:
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
        except APIError as e:
            logger.error(f"LLM Stream API Error: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected LLM Stream Error: {e}")
            raise e