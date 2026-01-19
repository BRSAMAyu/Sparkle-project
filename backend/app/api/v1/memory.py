from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.models.memory import MemoryPreference, MemoryGoal, EpisodicMemory
from app.models.user import User
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


def _ensure_memory_panel_enabled() -> None:
    if not settings.ENABLE_MEMORY_PANEL:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory panel disabled")


def _ensure_memory_export_enabled() -> None:
    if not settings.ENABLE_MEMORY_EXPORT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory export disabled")

def _ensure_memory_correction_enabled() -> None:
    if not settings.ENABLE_MEMORY_CORRECTION:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory correction disabled")


@router.get("/preferences")
async def list_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    result = await db.execute(
        select(MemoryPreference)
        .where(
            MemoryPreference.user_id == current_user.id,
            MemoryPreference.deleted_at.is_(None),
            MemoryPreference.retracted_at.is_(None),
        )
        .order_by(MemoryPreference.pref_key.asc(), MemoryPreference.version.desc())
    )
    latest_by_key = {}
    for record in result.scalars().all():
        if record.pref_key in latest_by_key:
            continue
        latest_by_key[record.pref_key] = {
            "id": str(record.id),
            "pref_key": record.pref_key,
            "pref_value": record.pref_value,
            "version": record.version,
            "confidence": record.confidence,
            "evidence_score": record.evidence_score,
            "correction_count": record.correction_count,
            "updated_at": record.updated_at,
            "evidence_missing": record.evidence_missing,
            "evidence_refs": record.evidence_refs or [],
            "retracted_at": record.retracted_at,
        }
    return {"items": list(latest_by_key.values())}


