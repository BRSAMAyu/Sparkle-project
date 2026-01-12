"""
File processing API
文件处理 API
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, AnyUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.celery_tasks import process_stored_file
from app.db.session import get_db
from app.models.file_storage import StoredFile


router = APIRouter()


async def verify_internal_token(x_internal_token: Optional[str] = Header(None)) -> None:
    if settings.INTERNAL_API_KEY and x_internal_token != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid internal token")


class FileProcessRequest(BaseModel):
    file_id: UUID
    user_id: UUID
    download_url: AnyUrl
    file_name: str
    mime_type: str
    thumbnail_upload_url: Optional[AnyUrl] = None


@router.post("/files/process", summary="Trigger file processing")
async def process_file(
    payload: FileProcessRequest,
    _: None = Depends(verify_internal_token),
):
    task = process_stored_file.delay(
        file_id=str(payload.file_id),
        user_id=str(payload.user_id),
        download_url=str(payload.download_url),
        file_name=payload.file_name,
        mime_type=payload.mime_type,
        thumbnail_upload_url=str(payload.thumbnail_upload_url) if payload.thumbnail_upload_url else None,
    )
    return {"status": "queued", "task_id": task.id}


@router.get("/files/{file_id}/status", summary="Get file processing status")
async def get_file_status(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_internal_token),
):
    record = await db.get(StoredFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "file_id": str(record.id),
        "status": record.status,
        "error_message": record.error_message,
        "updated_at": record.updated_at,
    }
