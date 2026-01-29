from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Send a chat completion request and return the full response content.
        """
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion chunks.
        """
        pass