@router.get("/preferences/{pref_key}/history")
async def preference_history(
    pref_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    result = await db.execute(
        select(MemoryPreference)
        .where(
            MemoryPreference.user_id == current_user.id,
            MemoryPreference.pref_key == pref_key,
            MemoryPreference.deleted_at.is_(None),
        )
        .order_by(MemoryPreference.version.desc())
    )
    history = []
    for record in result.scalars().all():
        history.append(
            {
                "id": str(record.id),
                "pref_key": record.pref_key,
                "pref_value": record.pref_value,
                "version": record.version,
                "confidence": record.confidence,
                "evidence_score": record.evidence_score,
                "correction_count": record.correction_count,
                "replaced_by_id": str(record.replaced_by_id) if record.replaced_by_id else None,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
                "evidence_missing": record.evidence_missing,
                "evidence_refs": record.evidence_refs or [],
                "retracted_at": record.retracted_at,
            }
        )
    return {"items": history}


@router.get("/goals")
async def list_goals(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    include_expired: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    now = datetime.utcnow()
    stmt = select(MemoryGoal).where(
        MemoryGoal.user_id == current_user.id,
        MemoryGoal.deleted_at.is_(None),
        MemoryGoal.retracted_at.is_(None),
    )
    if status_filter:
        stmt = stmt.where(MemoryGoal.status == status_filter)
    if not include_expired:
        stmt = stmt.where(
            (MemoryGoal.expires_at.is_(None) | (MemoryGoal.expires_at > now))
        )
    stmt = stmt.order_by(MemoryGoal.updated_at.desc()).limit(limit)
    result = await db.execute(stmt)
    items = []
    for record in result.scalars().all():
        items.append(
            {
                "id": str(record.id),
                "title": record.title,
                "status": record.status,
                "target_date": record.target_date,
                "expires_at": record.expires_at,
                "linked_task_id": str(record.linked_task_id) if record.linked_task_id else None,
                "linked_plan_id": str(record.linked_plan_id) if record.linked_plan_id else None,
                "evidence_score": record.evidence_score,
                "correction_count": record.correction_count,
                "evidence_missing": record.evidence_missing,
                "evidence_refs": record.evidence_refs or [],
                "updated_at": record.updated_at,
                "retracted_at": record.retracted_at,
            }
        )
    return {"items": items}


@router.get("/episodic")
async def list_episodic(
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    service = MemoryService(db)
    records = await service.list_recent_episodic(
        current_user.id,
        limit=limit,
        start=start,
        end=end,
    )
    items = []
    for record in records:
        items.append(
            {
                "id": str(record.id),
                "summary": record.summary,
                "source_type": record.source_type,
                "source_id": record.source_id,
                "occurred_at": record.occurred_at,
                "importance_score": record.importance_score,
                "evidence_score": record.evidence_score,
                "correction_count": record.correction_count,
                "evidence_missing": record.evidence_missing,
                "evidence_refs": record.evidence_refs or [],
                "updated_at": record.updated_at,
                "retracted_at": record.retracted_at,
            }
        )
    return {"items": items}


@router.post("/retract")
async def retract_memory(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    if not settings.ENABLE_MEMORY_RETRACTION:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory retraction disabled")

    kind = payload.get("type")
    memory_id = payload.get("id")
    reason = payload.get("reason")
    if not kind or not memory_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="type and id required")
    try:
        memory_uuid = UUID(memory_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid id") from exc

    service = MemoryService(db)
    try:
        success = await service.retract_memory(
            kind=kind,
            memory_id=memory_uuid,
            user_id=current_user.id,
            reason=reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory item not found")

    return {"status": "retracted"}


@router.post("/correct")
async def correct_memory(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    _ensure_memory_correction_enabled()

    kind = payload.get("type")
    memory_id = payload.get("id")
    action = payload.get("action")
    reason = payload.get("reason")
    if not kind or not memory_id or not action:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="type, id, and action required",
        )
    if action == "merge":
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="merge not implemented")
    if action in {"reject", "no_longer_applicable"} and not settings.ENABLE_MEMORY_RETRACTION:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory retraction disabled")
    try:
        memory_uuid = UUID(memory_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid id") from exc

    service = MemoryService(db)
    try:
        record = await service.apply_correction(
            kind=kind,
            memory_id=memory_uuid,
            user_id=current_user.id,
            action=action,
            reason=reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory item not found")

    return {
        "status": "corrected",
        "item": _serialize_corrected_memory(kind, record),
    }


@router.get("/export")
async def export_memory(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_export_enabled()
    _ensure_memory_panel_enabled()

    prefs_result = await db.execute(
        select(MemoryPreference)
        .where(
            MemoryPreference.user_id == current_user.id,
            MemoryPreference.deleted_at.is_(None),
        )
        .order_by(MemoryPreference.pref_key.asc(), MemoryPreference.version.desc())
    )
    prefs_latest = {}
    for record in prefs_result.scalars().all():
        if record.pref_key in prefs_latest:
            continue
        prefs_latest[record.pref_key] = _serialize_preference(record)

    goals_result = await db.execute(
        select(MemoryGoal)
        .where(
            MemoryGoal.user_id == current_user.id,
            MemoryGoal.deleted_at.is_(None),
        )
        .order_by(MemoryGoal.updated_at.desc())
    )
    goals = [_serialize_goal(item) for item in goals_result.scalars().all()]

    episodic_result = await db.execute(
        select(EpisodicMemory)
        .where(
            EpisodicMemory.user_id == current_user.id,
            EpisodicMemory.deleted_at.is_(None),
        )
        .order_by(EpisodicMemory.occurred_at.desc())
    )
    episodic = [_serialize_episodic(item) for item in episodic_result.scalars().all()]

    return {
        "user_id": str(current_user.id),
        "preferences": list(prefs_latest.values()),
        "goals": goals,
        "episodic": episodic,
    }


def _serialize_preference(record: MemoryPreference) -> dict:
    return {
        "id": str(record.id),
        "pref_key": record.pref_key,
        "pref_value": record.pref_value,
        "version": record.version,
        "confidence": record.confidence,
        "evidence_score": record.evidence_score,
        "correction_count": record.correction_count,
        "updated_at": record.updated_at,
        "evidence_missing": record.evidence_missing,
        "evidence_refs": record.evidence_refs or [],
        "retracted_at": record.retracted_at,
    }


def _serialize_goal(record: MemoryGoal) -> dict:
    return {
        "id": str(record.id),
        "title": record.title,
        "status": record.status,
        "target_date": record.target_date,
        "expires_at": record.expires_at,
        "evidence_score": record.evidence_score,
        "correction_count": record.correction_count,
        "evidence_missing": record.evidence_missing,
        "evidence_refs": record.evidence_refs or [],
        "retracted_at": record.retracted_at,
    }


def _serialize_episodic(record: EpisodicMemory) -> dict:
    payload = {
        "id": str(record.id),
        "summary": record.summary,
        "source_type": record.source_type,
        "source_id": record.source_id,
        "occurred_at": record.occurred_at,
        "importance_score": record.importance_score,
        "evidence_score": record.evidence_score,
        "correction_count": record.correction_count,
        "evidence_missing": record.evidence_missing,
        "evidence_refs": record.evidence_refs or [],
        "retracted_at": record.retracted_at,
    }
    if record.evidence_snapshot:
        payload["evidence_snapshot"] = record.evidence_snapshot
    return payload


def _serialize_corrected_memory(kind: str, record: object) -> dict:
    if kind == "preference":
        return _serialize_preference(record)
    if kind == "goal":
        return _serialize_goal(record)
    if kind == "episodic":
        return _serialize_episodic(record)
    return {"id": str(getattr(record, "id", ""))}
