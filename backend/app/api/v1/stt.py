"""
STT (Speech to Text) API
语音转文字服务
"""
from typing import Any
from fastapi import APIRouter, UploadFile, File, WebSocket, Form, Depends
from app.services.stt_service import stt_service
import shutil
import os
import uuid
from app.config import settings

router = APIRouter()

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form(None)
):
    """
    Upload audio file for transcription.
    """
    # Save uploaded file
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] if file.filename else ".tmp"
    temp_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
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
    await stt_service.handle_websocket_stream(websocket)
