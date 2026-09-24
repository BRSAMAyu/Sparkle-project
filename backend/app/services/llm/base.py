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

        契约：全部实现都是 async-generator 函数（函数体含 yield，调用即
        返回 AsyncGenerator 而非协程），调用方直接 ``async for`` 消费。
        抽象声明体中的 yield 仅为对齐该契约，永不执行。
        """
        yield ""
