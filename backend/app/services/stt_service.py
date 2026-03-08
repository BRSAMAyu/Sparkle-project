import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from app.config import settings
from app.services.llm_service import llm_service
from app.services.stt.providers.base import STTProvider


class STTService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

        # Initialize STT Provider based on configuration
        self.provider: STTProvider | None = None
        self._init_provider()

    def _init_provider(self):
        """根据配置初始化STT Provider"""
        provider_name = (settings.STT_PROVIDER or "zhipu").lower()
        if provider_name == "xunfei":
            logger.warning("STT_PROVIDER=xunfei 已废弃，自动切换到 zhipu")
            provider_name = "zhipu"

        if provider_name != "zhipu":
            logger.warning(f"STT Provider not supported: {provider_name}")
            self.provider = None
            return

        try:
            from app.services.stt.providers.zhipu_provider import ZhipuProvider

            self.provider = ZhipuProvider()
            logger.info("STT Provider initialized: zhipu")
        except Exception as e:
            logger.error(f"Failed to initialize ZhipuProvider: {e}")
            self.provider = None

    async def transcribe_file(self, file_path: str, language: str | None = None) -> dict[str, Any]:
        """
        Transcribe an audio file using configured STT Provider.
        """
        if not self.provider:
            return {"text": "STT Service Unavailable (Provider Not Initialized)", "error": True}

        if not os.path.exists(file_path):
            return {"text": "", "error": "File not found"}

        try:
            logger.info(f"Transcribing file: {file_path} using {settings.STT_PROVIDER}")

            text = await self.provider.transcribe_file(file_path, language=language)

            return {"text": text, "error": False}
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            # Mock response in Demo Mode if failure
            if settings.DEMO_MODE:
                return {"text": "这是演示模式下的模拟语音转写结果。实际调用失败，请检查 API 配置。", "error": False}
            return {"text": f"Transcription Error: {str(e)}", "error": True}

    async def enhance_transcript(self, text: str) -> str:
        """
        Use LLM to post-process text:
        - Add punctuation
        - Correct typos
        - Separate speakers (if apparent)
        """
        if not text or len(text) < 2:
            return text

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

        try:
            enhanced_text = await llm_service.chat(messages, temperature=0.3)
            return enhanced_text.strip()
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            return text

    async def handle_websocket_stream(self, websocket: WebSocket):
        """
        Handle WebSocket audio stream using configured STT Provider.

        This method creates an audio stream generator and passes it to the provider
        for real-time transcription. Results are streamed back to the client.
        """
        await websocket.accept()

        session_id = str(uuid.uuid4())
        logger.info(f"WebSocket STT stream started: {session_id}")

        if not self.provider:
            await websocket.send_json(
                {"type": "error", "content": "STT Service Unavailable (Provider Not Initialized)"}
            )
            await websocket.close()
            return

        try:
            # Create audio stream generator from WebSocket
            audio_stream = self._create_audio_stream_generator(websocket)

            # Transcribe using the provider
            async for text in self.provider.transcribe_stream(audio_stream):
                await websocket.send_json({"type": "transcription", "text": text, "is_final": False})

            # Send completion signal
            await websocket.send_json({"type": "status", "content": "completed"})

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.send_json({"type": "error", "content": str(e)})
        finally:
            # Cleanup
            if self.provider:
                await self.provider.close()

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
