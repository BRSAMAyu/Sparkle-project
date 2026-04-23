from __future__ import annotations
from datetime import timezone, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.accountability import PendingCommitmentListOut, PendingCommitmentOut
from app.api.deps import get_current_user, get_db
from app.config import settings
from app.core.cache import cache_service
from app.models.chat import ChatSession
from app.models.memory import EpisodicMemory, MemoryGoal, MemoryPreference
from app.models.user import User
from app.services.accountability_mvp_service import AccountabilityMvpService
from app.services.conflict_resolver_service import ConflictResolverService
from app.services.personalization.inferred_meta import INFERRED_META, build_inferred_explanation
from app.services.memory_service import MemoryService
from app.services.working_memory_consolidation_service import WorkingMemoryConsolidationService
from app.state_aggregator.service import StateAggregatorService
from app.working_memory.service import WorkingMemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _ensure_memory_panel_enabled() -> None:
    if not settings.ENABLE_MEMORY_PANEL:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory panel disabled")


def _ensure_memory_export_enabled() -> None:
    if not settings.ENABLE_MEMORY_EXPORT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory export disabled")

def _ensure_memory_correction_enabled() -> None:
    if not settings.ENABLE_MEMORY_CORRECTION:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory correction disabled")


def _resolve_preference_source(record: MemoryPreference) -> tuple[str, str]:
    evidence_types = {
        ref.get("type")
        for ref in (record.evidence_refs or [])
        if isinstance(ref, dict)
    }
    if "ai_inferred" in evidence_types:
        return "ai_inferred", "系统推断"
    return "user_state", "用户设置"


def _serialize_preference_record(
    record: MemoryPreference,
    *,
    current_values: dict[str, object],
) -> dict[str, object]:
    source_type, source_label = _resolve_preference_source(record)
    explanation = None
    adjustable = False
    if source_type == "ai_inferred":
        explanation = build_inferred_explanation(
            record.pref_key,
            (record.pref_value or {}).get("value") if isinstance(record.pref_value, dict) else record.pref_value,
            current_values,
        )
        adjustable = INFERRED_META.get(record.pref_key).adjustable if record.pref_key in INFERRED_META else False

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
        "source_label": source_label,
        "source_type": source_type,
        "explanation": explanation,
        "adjustable": adjustable,
    }


async def _resolve_working_memory_session_id(
    db: AsyncSession,
    *,
    user_id: UUID,
    session_id: str | None,
) -> str | None:
    if session_id:
        return session_id
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id, ChatSession.is_active.is_(True))
        .order_by(ChatSession.last_message_at.desc().nullslast(), ChatSession.created_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()
    return str(session.id) if session else None


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
    records = result.scalars().all()
    current_values = {}
    for record in records:
        if record.pref_key in current_values:
            continue
        current_values[record.pref_key] = (
            (record.pref_value or {}).get("value")
            if isinstance(record.pref_value, dict)
            else record.pref_value
        )
    for record in records:
        if record.pref_key in latest_by_key:
            continue
        latest_by_key[record.pref_key] = _serialize_preference_record(
            record,
            current_values=current_values,
        )
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
    status_filter: str | None = Query(default=None, alias="status"),
    include_expired: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    now = _utcnow()
    stmt = select(MemoryGoal).where(
        MemoryGoal.user_id == current_user.id,
        MemoryGoal.deleted_at.is_(None),
        MemoryGoal.retracted_at.is_(None),
    )
    if status_filter:
        stmt = stmt.where(MemoryGoal.status == status_filter)
    if not include_expired:
        stmt = stmt.where(
            MemoryGoal.expires_at.is_(None) | (MemoryGoal.expires_at > now)
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
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
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
                "source_lane": record.source_lane,
                "subject_type": record.subject_type,
                "occurred_at": record.occurred_at,
                "due_at": record.due_at,
                "resolved_at": record.resolved_at,
                "importance_score": record.importance_score,
                "confidence": record.confidence,
                "evidence_token": record.evidence_token,
                "decay_policy": record.decay_policy,
                "evidence_score": record.evidence_score,
                "correction_count": record.correction_count,
                "evidence_missing": record.evidence_missing,
                "evidence_refs": record.evidence_refs or [],
                "updated_at": record.updated_at,
                "retracted_at": record.retracted_at,
                "revoked_at": record.revoked_at,
                "mentioned_entity_hash": record.mentioned_entity_hash,
                "declaration_label": (
                    "AI 推断" if record.source_lane == "inferred_extraction" else None
                ),
            }
        )
    return {"items": items}


