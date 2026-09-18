"""
TTS (Text to Speech) API
文字转语音服务（阿里云百炼 qwen3-tts-instruct-flash）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.services.tts_service import tts_service

router = APIRouter()


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="待合成文本")
    voice: str | None = Field(None, max_length=64, description="音色（默认取 QWEN_TTS_VOICE）")
    instructions: str | None = Field(None, max_length=500, description="语音风格指令，仅 qwen3-tts-instruct 系列支持")


@router.post("/synthesize")
async def synthesize_speech(
    request: SynthesizeRequest,
    current_user: object = Depends(get_current_user),
):
    """
    Synthesize Chinese/multilingual speech to wav audio bytes.
    """
    result = await tts_service.synthesize(
        request.text,
        voice=request.voice,
        instructions=request.instructions,
    )

    if result.get("error") or not result.get("audio"):
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(result.get("error") or "TTS synthesis failed"),
        )

    media_type = "audio/mpeg" if result.get("format") == "mp3" else "audio/wav"
    return Response(content=result["audio"], media_type=media_type)
