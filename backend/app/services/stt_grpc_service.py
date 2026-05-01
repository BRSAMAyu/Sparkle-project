from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from loguru import logger

_GEN_ROOT = Path(__file__).resolve().parents[1] / "gen"
for _path in (_GEN_ROOT, _GEN_ROOT / "stt" / "v1"):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.append(_path_str)

from app.gen import stt_service_pb2, stt_service_pb2_grpc
from app.services.stt_service import STTService, stt_service


class STTGrpcServiceImpl(stt_service_pb2_grpc.STTServiceServicer):
    """gRPC adapter for the production STT service."""

    def __init__(self, service: STTService | None = None):
        self.service = service or stt_service

    async def TranscribeAudio(self, request, context):
        start = time.perf_counter()
        suffix = self._safe_suffix(request.filename or request.format)
        temp_path = ""

        try:
            if not request.audio_data:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("audio_data is required")
                return self._transcribe_error("STT_ERROR_CODE_INVALID_SAMPLE_RATE", "audio_data is required")

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(request.audio_data)
                temp_path = tmp.name

            result = await self.service.transcribe_file(temp_path, language=request.language or None)
            if result.get("error"):
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                context.set_details("STT provider failed")
                return self._transcribe_error(
                    "STT_ERROR_CODE_RECOGNITION_FAILED",
                    "STT provider failed",
                    processing_time_ms=self._elapsed_ms(start),
                    file_size_bytes=len(request.audio_data),
                    sample_rate=request.sample_rate,
                )

            text = str(result.get("text") or "")
            enhanced = ""
            if request.enable_enhancement and text:
                enhanced = await self.service.enhance_transcript(text)

            return stt_service_pb2.TranscribeResponse(
                text=text,
                confidence=1.0 if text else 0.0,
                detected_language=request.language,
                enhanced_text=enhanced,
                metadata=stt_service_pb2.TranscriptionMetadata(
                    provider=self._provider_name(),
                    model="configured",
                    processing_time_ms=self._elapsed_ms(start),
                    file_size_bytes=len(request.audio_data),
                    sample_rate=request.sample_rate,
                ),
            )
        except Exception:
            logger.exception("gRPC TranscribeAudio failed")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("STT transcription failed")
            return self._transcribe_error(
                "STT_ERROR_CODE_INTERNAL_ERROR",
                "STT transcription failed",
                processing_time_ms=self._elapsed_ms(start),
                file_size_bytes=len(request.audio_data),
                sample_rate=request.sample_rate,
            )
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    logger.warning("Failed to remove temporary STT upload: {}", temp_path)

    async def EnhanceTranscript(self, request, context):
        start = time.perf_counter()
        try:
            enhanced = await self.service.enhance_transcript(request.text)
            return stt_service_pb2.EnhanceResponse(
                enhanced_text=enhanced,
                original_text=request.text,
                changes_count=1 if enhanced != request.text else 0,
                processing_time_ms=self._elapsed_ms(start),
            )
        except Exception:
            logger.exception("gRPC EnhanceTranscript failed")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Transcript enhancement failed")
            return stt_service_pb2.EnhanceResponse(original_text=request.text)

    async def StreamSpeechToText(self, request_iterator, context):
        provider = self.service.stream_provider or self.service.provider
        if provider is None:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("STT stream provider unavailable")
            yield self._stream_error("STT_ERROR_CODE_PROVIDER_UNAVAILABLE", "STT stream provider unavailable")
            return

        session_id = ""

        async def audio_chunks():
            nonlocal session_id
            async for request in request_iterator:
                session_id = request.session_id or session_id
                if request.data:
                    yield request.data
                if request.end_of_stream:
                    break

        sequence = 0
        try:
            async for text in provider.transcribe_stream(audio_chunks()):
                sequence += 1
                timestamp = Timestamp()
                timestamp.GetCurrentTime()
                yield stt_service_pb2.TranscriptionResult(
                    text=text,
                    is_final=False,
                    confidence=1.0 if text else 0.0,
                    sequence=sequence,
                    timestamp=timestamp,
                    session_id=session_id,
                )
        except Exception:
            logger.exception("gRPC StreamSpeechToText failed")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("STT stream failed")
            yield self._stream_error("STT_ERROR_CODE_INTERNAL_ERROR", "STT stream failed", session_id=session_id)

    @staticmethod
    def _safe_suffix(filename_or_format: str) -> str:
        value = (filename_or_format or "").lower().strip()
        _, ext = os.path.splitext(value)
        if ext and ext.replace(".", "").isalnum() and len(ext) <= 8:
            return ext
        if value.isalnum() and len(value) <= 8:
            return f".{value}"
        return ".audio"

    def _provider_name(self) -> str:
        provider = self.service.provider or self.service.backup_provider or self.service.stream_provider
        return provider.__class__.__name__ if provider is not None else "none"

    @staticmethod
    def _elapsed_ms(start: float) -> int:
        return int((time.perf_counter() - start) * 1000)

    @staticmethod
    def _transcribe_error(
        code: str,
        message: str,
        *,
        processing_time_ms: int = 0,
        file_size_bytes: int = 0,
        sample_rate: int = 0,
    ):
        return stt_service_pb2.TranscribeResponse(
            confidence=0.0,
            metadata=stt_service_pb2.TranscriptionMetadata(
                processing_time_ms=processing_time_ms,
                file_size_bytes=file_size_bytes,
                sample_rate=sample_rate,
            ),
            error=stt_service_pb2.TranscriptionError(
                code=code,
                message=message,
                recoverable=False,
            ),
        )

    @staticmethod
    def _stream_error(code: str, message: str, *, session_id: str = ""):
        timestamp = Timestamp()
        timestamp.GetCurrentTime()
        return stt_service_pb2.TranscriptionResult(
            is_final=True,
            timestamp=timestamp,
            session_id=session_id,
            error=stt_service_pb2.TranscriptionError(
                code=code,
                message=message,
                recoverable=False,
            ),
        )
