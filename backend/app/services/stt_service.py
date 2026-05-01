from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from app.config import settings
from app.services.stt.providers.base import STTProvider


class STTService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

        self.provider: STTProvider | None = None
        self.backup_provider: STTProvider | None = None
        self.stream_provider: STTProvider | None = None
        self._init_provider()

    def _init_provider(self):
        """根据配置初始化STT Provider"""
        provider_name = (settings.STT_PROVIDER or "zhipu").lower()
        backup_name = (settings.STT_BACKUP_PROVIDER or "").lower()
        self.provider = self._build_provider(provider_name)
        alternate_name = backup_name or ("xunfei" if provider_name == "zhipu" else "zhipu")
        self.backup_provider = self._build_provider(alternate_name)

        # 移动端的聊天、群聊、工具页都通过 WebSocket 走流式识别。
        # 当讯飞凭证可用时，优先用其原生流式协议，避免智谱配额问题直接打断实时链路。
        if provider_name == "zhipu" and self.backup_provider is not None:
            self.stream_provider = self.backup_provider
        else:
            self.stream_provider = self.provider

        if self.provider is not None:
            logger.info(f"STT primary provider initialized: {provider_name}")
        else:
            logger.warning(f"STT primary provider unavailable: {provider_name}")

        if self.backup_provider is not None:
            logger.info(f"STT backup provider initialized: {alternate_name}")

    def _build_provider(self, provider_name: str) -> STTProvider | None:
        try:
            if provider_name == "zhipu":
                from app.services.stt.providers.zhipu_provider import ZhipuProvider

                if not self._is_configured_value(settings.ZHIPU_API_KEY):
                    return None
                return ZhipuProvider()

            if provider_name == "xunfei":
                from app.services.stt.providers.xunfei_provider import XunFeiProvider

                if not all(
                    self._is_configured_value(value)
                    for value in (
                        settings.XUNFEI_APP_ID,
                        settings.XUNFEI_API_KEY,
                        settings.XUNFEI_API_SECRET,
                    )
                ):
                    return None
                return XunFeiProvider()
        except Exception as e:
            logger.error(f"Failed to initialize STT provider {provider_name}: {e}")
            return None

        logger.warning(f"STT Provider not supported: {provider_name}")
        return None

    def _is_configured_value(self, value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def _ordered_providers(self) -> list[STTProvider]:
        providers: list[STTProvider] = []
        for provider in (self.provider, self.backup_provider):
            if provider is not None and provider not in providers:
                providers.append(provider)
        return providers

    def _should_try_backup(self, error_message: str) -> bool:
        lowered = error_message.lower()
        fallback_markers = (
            "余额不足",
            "无可用资源包",
            "rate limit",
            "rate_limit",
            "429",
            "ffprobe",
            "ffmpeg",
            "no such file or directory",
            "provider unavailable",
            "api key",
            "未配置",
            "识别失败",
            "request failed",
            "timeout",
            "timed out",
        )
        return any(marker in lowered for marker in fallback_markers)

    def _provider_timeout(self, provider: STTProvider) -> float:
        if provider.__class__.__name__ == "XunFeiProvider":
            return 60.0
        return 90.0

    async def transcribe_file(self, file_path: str, language: str | None = None) -> dict[str, Any]:
        """
        Transcribe an audio file using configured STT Provider.
        """
        providers = self._ordered_providers()
        if not providers:
            return {"text": "STT Service Unavailable (Provider Not Initialized)", "error": True}

        if not os.path.exists(file_path):
            return {"text": "", "error": "File not found"}

        last_error: str | None = None
        for index, provider in enumerate(providers):
            provider_name = provider.__class__.__name__
            try:
                logger.info(f"Transcribing file: {file_path} using {provider_name}")
                text = await asyncio.wait_for(
                    provider.transcribe_file(file_path, language=language),
                    timeout=self._provider_timeout(provider),
                )

                if not text:
                    raise RuntimeError("Empty transcription result")
                if index < len(providers) - 1 and self._should_try_backup(text):
                    raise RuntimeError(text)

                return {"text": text, "error": False}
            except Exception as e:
                last_error = str(e)
                logger.warning(f"STT provider {provider_name} failed: {e}")
                if index == len(providers) - 1 or not self._should_try_backup(last_error):
                    break

        if settings.DEMO_MODE:
            return {"text": "这是演示模式下的模拟语音转写结果。实际调用失败，请检查 API 配置。", "error": False}

        return {"text": f"Transcription Error: {last_error or 'Unknown STT error'}", "error": True}

    async def enhance_transcript(self, text: str) -> str:
        """
        Use LLM to post-process text:
        - Add punctuation
        - Correct typos
        - Separate speakers (if apparent)
        """
        if not text or len(text) < 2:
            return text

        from app.services.llm_fallback_utils import stt_llm

        system_prompt = """
        You are a professional transcript editor.
        Task: Optimize the following Automatic Speech Recognition (ASR) text.

        Requirements:
        1. Correct punctuation and capitalization.
        2. Fix obvious homophone errors (typos).
        3. If there are clearly multiple speakers (based on context), try to format it as "Speaker A: ... Speaker B: ...".
        4. Keep the original meaning and tone.
        5. Output ONLY the corrected text.
        """

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]

        enhanced_text = await stt_llm.call(messages, fallback=text, temperature=0.3)
        return enhanced_text.strip() if enhanced_text else text

    _PROVIDER_ERROR_MARKERS = (
        "未配置",
        "识别失败",
        "语音识别失败",
        "API密钥",
        "请求失败",
    )

    async def handle_websocket_stream(self, websocket: WebSocket):
        """
        Handle WebSocket audio stream using configured STT Provider.

        This method creates an audio stream generator and passes it to the provider
        for real-time transcription. Results are streamed back to the client.
        """
        await websocket.accept()

        session_id = str(uuid.uuid4())
        logger.info(f"WebSocket STT stream started: {session_id}")

        active_provider = self.stream_provider or self.provider
        if not active_provider:
            await websocket.send_json(
                {"type": "error", "content": "STT Service Unavailable (Provider Not Initialized)"}
            )
            await websocket.close()
            return

        try:
            # Create audio stream generator from WebSocket
            audio_stream = self._create_audio_stream_generator(websocket)

            # Transcribe using the provider
            async for text in active_provider.transcribe_stream(audio_stream):
                # Detect error text leaked from providers as transcription
                if any(marker in text for marker in self._PROVIDER_ERROR_MARKERS):
                    logger.warning(f"Provider returned error as text: {text[:80]}")
                    await websocket.send_json({"type": "error", "content": "STT provider error"})
                    break
                await websocket.send_json({"type": "transcription", "text": text, "is_final": False})

            # Send completion signal
            await websocket.send_json({"type": "status", "content": "completed"})

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            try:
                await websocket.send_json({"type": "error", "content": "STT stream error"})
            except Exception:
                pass

    async def _create_audio_stream_generator(self, websocket: WebSocket) -> AsyncGenerator[bytes, None]:
        """
        Create an async generator that yields audio chunks from WebSocket.

        This generator handles:
        - Receiving audio bytes
        - Handling control messages (STOP)
        - Proper cleanup on disconnect
        """
        try:
            while True:
                # Receive data
                data = await websocket.receive()

                if "bytes" in data:
                    chunk = data["bytes"]
                    if chunk:  # Only yield non-empty chunks
                        yield chunk

                elif "text" in data:
                    text = data["text"]
                    if text == "STOP":
                        # Stop signal received
                        break

        except WebSocketDisconnect:
            # Connection closed, stop the generator
            return
        except Exception as e:
            logger.error(f"Error in audio stream generator: {e}")
            raise


stt_service = STTService()
