"""Source document lifecycle API."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.file_storage import SourceLifecycleStatus
from app.models.user import User
from app.services.source_lifecycle import source_lifecycle_payload, source_lifecycle_service

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceLifecycleRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class GoalCloseCleanupRequest(BaseModel):
    goal_id: UUID
    reason: str | None = Field(default="goal_closed", max_length=255)


async def _load_source_or_404(db: AsyncSession, source_id: UUID, user_id: UUID):
    source = await source_lifecycle_service.get_owned_source(db, source_id=source_id, user_id=user_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


# route-tier: authed
@router.post("/{source_id}/archive", summary="Archive a source document")
async def archive_source(
    source_id: UUID,
    payload: SourceLifecycleRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    source = await _load_source_or_404(db, source_id, current_user.id)
    if source.lifecycle_status == SourceLifecycleStatus.ARCHIVED.value:
        raise HTTPException(status_code=409, detail="Source is already archived")
    result = await source_lifecycle_service.archive(
        db,
        source=source,
        reason=(payload.reason if payload else None) or "user_archive",
    )
    await db.commit()
    return source_lifecycle_payload(result.source, invalidated_keys=result.invalidated_keys)


# route-tier: authed
@router.post("/{source_id}/restore", summary="Restore an archived or orphaned source document")
async def restore_source(
    source_id: UUID,
    payload: SourceLifecycleRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    source = await _load_source_or_404(db, source_id, current_user.id)
    try:
        result = await source_lifecycle_service.restore(
            db,
            source=source,
            reason=(payload.reason if payload else None) or "user_restore",
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.commit()
    return source_lifecycle_payload(result.source, invalidated_keys=result.invalidated_keys)


# route-tier: authed
@router.post("/{source_id}/revoke", summary="Revoke sharing/retrieval permissions for a source document")
async def revoke_source_permissions(
    source_id: UUID,
    payload: SourceLifecycleRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    source = await _load_source_or_404(db, source_id, current_user.id)
    result = await source_lifecycle_service.revoke_permissions(
        db,
        source=source,
        reason=(payload.reason if payload else None) or "permission_revoked",
    )
    await db.commit()
    body = source_lifecycle_payload(result.source, invalidated_keys=result.invalidated_keys)
    body["revoked_group_links"] = result.affected_group_links
    return body


# route-tier: authed
@router.delete("/{source_id}", summary="Delete and cryptographically erase a source document")
async def delete_source(
    source_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    source = await _load_source_or_404(db, source_id, current_user.id)
    result = await source_lifecycle_service.delete(db, source=source)
    await db.commit()
    return source_lifecycle_payload(result.source, invalidated_keys=result.invalidated_keys)


# route-tier: authed
@router.post("/goal-close-cleanup", summary="Mark closed-goal source material as orphaned")
async def goal_close_cleanup(
    payload: GoalCloseCleanupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    results = await source_lifecycle_service.goal_close_cleanup(
        db,
        user_id=current_user.id,
        goal_id=payload.goal_id,
        reason=payload.reason or "goal_closed",
    )
    await db.commit()
    return {
        "updated": len(results),
        "sources": [
            source_lifecycle_payload(result.source, invalidated_keys=result.invalidated_keys)
            for result in results
        ],
    }


# route-tier: authed
@router.get("/archive-review-due", summary="List archived sources that need keep/delete review")
async def archive_review_due(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    due_sources = await source_lifecycle_service.list_archive_review_due(db)
    mine = [source for source in due_sources if source.user_id == current_user.id]
    return {"sources": [source_lifecycle_payload(source) for source in mine]}
