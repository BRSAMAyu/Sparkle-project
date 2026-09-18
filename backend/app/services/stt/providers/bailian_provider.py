"""
阿里云百炼 Qwen ASR Provider（qwen3-asr-flash-realtime）。

走 DashScope Realtime WebSocket 协议（manual commit 模式）：
  wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen3-asr-flash-realtime
  - session.update  配置 pcm/16k + turn_detection=null
  - input_audio_buffer.append 推送 base64 PCM
  - input_audio_buffer.commit 触发转写
  - session.finish   结束会话
  - conversation.item.input_audio_transcription.completed 携带最终文本

流式识别沿用既有"分段转写"模式（与 ZhipuProvider 一致）：每满
QWEN_ASR_STREAM_SEGMENT_SECONDS 秒 PCM 起一个会话转写并去重增量返回；
文件转写则将整段音频（≤ QWEN_ASR_MAX_AUDIO_SECONDS）单会话转写。
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import tempfile
import uuid
import wave
from collections.abc import AsyncGenerator
from pathlib import Path

import websockets
from loguru import logger

from app.config import settings
from app.services.stt.providers.base import STTProvider


class BailianProvider(STTProvider):
    """百炼 Qwen3-ASR-Flash-Realtime Provider。"""

    _PCM_CHUNK_BYTES = 3200  # ~0.1s @16kHz 16bit mono
    _SESSION_OPEN_TIMEOUT_SECONDS = 10.0
    _FIRST_MESSAGE_TIMEOUT_SECONDS = 15.0

    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.ws_base_url = settings.QWEN_ASR_WS_URL.rstrip("/")
        self.model = settings.QWEN_ASR_MODEL
        self.sample_rate = settings.QWEN_ASR_SAMPLE_RATE
        self.stream_segment_seconds = max(1, settings.QWEN_ASR_STREAM_SEGMENT_SECONDS)
        self.max_audio_seconds = settings.QWEN_ASR_MAX_AUDIO_SECONDS
        self.language = settings.QWEN_ASR_LANGUAGE
        self.timeout = float(settings.QWEN_ASR_REQUEST_TIMEOUT_SECONDS)

        if not self.api_key:
            logger.warning("DASHSCOPE_API_KEY 未配置，BailianProvider 将无法工作")

    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str | None = None,
        sample_rate: int | None = None,
    ) -> AsyncGenerator[str, None]:
        self._ensure_api_key()

        del sample_rate  # 固定按 settings.QWEN_ASR_SAMPLE_RATE 分段计长（移动端为 16k PCM）
        segment_bytes = self.sample_rate * 2 * self.stream_segment_seconds
        pcm_buffer = bytearray()
        last_emitted = ""

        async for audio_chunk in audio_stream:
            if not audio_chunk:
                continue

            pcm_buffer.extend(audio_chunk)
            if len(pcm_buffer) >= segment_bytes:
                text = await self._transcribe_pcm_segment(bytes(pcm_buffer), language)
                if text and text != last_emitted:
                    last_emitted = text
                    yield text
                pcm_buffer.clear()

        if pcm_buffer:
            text = await self._transcribe_pcm_segment(bytes(pcm_buffer), language)
            if text and text != last_emitted:
                yield text

    async def transcribe_file(
        self,
        file_path: str,
        language: str | None = None,
    ) -> str:
        self._ensure_api_key()

        if not os.path.exists(file_path):
            raise RuntimeError("文件不存在")

        prepared_path, cleanup_dir, detected_sample_rate = await self._prepare_audio_file(file_path)
        try:
            pcm_bytes = await asyncio.to_thread(self._read_wav_pcm, prepared_path)
            duration = len(pcm_bytes) / 2 / (detected_sample_rate or self.sample_rate)
            if duration > self.max_audio_seconds:
                raise RuntimeError(f"百炼 ASR 单次会话最长支持 {self.max_audio_seconds} 秒音频")

            return await self._transcribe_pcm_segment(pcm_bytes, language, detected_sample_rate)
        finally:
            if cleanup_dir:
                shutil.rmtree(cleanup_dir, ignore_errors=True)

    async def close(self) -> None:
        return None

    def _ensure_api_key(self) -> None:
        if not self.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY 未配置")

    def _normalize_language(self, language: str | None) -> str | None:
        target = (language or self.language or "").strip()
        if not target:
            return None
        lowered = target.lower()
        if lowered.startswith("zh"):
            return "zh"
        if lowered.startswith("en"):
            return "en"
        return lowered.split("-")[0] or None

    def _build_ws_url(self) -> str:
        return f"{self.ws_base_url}?model={self.model}"

    def _build_ws_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

    def _session_update_event(self, language: str | None) -> dict:
        session: dict[str, object] = {
            "modalities": ["text"],
            "input_audio_format": "pcm",
            "sample_rate": self.sample_rate,
            "turn_detection": None,  # manual commit 模式，转写由 commit 显式触发
        }
        normalized = self._normalize_language(language)
        if normalized:
            session["input_audio_transcription"] = {"language": normalized}
        return {
            "event_id": f"event_{uuid.uuid4().hex}",
            "type": "session.update",
            "session": session,
        }

    def _append_event(self, pcm_chunk: bytes) -> dict:
        return {
            "event_id": f"event_{uuid.uuid4().hex}",
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(pcm_chunk).decode("utf-8"),
        }

    def _commit_event(self) -> dict:
        return {
            "event_id": f"event_{uuid.uuid4().hex}",
            "type": "input_audio_buffer.commit",
        }

    def _finish_event(self) -> dict:
        return {
            "event_id": f"event_{uuid.uuid4().hex}",
            "type": "session.finish",
        }

    async def _transcribe_pcm_segment(
        self,
        pcm_bytes: bytes,
        language: str | None = None,
        sample_rate: int | None = None,
    ) -> str:
        if not pcm_bytes:
            return ""

        original_sample_rate = self.sample_rate
        if sample_rate and sample_rate != self.sample_rate:
            # 文件场景带真实采样率：临时切换会话采样率，避免重采样
            self.sample_rate = sample_rate
        try:
            async with websockets.connect(
                self._build_ws_url(),
                additional_headers=self._build_ws_headers(),
                max_size=2**22,
                open_timeout=self._SESSION_OPEN_TIMEOUT_SECONDS,
                close_timeout=2,
            ) as websocket:
                await websocket.send(json.dumps(self._session_update_event(language)))

                for offset in range(0, len(pcm_bytes), self._PCM_CHUNK_BYTES):
                    chunk = pcm_bytes[offset : offset + self._PCM_CHUNK_BYTES]
                    await websocket.send(json.dumps(self._append_event(chunk)))

                await websocket.send(json.dumps(self._commit_event()))
                await websocket.send(json.dumps(self._finish_event()))

                return await self._collect_transcript(websocket)
        finally:
            self.sample_rate = original_sample_rate

    async def _collect_transcript(self, websocket) -> str:
        deadline = asyncio.get_event_loop().time() + self.timeout
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise RuntimeError("百炼 ASR 响应超时")
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
            except TimeoutError:
                raise RuntimeError("百炼 ASR 响应超时") from None
            except websockets.ConnectionClosed:
                raise RuntimeError("百炼 ASR 连接被服务端关闭") from None

            try:
                data = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue

            event_type = data.get("type")
            if event_type == "conversation.item.input_audio_transcription.completed":
                transcript = str(data.get("transcript") or "").strip()
                logger.debug(f"百炼 ASR 转写完成: {transcript[:80]}")
                return transcript
            if event_type == "conversation.item.input_audio_transcription.text":
                # 部分结果（manual 模式下少见）：仅日志留痕，等 completed
                continue
            if event_type == "error":
                error = data.get("error") or {}
                message = error.get("message") if isinstance(error, dict) else str(error)
                raise RuntimeError(f"百炼 ASR 请求失败: {message or data}")
            if event_type == "session.finished":
                raise RuntimeError("百炼 ASR 会话结束但未返回转写结果")

    async def _prepare_audio_file(self, file_path: str) -> tuple[str, str | None, int | None]:
        """统一转成 16k mono wav；返回 (路径, 清理目录, 实际采样率)。"""
        ext = Path(file_path).suffix.lower()
        if ext == ".wav":
            detected = await asyncio.to_thread(self._probe_wav_sample_rate, file_path)
            return file_path, None, detected

        temp_dir = tempfile.mkdtemp(prefix="bailian-asr-")
        converted_path = os.path.join(temp_dir, "converted.wav")
        await self._run_command(
            "ffmpeg",
            "-y",
            "-i",
            file_path,
            "-ac",
            "1",
            "-ar",
            str(self.sample_rate),
            converted_path,
        )
        return converted_path, temp_dir, self.sample_rate

    def _probe_wav_sample_rate(self, file_path: str) -> int:
        with wave.open(file_path, "rb") as wav_file:
            rate = wav_file.getframerate()
        if rate <= 0:
            raise RuntimeError(f"无法识别音频采样率: {file_path}")
        return rate

    def _read_wav_pcm(self, file_path: str) -> bytes:
        with wave.open(file_path, "rb") as wav_file:
            if wav_file.getsampwidth() != 2 or wav_file.getnchannels() != 1:
                raise RuntimeError("百炼 ASR 仅支持 16bit 单声道 PCM WAV，请先转码")
            return wav_file.readframes(wav_file.getnframes())

    async def _run_command(self, *command: str) -> str:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            message = stderr.decode("utf-8", errors="ignore").strip() or stdout.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(message or f"命令执行失败: {' '.join(command)}")
        return stdout.decode("utf-8", errors="ignore")
