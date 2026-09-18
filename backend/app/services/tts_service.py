"""
TTS (Text to Speech) 服务。

比赛主力供应商为阿里云百炼：
  POST {DASHSCOPE_BASE_HTTP_API_URL}/services/aigc/multimodal-generation/generation
  model=qwen3-tts-instruct-flash → output.audio.data(base64) / output.audio.url

保留 provider 结构，便于后续接入其他 TTS 供应商。移动端当前使用端上
flutter_tts，本服务面向服务端合成场景（如通知播报、多模态回复）。
"""

from __future__ import annotations

import base64
from typing import Any

import httpx
from loguru import logger

from app.config import settings


class TTSProviderError(RuntimeError):
    """TTS 合成失败。"""


def _is_probably_audio(data: bytes) -> bool:
    if len(data) < 12:
        return False
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":  # wav
        return True
    if data[:3] == b"ID3" or (data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):  # mp3
        return True
    return False


class BailianTTSProvider:
    """百炼 Qwen3-TTS-Instruct-Flash Provider（HTTP 非流式）。"""

    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.endpoint = (
            settings.DASHSCOPE_BASE_HTTP_API_URL.rstrip("/") + "/services/aigc/multimodal-generation/generation"
        )
        self.model = settings.QWEN_TTS_MODEL
        self.voice = settings.QWEN_TTS_VOICE
        self.audio_format = settings.QWEN_TTS_AUDIO_FORMAT
        self.timeout = httpx.Timeout(settings.QWEN_TTS_REQUEST_TIMEOUT_SECONDS)

        if not self.api_key:
            logger.warning("DASHSCOPE_API_KEY 未配置，BailianTTSProvider 将无法工作")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        text: str,
        voice: str | None = None,
        instructions: str | None = None,
    ) -> dict[str, Any]:
        input_body: dict[str, Any] = {"text": text}
        resolved_voice = voice or self.voice
        if resolved_voice:
            input_body["voice"] = resolved_voice
        if instructions:
            # instruction 控制仅 qwen3-tts-instruct 系列支持
            input_body["instructions"] = instructions

        return {
            "model": self.model,
            "input": input_body,
        }

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        instructions: str | None = None,
    ) -> bytes:
        if not self.api_key:
            raise TTSProviderError("DASHSCOPE_API_KEY 未配置")
        if not text or not text.strip():
            raise TTSProviderError("合成文本不能为空")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.endpoint,
                headers=self._headers(),
                json=self._build_payload(text, voice, instructions),
            )
            if response.status_code >= 400:
                raise TTSProviderError(f"百炼 TTS 请求失败: {self._extract_api_error(response)}")

            payload = response.json()
            audio = (payload.get("output") or {}).get("audio") or {}

            audio_bytes = b""
            if audio.get("data"):
                try:
                    audio_bytes = base64.b64decode(audio["data"])
                except Exception as exc:
                    raise TTSProviderError(f"百炼 TTS 音频解码失败: {exc}") from exc
            elif audio.get("url"):
                audio_bytes = await self._download_audio(client, audio["url"])

            if not audio_bytes:
                raise TTSProviderError(f"百炼 TTS 返回异常（无音频数据）: {payload}")

            if not _is_probably_audio(audio_bytes):
                raise TTSProviderError("百炼 TTS 返回内容不是有效音频（RIFF/mp3 magic 校验失败）")

            return audio_bytes

    async def _download_audio(self, client: httpx.AsyncClient, url: str) -> bytes:
        audio_response = await client.get(url)
        if audio_response.status_code >= 400:
            raise TTSProviderError(f"百炼 TTS 音频下载失败: HTTP {audio_response.status_code}")
        return audio_response.content

    def _extract_api_error(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except Exception:
            return response.text

        error = payload.get("error") or {}
        if isinstance(error, dict):
            message = error.get("message") or error.get("code")
            if message:
                return str(message)
        return str(payload)[:500]


class TTSService:
    """按配置路由到具体 TTS Provider（当前 bailian）。"""

    def __init__(self):
        self.provider: BailianTTSProvider | None = None
        self._init_provider()

    def _init_provider(self):
        provider_name = (settings.TTS_PROVIDER or "bailian").lower()
        try:
            if provider_name == "bailian":
                if settings.DASHSCOPE_API_KEY and settings.DASHSCOPE_API_KEY.strip():
                    self.provider = BailianTTSProvider()
        except Exception as e:
            logger.error(f"Failed to initialize TTS provider {provider_name}: {e}")
            self.provider = None

        if self.provider is not None:
            logger.info(f"TTS provider initialized: {provider_name}")
        else:
            logger.warning(f"TTS provider unavailable: {provider_name}")

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        instructions: str | None = None,
    ) -> dict[str, Any]:
        """合成语音，返回 {"audio": bytes, "format": str, "error": bool|None}。"""
        if self.provider is None:
            return {
                "audio": b"",
                "format": settings.QWEN_TTS_AUDIO_FORMAT,
                "error": "TTS Service Unavailable (Provider Not Initialized)",
            }

        try:
            audio_bytes = await self.provider.synthesize(text, voice=voice, instructions=instructions)
            return {"audio": audio_bytes, "format": self.provider.audio_format, "error": None}
        except TTSProviderError as e:
            logger.warning(f"TTS synthesize failed: {e}")
            return {"audio": b"", "format": settings.QWEN_TTS_AUDIO_FORMAT, "error": str(e)}
        except Exception as e:
            logger.error(f"TTS synthesize unexpected error: {e}")
            return {
                "audio": b"",
                "format": settings.QWEN_TTS_AUDIO_FORMAT,
                "error": "Speech synthesis failed. Please try again later.",
            }


tts_service = TTSService()