# route-tier: authed
@router.get("/working-memory/session")
async def get_working_memory_session(
    session_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    resolved_session_id = await _resolve_working_memory_session_id(
        db,
        user_id=current_user.id,
        session_id=session_id,
    )
    if resolved_session_id is None:
        return {"session_id": None, "items": []}

    service = WorkingMemoryService(cache_service.redis)
    items = await service.list_entries(
        user_id=str(current_user.id),
        session_id=resolved_session_id,
        limit=10,
        include_rejected=True,
    )
    return {
        "session_id": resolved_session_id,
        "items": [
            {
                "id": item.entry_id,
                "summary": item.text,
                "subject_type": item.subject_type,
                "mention_count": item.mention_count,
                "salience_score": item.salience_score,
                "source_turn_ids": list(item.source_turn_ids),
                "evidence_token": item.evidence_token,
                "confirmation_status": item.confirmation_status,
                "consolidated_to_l1_id": item.consolidated_to_l1_id,
                "rejected": item.rejected,
                "last_seen_at": item.last_seen_at,
            }
            for item in items
        ],
    }


# route-tier: authed
@router.post("/working-memory/{entry_id}/forget")
async def forget_working_memory_entry(
    entry_id: str,
    session_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    resolved_session_id = await _resolve_working_memory_session_id(
        db,
        user_id=current_user.id,
        session_id=session_id,
    )
    if resolved_session_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session working memory")
    service = WorkingMemoryService(cache_service.redis)
    deleted = await service.forget_entry(
        user_id=str(current_user.id),
        session_id=resolved_session_id,
        entry_id=entry_id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Working memory entry not found")
    return {"status": "ok"}


# route-tier: authed
@router.post("/working-memory/{entry_id}/mark-correct")
async def mark_working_memory_entry_correct(
    entry_id: str,
    session_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    resolved_session_id = await _resolve_working_memory_session_id(
        db,
        user_id=current_user.id,
        session_id=session_id,
    )
    if resolved_session_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session working memory")
    service = WorkingMemoryService(cache_service.redis)
    updated = await service.mark_correct(
        user_id=str(current_user.id),
        session_id=resolved_session_id,
        entry_id=entry_id,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Working memory entry not found")
    consolidation = WorkingMemoryConsolidationService(db, cache_service.redis)
    await consolidation.maybe_consolidate_recent_entries(
        user_id=current_user.id,
        session_id=UUID(resolved_session_id),
        explicit_confirmation=True,
    )
    return {
        "id": updated.entry_id,
        "summary": updated.text,
        "subject_type": updated.subject_type,
        "mention_count": updated.mention_count,
        "confirmation_status": updated.confirmation_status,
        "consolidated_to_l1_id": updated.consolidated_to_l1_id,
        "last_seen_at": updated.last_seen_at,
    }


# route-tier: authed
@router.get("/accountability/pending", response_model=PendingCommitmentListOut)
async def list_pending_commitments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    service = AccountabilityMvpService(db)
    items = await service.list_pending_commitments(user_id=current_user.id)
    return PendingCommitmentListOut(
        items=[
            PendingCommitmentOut(
                id=item.id,
                summary=item.summary,
                due_at=item.due_at,
                subject_type=item.subject_type,
                evidence_token=item.evidence_token,
                resolved_at=item.resolved_at,
            )
            for item in items
        ]
    )


# route-tier: authed
@router.get("/accountability/recent-scenes")
async def list_recent_scenes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    state = await StateAggregatorService(db).get_user_state(
        current_user.id,
        required_fields=("recent_scenes",),
    )
    field = state.recent_scenes
    if field is None:
        return {"schema_version": state.schema_version, "items": []}
    return {
        "schema_version": state.schema_version,
        "items": [
            {
                "scene_id": item.scene_id,
                "title": item.title,
                "time_start": item.time_start,
                "time_end": item.time_end,
                "member_count": item.member_count,
                "quality_score": item.quality_score,
            }
            for item in field.value.items
        ],
    }


# route-tier: authed
@router.get("/accountability/foresight-hint")
async def get_foresight_hint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    state = await StateAggregatorService(db).get_user_state(
        current_user.id,
        required_fields=("foresight_hint",),
    )
    field = state.foresight_hint
    if field is None:
        return {
            "schema_version": state.schema_version,
            "hint_text": None,
            "generated_at": None,
            "deviation_count": 0,
            "attractor_confidences": [],
        }
    return {
        "schema_version": state.schema_version,
        "hint_text": field.value.hint_text,
        "generated_at": field.value.generated_at,
        "deviation_count": field.value.deviation_count,
        "attractor_confidences": [
            {
                "dim": item.dim,
                "confidence": item.confidence,
            }
            for item in field.value.attractor_confidences
        ],
    }


# route-tier: authed
@router.post("/accountability/pending/{memory_id}/resolve", response_model=PendingCommitmentOut)
async def resolve_pending_commitment(
    memory_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    service = AccountabilityMvpService(db)
    item = await service.resolve_commitment(user_id=current_user.id, memory_id=memory_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="commitment not found")
    return PendingCommitmentOut(
        id=item.id,
        summary=item.summary,
        due_at=item.due_at,
        subject_type=item.subject_type,
        evidence_token=item.evidence_token,
        resolved_at=item.resolved_at,
    )


# route-tier: authed
@router.get("/unresolved-conflicts")
async def list_unresolved_conflicts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    service = ConflictResolverService(db)
    items = await service.list_unresolved_conflicts(user_id=current_user.id)
    return {"items": [_serialize_unresolved_conflict(item) for item in items]}


# route-tier: authed
@router.post("/unresolved-conflicts/{conflict_id}/arbitrate")
async def arbitrate_unresolved_conflict(
    conflict_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_panel_enabled()
    selection = str(payload.get("selection") or "").strip().lower()
    if selection not in {"left", "right", "none"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="selection must be left/right/none")
    service = ConflictResolverService(db)
    item = await service.arbitrate_unresolved_conflict(
        user_id=current_user.id,
        conflict_id=conflict_id,
        selection=selection,
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unresolved conflict not found")
    return _serialize_unresolved_conflict(item)


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
            EpisodicMemory.revoked_at.is_(None),
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
        "source_lane": record.source_lane,
        "occurred_at": record.occurred_at,
        "importance_score": record.importance_score,
        "confidence": record.confidence,
        "evidence_token": record.evidence_token,
        "decay_policy": record.decay_policy,
        "evidence_score": record.evidence_score,
        "correction_count": record.correction_count,
        "evidence_missing": record.evidence_missing,
        "evidence_refs": record.evidence_refs or [],
        "retracted_at": record.retracted_at,
        "revoked_at": record.revoked_at,
        "declaration_label": (
            "AI 推断" if record.source_lane == "inferred_extraction" else None
        ),
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


def _serialize_unresolved_conflict(record) -> dict[str, object]:
    return {
        "id": str(record.id),
        "conflict_key": record.conflict_key,
        "status": record.status,
        "surfaced_at": record.surfaced_at,
        "resolved_at": record.resolved_at,
        "resolution_reason": record.resolution_reason,
        "selected_side": record.selected_side,
        "left_candidate": {
            "record_id": str(record.left_record_id) if record.left_record_id else None,
            "summary": record.left_summary,
            "lane": record.left_lane,
            "evidence_token": record.left_evidence_token,
        },
        "right_candidate": {
            "record_id": str(record.right_record_id) if record.right_record_id else None,
            "summary": record.right_summary,
            "lane": record.right_lane,
            "evidence_token": record.right_evidence_token,
        },
    }
