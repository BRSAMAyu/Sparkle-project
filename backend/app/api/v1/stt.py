"""
STT (Speech to Text) API
语音转文字服务
"""
from typing import Any
from fastapi import APIRouter, UploadFile, File, WebSocket, Form, Depends, HTTPException, status
from app.services.stt_service import stt_service
import os
import uuid
from app.config import settings
from app.api.deps import get_current_user
from app.core.security import decode_token
from app.utils.helpers import save_upload_file

router = APIRouter()

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form(None),
    current_user: object = Depends(get_current_user)
):
    """
    Upload audio file for transcription.
    """
    # Save uploaded file
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] if file.filename else ".tmp"
    temp_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")
    
    try:
        await save_upload_file(
            file,
            temp_path,
            max_size=settings.MAX_UPLOAD_SIZE,
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
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        decode_token(token, expected_type="access")
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await stt_service.handle_websocket_stream(websocket)
