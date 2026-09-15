"""
STT (Speech to Text) API
语音转文字服务
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile, WebSocket, status

from app.api.deps import get_current_user
from app.config import settings
from app.core.security import decode_token
from app.services.stt_service import stt_service
from app.utils.helpers import save_upload_file

router = APIRouter()


def _stt_max_upload_size() -> int:
    provider_name = (settings.STT_PROVIDER or "zhipu").lower()
    if provider_name in {"zhipu", "xunfei"}:
        return min(settings.MAX_UPLOAD_SIZE, settings.ZHIPU_ASR_MAX_FILE_SIZE_BYTES)
    return settings.MAX_UPLOAD_SIZE


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...), language: str = Form(None), current_user: object = Depends(get_current_user)
):
    """
    Upload audio file for transcription.
    """
    # Save uploaded file
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] if file.filename else ".tmp"
    temp_path = str(Path(settings.UPLOAD_DIR).joinpath(f"{file_id}{ext}").resolve())

    try:
        await save_upload_file(
            file,
            temp_path,
            max_size=_stt_max_upload_size(),
            allowed_extensions={".wav", ".mp3", ".m4a", ".mp4", ".webm", ".ogg"},
            allowed_content_types={
                "audio/wav",
                "audio/x-wav",
                "audio/mpeg",
                "audio/mp4",
                "audio/webm",
                "audio/ogg",
                "audio/x-m4a",
            },
        )

        # Transcribe
        result = await stt_service.transcribe_file(temp_path, language=language)

        # Post-process (Enhance)
        if not result["error"] and result["text"]:
            enhanced = await stt_service.enhance_transcript(result["text"])
            result["enhanced_text"] = enhanced

        return result

    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket for audio streaming.
    Client sends binary audio chunks.
    Server returns JSON: {"type": "transcription", "text": "...", "is_final": bool}
    """
    token = _extract_ws_token(websocket)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        await decode_token(token, expected_type="access")
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await stt_service.handle_websocket_stream(websocket)


def _extract_ws_token(websocket: WebSocket) -> str | None:
    auth_header = websocket.headers.get("authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()

    protocol = websocket.headers.get("sec-websocket-protocol")
    if protocol:
        for part in protocol.split(","):
            candidate = part.strip()
            lower = candidate.lower()
            if lower.startswith("bearer "):
                return candidate[7:].strip()
            if lower.startswith("token="):
                return candidate[6:].strip()
            if lower.startswith("token:"):
                return candidate[6:].strip()

    if settings.WS_ALLOW_QUERY_TOKEN:
        return websocket.query_params.get("token")
    return None
