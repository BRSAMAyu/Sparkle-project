"""
STT Provider抽象接口
定义语音转文字服务的统一接口，支持多Provider切换
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class STTProvider(ABC):
    """
    STT (Speech to Text) Provider 抽象基类

    所有语音识别服务提供商都必须实现这个接口。
    支持流式识别和文件识别两种模式。
    """

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str | None = None,
        sample_rate: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        实时语音识别流式接口

        Args:
            audio_stream: 音频数据流生成器（字节流）
            language: 目标语言代码（如 'zh-CN', 'en-US'）
            sample_rate: 音频采样率（Hz），默认16000

        Yields:
            识别结果文本（支持流式返回）

        Example:
            async for text in provider.transcribe_stream(audio_stream):
                print(f"实时识别结果: {text}")
        """
        pass

    @abstractmethod
    async def transcribe_file(
        self,
        file_path: str,
        language: str | None = None,
    ) -> str:
        """
        文件语音识别接口

        Args:
            file_path: 音频文件路径
            language: 目标语言代码

        Returns:
            识别结果文本

        Example:
            text = await provider.transcribe_file("audio.wav", language="zh-CN")
        """
        pass

    async def close(self) -> None:
        """
        清理资源

        默认实现为空，子类可以重写以释放连接等资源
        """
        pass
