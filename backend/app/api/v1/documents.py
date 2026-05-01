"""
Public document upload API.
"""
from __future__ import annotations

import json
import os
from pathlib import PurePath
from uuid import UUID, uuid4

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.core.cache import cache_service
from app.core.celery_tasks import process_stored_file
from app.models.background_task import BackgroundTask, BackgroundTaskStatus, BackgroundTaskType
from app.models.community import GroupRole
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode
from app.models.user import User
from app.services.document_service import document_service
from app.services.document_upload_storage import document_upload_storage
from app.services.group_file_service import GroupFileService

router = APIRouter()

DOCUMENT_UPLOAD_MIME_TYPES = {
    "application/pdf": {".pdf"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": {".pptx"},
    "text/markdown": {".md", ".markdown"},
    "text/plain": {".md", ".markdown", ".txt"},
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/gif": {".gif"},
    "image/webp": {".webp"},
}
DEFAULT_EXT_BY_MIME = {mime_type: next(iter(exts)) for mime_type, exts in DOCUMENT_UPLOAD_MIME_TYPES.items()}


class DocumentUploadRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=3, max_length=150)
    file_size: int = Field(..., gt=0)
    visibility: str | None = Field(default="private", max_length=32)
    group_id: UUID | None = None

    @field_validator("mime_type")
    @classmethod
    def normalize_mime_type(cls, value: str) -> str:
        return value.split(";", 1)[0].strip().lower()

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str | None) -> str:
        visibility = (value or "private").strip().lower()
        if visibility not in {"private", "friends", "group", "public"}:
            raise ValueError("visibility must be private, friends, group, or public")
        return visibility


class DocumentUploadResponse(BaseModel):
    file_id: UUID
    presigned_url: str
    expires_in: int


class ConfirmUploadResponse(BaseModel):
    job_id: str
    estimated_seconds: int


class DocumentStatusResponse(BaseModel):
    status: str
    progress_percent: int
    stage: str
    nodes_found: int | None = None
    drafts_pending: int | None = None
    error: str | None = None


class CitationFeedbackRequest(BaseModel):
    file_id: UUID
    chunk_id: str | None = Field(default=None, min_length=1, max_length=128)
    query_type: str | None = Field(default=None, max_length=64)
    rating: int
    conversation_id: str | None = Field(default=None, max_length=128)
    context: dict[str, object] | None = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: int) -> int:
        if value not in {-1, 1}:
            raise ValueError("rating must be 1 or -1")
        return value


class CitationFeedbackResponse(BaseModel):
    accepted: bool
    feedback_source: str


def _allowed_mime_types() -> set[str]:
    configured = {
        item.strip().lower()
        for item in (settings.FILE_ALLOWED_MIME_TYPES or "").split(",")
        if item.strip()
    }
    return configured & set(DOCUMENT_UPLOAD_MIME_TYPES) or set(DOCUMENT_UPLOAD_MIME_TYPES)


def _clean_filename(filename: str) -> str:
    cleaned = PurePath(filename.strip()).name
    if cleaned in {"", ".", ".."}:
        return "document"
    return cleaned[:255]


def _extension_for_upload(filename: str, mime_type: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = DOCUMENT_UPLOAD_MIME_TYPES.get(mime_type)
    if not allowed_exts:
        raise HTTPException(status_code=400, detail="Unsupported mime_type")
    if ext:
        if ext not in allowed_exts:
            raise HTTPException(status_code=400, detail="mime_type does not match filename extension")
        return ext
    return DEFAULT_EXT_BY_MIME[mime_type]


def _validate_declared_file(payload: DocumentUploadRequest) -> tuple[str, str]:
    if payload.file_size > settings.FILE_MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="file_size exceeds limit")
    if payload.mime_type not in _allowed_mime_types():
        raise HTTPException(status_code=400, detail="Unsupported mime_type")
    filename = _clean_filename(payload.filename)
    ext = _extension_for_upload(filename, payload.mime_type)
    return filename, ext


def _magic_bytes_match(header: bytes, mime_type: str) -> bool:
    if mime_type == "application/pdf":
        return header.startswith(b"%PDF-")
    if mime_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }:
        return header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06") or header.startswith(b"PK\x07\x08")
    if mime_type == "image/png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/jpeg":
        return header.startswith(b"\xff\xd8\xff")
    if mime_type == "image/gif":
        return header.startswith((b"GIF87a", b"GIF89a"))
    if mime_type == "image/webp":
        return len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    if mime_type in {"text/markdown", "text/plain"}:
        if b"\x00" in header:
            return False
        try:
            header.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    return False


