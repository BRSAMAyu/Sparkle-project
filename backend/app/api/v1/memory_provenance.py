"""Memory Provenance/Scope user API (task M-08) — the U-03 read/mutation face.

Every endpoint is a thin handler over ``MemoryProvenanceService``; zero
business logic lives here. Ownership law (X-05B runs.py pattern): cross-user
AND missing records are indistinguishable — both 404, no existence leak, for
ids AND receipt/pack enumeration paths alike.

Error mapping:
    ValueError                      → 422 (malformed ref / unknown bucket-kind /
                                      missing required field)
    ...ConflictError                → 409 (truth source declined / terminal state)
    ...NotFoundError                → 404 (missing OR cross-user)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.models.user import User
from app.services.memory_provenance_service import (
    MemoryProvenanceConflictError,
    MemoryProvenanceNotFoundError,
    MemoryProvenanceService,
)

router = APIRouter(prefix="/memory/provenance", tags=["memory"])


def _ensure_memory_panel_enabled() -> None:
    if not settings.ENABLE_MEMORY_PANEL:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory panel disabled")


# --- request models -----------------------------------------------------------


class ScopeUpdateRequest(BaseModel):
    """Scope action: pause/resume（暂时不用/恢复）or goal linkage（仅此 Goal）."""

    action: str = Field(min_length=1, max_length=32)
    plan_id: UUID | None = None
    task_id: UUID | None = None
    reason: str | None = Field(default=None, max_length=500)


class MemoryUpdateRequest(BaseModel):
    """User edit of a memory item (supersede for episodic, version-chain for
    preference, field update for goal — semantics owned by the service)."""

    content: str | None = Field(default=None, min_length=1, max_length=2000)
    pref_value: dict[str, object] | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    goal_status: str | None = Field(default=None, max_length=30)
    reason: str | None = Field(default=None, max_length=500)


class RevokeRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class WhyThisRequest(BaseModel):
    """A memory-use receipt as it rides in ContextPack.metadata
    (M-05 memory_selfcheck structure + C-01 memory:// ref)."""

    memory_ref: str = Field(min_length=1, max_length=120)
    version: str | None = Field(default=None, max_length=64)
    pack_id: UUID | None = None
    why_included: list[str] = Field(default_factory=list, max_length=32)
    internal_only: list[dict[str, object]] = Field(default_factory=list, max_length=64)


# --- helpers -------------------------------------------------------------------


def _parse_kind(kind: str) -> str:
    normalized = str(kind or "").strip().lower()
    if normalized not in {"episodic", "preference", "goal"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="kind must be episodic/preference/goal"
        )
    return normalized


# --- Work 1: list / detail / scope / update / revoke ---------------------------


# route-tier: authed
@router.get("/items")
async def list_memory_items(
    bucket: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    include_inactive: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    service = MemoryProvenanceService(db)
    try:
        return await service.list_items(
            current_user.id,
            bucket=bucket,
            kind=_parse_kind(kind) if kind else None,
            limit=limit,
            offset=offset,
            include_inactive=include_inactive,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


# route-tier: authed
@router.get("/items/{kind}/{memory_id}")
async def get_memory_item(
    kind: str,
    memory_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    service = MemoryProvenanceService(db)
    try:
        return await service.get_item(current_user.id, _parse_kind(kind), memory_id)
    except MemoryProvenanceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# route-tier: authed
@router.get("/items/{kind}/{memory_id}/source")
async def get_memory_source(
    kind: str,
    memory_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    service = MemoryProvenanceService(db)
    try:
        return await service.get_source(current_user.id, _parse_kind(kind), memory_id)
    except MemoryProvenanceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# route-tier: authed
@router.get("/items/{kind}/{memory_id}/scope")
async def get_memory_scope(
    kind: str,
    memory_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    service = MemoryProvenanceService(db)
    try:
        return await service.get_scope(current_user.id, _parse_kind(kind), memory_id)
    except MemoryProvenanceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# route-tier: authed
@router.put("/items/{kind}/{memory_id}/scope")
async def update_memory_scope(
    kind: str,
    memory_id: UUID,
    payload: ScopeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    service = MemoryProvenanceService(db)
    try:
        return await service.update_scope(
            current_user.id,
            _parse_kind(kind),
            memory_id,
            action=payload.action,
            plan_id=payload.plan_id,
            task_id=payload.task_id,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except MemoryProvenanceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except MemoryProvenanceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# route-tier: authed
@router.post("/items/{kind}/{memory_id}/update")
async def update_memory_item(
    kind: str,
    memory_id: UUID,
    payload: MemoryUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    if not settings.ENABLE_MEMORY_CORRECTION:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory correction disabled")
    service = MemoryProvenanceService(db)
    try:
        return await service.update_item(
            current_user.id,
            _parse_kind(kind),
            memory_id,
            content=payload.content,
            pref_value=payload.pref_value,
            title=payload.title,
            status=payload.goal_status,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except MemoryProvenanceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except MemoryProvenanceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# route-tier: authed
@router.post("/items/{kind}/{memory_id}/revoke")
async def revoke_memory_item(
    kind: str,
    memory_id: UUID,
    payload: RevokeRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    if not settings.ENABLE_MEMORY_RETRACTION:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory retraction disabled")
    service = MemoryProvenanceService(db)
    try:
        return await service.revoke_item(
            current_user.id,
            _parse_kind(kind),
            memory_id,
            reason=(payload.reason if payload else None),
        )
    except MemoryProvenanceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# --- Work 3: Why-this by memory_use_receipt ------------------------------------


# route-tier: authed
@router.post("/why-this")
async def lookup_why_this(
    payload: WhyThisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按记忆使用回执查「为什么当时用这条记忆」（M-05 receipt structure)."""
    _ensure_memory_panel_enabled()
    service = MemoryProvenanceService(db)
    receipt = {
        "memory_ref": payload.memory_ref,
        "version": payload.version,
        "pack_id": payload.pack_id,
        "why_included": payload.why_included,
        "internal_only": payload.internal_only,
    }
    try:
        return await service.lookup_why_this(current_user.id, receipt)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except MemoryProvenanceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
