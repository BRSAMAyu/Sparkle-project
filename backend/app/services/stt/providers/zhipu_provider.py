"""
智谱 ASR Provider.

使用 GLM-ASR-2512 文件转写接口，并对现有 PCM WebSocket 流做分段封装。
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import shutil
import tempfile
import uuid
import wave
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
from loguru import logger

from app.config import settings
from app.services.stt.providers.base import STTProvider


class ZhipuProvider(STTProvider):
    """智谱 GLM-ASR-2512 Provider。"""

    SUPPORTED_EXTENSIONS = {".wav", ".mp3"}

    def __init__(self):
        self.api_key = settings.ZHIPU_API_KEY
        self.base_url = settings.ZHIPU_ASR_BASE_URL.rstrip("/")
        self.model = settings.ZHIPU_ASR_MODEL
        self.sample_rate = settings.ZHIPU_ASR_SAMPLE_RATE
        self.stream_segment_seconds = max(1, settings.ZHIPU_ASR_STREAM_SEGMENT_SECONDS)
        self.max_audio_seconds = settings.ZHIPU_ASR_MAX_AUDIO_SECONDS
        self.max_file_size_bytes = settings.ZHIPU_ASR_MAX_FILE_SIZE_BYTES
        self.timeout = httpx.Timeout(settings.ZHIPU_ASR_REQUEST_TIMEOUT_SECONDS)
        self.endpoint = f"{self.base_url}/audio/transcriptions"

        if not self.api_key:
            logger.warning("智谱 ASR API Key 未配置，ZhipuProvider 将无法工作")

    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str | None = None,
        sample_rate: int | None = None,
    ) -> AsyncGenerator[str, None]:
        del language
        self._ensure_api_key()

        target_sample_rate = sample_rate or self.sample_rate
        bytes_per_second = target_sample_rate * 2
        pcm_buffer = bytearray()
        last_emitted = ""
        next_flush_at = self.stream_segment_seconds

        async for audio_chunk in audio_stream:
            if not audio_chunk:
                continue

            pcm_buffer.extend(audio_chunk)
            current_duration = len(pcm_buffer) / bytes_per_second
            if current_duration > self.max_audio_seconds:
                raise RuntimeError(f"智谱 ASR 最长支持 {self.max_audio_seconds} 秒音频")

            if current_duration >= next_flush_at:
                text = await self._transcribe_pcm_buffer(bytes(pcm_buffer), target_sample_rate)
                if text and text != last_emitted:
                    last_emitted = text
                    yield text
                next_flush_at += self.stream_segment_seconds

        if pcm_buffer:
            text = await self._transcribe_pcm_buffer(bytes(pcm_buffer), target_sample_rate)
            if text and text != last_emitted:
                yield text

    async def transcribe_file(
        self,
        file_path: str,
        language: str | None = None,
    ) -> str:
        del language
        self._ensure_api_key()

        if not os.path.exists(file_path):
            raise RuntimeError("文件不存在")

        prepared_path, cleanup_dir = await self._prepare_audio_file(file_path)
        try:
            ext = Path(prepared_path).suffix.lower()
            content_type = "audio/mpeg" if ext == ".mp3" else "audio/wav"
            audio_bytes = await asyncio.to_thread(Path(prepared_path).read_bytes)
            return await self._transcribe_audio_bytes(
                audio_bytes=audio_bytes,
                filename=Path(prepared_path).name,
                content_type=content_type,
            )
        finally:
            if cleanup_dir:
                shutil.rmtree(cleanup_dir, ignore_errors=True)

    async def close(self) -> None:
        return None

    def _ensure_api_key(self) -> None:
        if not self.api_key:
            raise RuntimeError("智谱 ASR API Key 未配置")

    async def _transcribe_pcm_buffer(self, pcm_bytes: bytes, sample_rate: int) -> str:
        wav_bytes = self._build_wav_bytes(pcm_bytes, sample_rate)
        return await self._transcribe_audio_bytes(
            audio_bytes=wav_bytes,
            filename="stream.wav",
            content_type="audio/wav",
        )

    async def _transcribe_audio_bytes(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        if len(audio_bytes) > self.max_file_size_bytes:
            raise RuntimeError("音频文件超过智谱 ASR 25MB 限制")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {
            "model": self.model,
            "stream": "false",
            "request_id": uuid.uuid4().hex,
        }
        files = {
            "file": (filename, audio_bytes, content_type),
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.endpoint,
                headers=headers,
                data=data,
                files=files,
            )

        if response.status_code >= 400:
            message = self._extract_api_error(response)
            raise RuntimeError(f"智谱 ASR 请求失败: {message}")

        payload = response.json()
        text = payload.get("text")
        if not isinstance(text, str):
            raise RuntimeError(f"智谱 ASR 返回异常: {payload}")
        return text.strip()

    async def _prepare_audio_file(self, file_path: str) -> tuple[str, str | None]:
        ext = Path(file_path).suffix.lower()
        if ext in self.SUPPORTED_EXTENSIONS:
            await self._validate_audio_file(file_path)
            return file_path, None

        temp_dir = tempfile.mkdtemp(prefix="zhipu-asr-")
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
        await self._validate_audio_file(converted_path)
        return converted_path, temp_dir

    async def _validate_audio_file(self, file_path: str) -> None:
        file_size = os.path.getsize(file_path)
        if file_size > self.max_file_size_bytes:
            raise RuntimeError("音频文件超过智谱 ASR 25MB 限制")

        duration = await self._detect_duration(file_path)
        if duration > self.max_audio_seconds:
            raise RuntimeError(f"智谱 ASR 最长支持 {self.max_audio_seconds} 秒音频")

    async def _detect_duration(self, file_path: str) -> float:
        if file_path.lower().endswith(".wav"):
            return await asyncio.to_thread(self._probe_wav_duration, file_path)
        return await self._probe_duration(file_path)

    def _probe_wav_duration(self, file_path: str) -> float:
        with wave.open(file_path, "rb") as wav_file:
            frame_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
        if frame_rate <= 0:
            raise RuntimeError(f"无法识别音频时长: {file_path}")
        return frame_count / frame_rate

    async def _probe_duration(self, file_path: str) -> float:
        stdout = await self._run_command(
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            file_path,
        )
        try:
            payload = json.loads(stdout)
            duration = float(payload["format"]["duration"])
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"无法识别音频时长: {file_path}") from exc
        return duration

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

    def _build_wav_bytes(self, pcm_bytes: bytes, sample_rate: int) -> bytes:
        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_bytes)
            return buffer.getvalue()

    def _extract_api_error(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except json.JSONDecodeError:
            return response.text

        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message") or error.get("code")
            if message:
                return str(message)
        return json.dumps(payload, ensure_ascii=False)