def _document_stage(record_status: str, progress_percent: int) -> tuple[str, str]:
    normalized = (record_status or "").lower()
    if normalized == "failed":
        return "failed", "failed"
    if normalized in {"processed", "done"}:
        return "done", "done"
    if normalized in {"uploading", "uploaded", "queued"}:
        return "queued", "queued"
    if progress_percent < 25:
        return "extracting", "extracting"
    if progress_percent < 70:
        return "embedding", "embedding"
    return "building_nodes", "building_nodes"


async def _latest_task(db: AsyncSession, file_id: UUID, user_id: UUID) -> BackgroundTask | None:
    result = await db.execute(
        select(BackgroundTask)
        .where(
            BackgroundTask.user_id == user_id,
            BackgroundTask.related_entity_id == file_id,
            BackgroundTask.related_entity_type == "stored_file",
            BackgroundTask.task_type == BackgroundTaskType.DATA_SYNC,
            BackgroundTask.not_deleted_filter(),
        )
        .order_by(desc(BackgroundTask.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _publish_status(
    *,
    file_id: UUID,
    user_id: UUID,
    status_value: str,
    progress_percent: int,
    stage: str,
    job_id: str | None = None,
    error: str | None = None,
) -> None:
    if not cache_service.redis:
        await cache_service.init_redis()
    if not cache_service.redis:
        return
    payload = {
        "type": "file_status",
        "file_id": str(file_id),
        "user_id": str(user_id),
        "status": status_value,
        "progress": progress_percent,
        "progress_percent": progress_percent,
        "stage": stage,
    }
    if job_id:
        payload["job_id"] = job_id
    if error:
        payload["error"] = error[:200]

    await cache_service.redis.publish("file_status", json.dumps(payload, ensure_ascii=True))


@router.post("/upload", response_model=DocumentUploadResponse, summary="Prepare document upload")
async def prepare_document_upload(
    payload: DocumentUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filename, ext = _validate_declared_file(payload)
    file_id = uuid4()
    visibility = (payload.visibility or ("group" if payload.group_id else "private")).strip().lower()
    if payload.group_id and visibility not in {"group", "public"}:
        raise HTTPException(status_code=422, detail="group uploads require visibility group or public")
    object_key = f"{current_user.id}/{file_id}/original{ext}"

    record = StoredFile(
        id=file_id,
        user_id=current_user.id,
        file_name=filename,
        mime_type=payload.mime_type,
        file_size=payload.file_size,
        bucket=document_upload_storage.bucket,
        object_key=object_key,
        status="uploading",
        visibility=visibility,
        retention_policy="standard",
    )
    db.add(record)
    await db.flush()

    if payload.group_id:
        try:
            await GroupFileService.share_file(
                db,
                group_id=payload.group_id,
                user_id=current_user.id,
                file_id=file_id,
                category=None,
                description=None,
                tags=[],
                view_role=GroupRole.MEMBER,
                download_role=GroupRole.MEMBER,
                manage_role=GroupRole.ADMIN,
            )
        except ValueError as exc:
            await db.rollback()
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    await db.commit()

    presigned_url = document_upload_storage.create_presigned_put_url(
        object_key=object_key,
        mime_type=payload.mime_type,
        file_size=payload.file_size,
    )
    return DocumentUploadResponse(
        file_id=file_id,
        presigned_url=presigned_url,
        expires_in=document_upload_storage.expires_in,
    )


@router.post("/{file_id}/confirm-upload", response_model=ConfirmUploadResponse, summary="Confirm document upload")
async def confirm_document_upload(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(StoredFile, file_id)
    if not record or record.user_id != current_user.id or record.is_deleted:
        raise HTTPException(status_code=404, detail="File not found")
    if record.status not in {"uploading", "uploaded", "queued", "failed"}:
        raise HTTPException(status_code=409, detail="File is already processing or processed")

    try:
        metadata = document_upload_storage.head_object(object_key=record.object_key)
        actual_size = int(metadata.get("ContentLength") or 0)
        header = document_upload_storage.read_header(object_key=record.object_key)
    except ClientError as exc:
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_code == 404:
            raise HTTPException(status_code=400, detail="Uploaded object not found") from exc
        raise HTTPException(status_code=502, detail="Failed to validate uploaded object") from exc

    if actual_size <= 0:
        raise HTTPException(status_code=400, detail="Uploaded object is empty")
    if actual_size > settings.FILE_MAX_UPLOAD_SIZE or actual_size != record.file_size:
        record.status = "failed"
        record.error_message = "Uploaded object size does not match requested file_size"
        db.add(record)
        await db.commit()
        raise HTTPException(status_code=400, detail=record.error_message)
    if not _magic_bytes_match(header, record.mime_type):
        record.status = "failed"
        record.error_message = "Uploaded object content does not match declared mime_type"
        db.add(record)
        await db.commit()
        raise HTTPException(status_code=400, detail=record.error_message)

    download_url = document_upload_storage.create_presigned_get_url(object_key=record.object_key)
    thumbnail_upload_url = None
    if record.mime_type == "application/pdf":
        thumbnail_upload_url = document_upload_storage.create_presigned_put_url(
            object_key=f"{file_id}/thumbnail.jpg",
            mime_type="image/jpeg",
            file_size=0,
        )

    task = process_stored_file.delay(
        file_id=str(record.id),
        user_id=str(current_user.id),
        download_url=download_url,
        file_name=record.file_name,
        mime_type=record.mime_type,
        thumbnail_upload_url=thumbnail_upload_url,
    )
    record.status = "queued"
    record.error_message = None
    db.add(record)
    db.add(
        BackgroundTask(
            user_id=current_user.id,
            task_type=BackgroundTaskType.DATA_SYNC,
            name=f"文档分析: {record.file_name}",
            status=BackgroundTaskStatus.PENDING,
            progress=0.0,
            progress_message="Queued for document analysis",
            related_entity_id=record.id,
            related_entity_type="stored_file",
            external_task_id=task.id,
        )
    )
    await db.commit()
    await _publish_status(
        file_id=record.id,
        user_id=current_user.id,
        status_value="queued",
        progress_percent=0,
        stage="queued",
        job_id=task.id,
    )
    return ConfirmUploadResponse(job_id=task.id, estimated_seconds=60)


@router.get("/{file_id}/status", response_model=DocumentStatusResponse, summary="Get document processing status")
async def get_document_status(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(StoredFile, file_id)
    if not record or record.user_id != current_user.id or record.is_deleted:
        raise HTTPException(status_code=404, detail="File not found")

    task = await _latest_task(db, file_id, current_user.id)
    progress_percent = int(max(0, min(100, round((task.progress or 0.0) * 100)))) if task else 0
    if record.status in {"processed", "done"}:
        progress_percent = 100
    elif record.status == "failed":
        progress_percent = max(progress_percent, 100)

    status_value, stage = _document_stage(record.status, progress_percent)
    error = record.error_message or (task.error_message if task else None)

    nodes_found = None
    if status_value in {"building_nodes", "done", "failed"}:
        node_count = await db.scalar(
            select(func.count(KnowledgeNode.id)).where(
                KnowledgeNode.source_file_id == file_id,
                KnowledgeNode.not_deleted_filter(),
            )
        )
        if node_count and node_count > 0:
            nodes_found = int(node_count)
        else:
            chunk_count = await db.scalar(
                select(func.count(DocumentChunk.id)).where(
                    DocumentChunk.file_id == file_id,
                    DocumentChunk.not_deleted_filter(),
                )
            )
            nodes_found = int(chunk_count or 0)

    drafts_pending = None
    if status_value == "done":
        draft_count = await db.scalar(
            select(func.count(KnowledgeNode.id)).where(
                KnowledgeNode.source_file_id == file_id,
                KnowledgeNode.status == "draft",
                KnowledgeNode.not_deleted_filter(),
            )
        )
        drafts_pending = int(draft_count or 0)

    return DocumentStatusResponse(
        status=status_value,
        progress_percent=progress_percent,
        stage=stage,
        nodes_found=nodes_found,
        drafts_pending=drafts_pending,
        error=error,
    )


class DraftsSummaryResponse(BaseModel):
    total_drafts: int
    files_with_drafts: list[dict[str, object]]


@router.get("/drafts/summary", response_model=DraftsSummaryResponse, summary="Get pending draft nodes summary")
async def get_drafts_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(
            KnowledgeNode.source_file_id,
            func.count(KnowledgeNode.id).label("draft_count"),
        )
        .where(
            KnowledgeNode.user_id == current_user.id,
            KnowledgeNode.status == "draft",
            KnowledgeNode.not_deleted_filter(),
        )
        .group_by(KnowledgeNode.source_file_id)
    )
    files = []
    total = 0
    for row in rows:
        files.append({"file_id": str(row.source_file_id), "draft_count": row.draft_count})
        total += row.draft_count
    return DraftsSummaryResponse(total_drafts=total, files_with_drafts=files)


@router.post("/feedback/citation", response_model=CitationFeedbackResponse, summary="Submit document citation feedback")
async def submit_citation_feedback(
    payload: CitationFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(StoredFile, payload.file_id)
    if not record or record.is_deleted:
        raise HTTPException(status_code=404, detail="File not found")

    is_owner = record.user_id == current_user.id
    if not is_owner and str(record.visibility or "private").lower() != "group":
        raise HTTPException(status_code=403, detail="You do not have access to this file")

    await document_service.publish_citation_feedback(
        user_id=str(current_user.id),
        file_id=str(payload.file_id),
        chunk_id=payload.chunk_id,
        rating=payload.rating,
        query_type=payload.query_type,
        conversation_id=payload.conversation_id,
        context=payload.context or {},
        feedback_source="explicit",
        db=db,
    )
    return CitationFeedbackResponse(accepted=True, feedback_source="explicit")
