from typing import List, Dict, AsyncGenerator, Optional
from loguru import logger

from app.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.providers import OpenAICompatibleProvider

class LLMService:
    def __init__(self):
        self.provider: LLMProvider = OpenAICompatibleProvider(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE_URL
        )
        self.default_model = settings.LLM_MODEL_NAME

    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Send a chat request to the LLM.
        """
        model = model or self.default_model
        logger.debug(f"Sending chat request to model: {model}")
        return await self.provider.chat(messages, model=model, temperature=temperature, **kwargs)

    async def stream_chat(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response from the LLM.
        """
        model = model or self.default_model
        logger.debug(f"Starting stream chat with model: {model}")
        async for chunk in self.provider.stream_chat(messages, model=model, temperature=temperature, **kwargs):
            yield chunk

# Singleton instance
llm_service = LLMService()
