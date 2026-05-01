from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.models.chat import ChatMessage, MessageRole
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode
from app.models.memory import EpisodicMemory
from app.models.nightly_review import NightlyReview
from app.models.semantic_memory import StrategyNode
from app.models.task import Task
from app.models.user import User
from app.schemas.events import (
    EventDeleteResponse,
    EventDetailResponse,
    EventIngestRequest,
    EventIngestResponse,
    EvidenceResolveItem,
    EvidenceResolveRequest,
    EvidenceResolveResponse,
    UserStateSummary,
)
from app.services.event_service import EventService
from app.services.state_estimator_service import StateEstimatorService

router = APIRouter(prefix="/events", tags=["events"])


def _tag_value(tags: list[str] | None, prefix: str) -> str:
    for tag in tags or []:
        value = str(tag or "")
        if value.startswith(prefix):
            return value.split(":", 1)[1].strip()
    return ""


def _coerce_uuid(raw: str):
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        return None


@router.post("/ingest", response_model=EventIngestResponse)
async def ingest_events(
    payload: EventIngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = []
    for event in payload.events:
        if event.user_id and event.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user_id mismatch")
        item = event.model_dump()
        item["user_id"] = str(current_user.id)
        items.append(item)

    service = EventService(db)
    result = await service.ingest_events(current_user.id, items)

    estimator = StateEstimatorService(db)
    timezone_name = (
        getattr(getattr(current_user, "push_preference", None), "timezone", None)
        or "Asia/Shanghai"
    )
    await estimator.update_state(current_user.id, timezone_name)
    await cache_service.delete(f"predictive:next_intent:{current_user.id}")

    return EventIngestResponse(**result)


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EventService(db)
    event = await service.get_event(current_user.id, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return EventDetailResponse(
        event_id=event.event_id,
        user_id=event.user_id,
        event_type=event.event_type,
        schema_version=event.schema_version,
        source=event.source,
        ts_ms=event.ts_ms,
        entities=event.entities,
        payload=event.payload,
        deleted=event.deleted_at is not None,
        created_at=event.created_at,
    )


@router.post("/evidence/resolve", response_model=EvidenceResolveResponse)
async def resolve_evidence(
    payload: EvidenceResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EventService(db)
    resolved: list[EvidenceResolveItem] = []
    for item in payload.items:
        if item.user_deleted:
            resolved.append(
                EvidenceResolveItem(
                    type=item.type,
                    id=item.id,
                    status="redacted",
                    redaction_reason="user_deleted_flag",
                )
            )
            continue
        if item.type != "event":
            if item.type == "chat_turn":
                chat_id = _coerce_uuid(item.id)
                if chat_id is None:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="invalid_id")
                    )
                    continue
                result = await db.execute(
                    select(ChatMessage).where(
                        ChatMessage.id == chat_id,
                        ChatMessage.user_id == current_user.id,
                        ChatMessage.deleted_at.is_(None),
                    )
                )
                chat_turn = result.scalar_one_or_none()
                if not chat_turn:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="not_found")
                    )
                    continue
                resolved.append(
                    EvidenceResolveItem(
                        type=item.type,
                        id=item.id,
                        status="ok",
                        chat_turn={
                            "id": str(chat_turn.id),
                            "session_id": str(chat_turn.session_id),
                            "role": (
                                chat_turn.role.value
                                if isinstance(chat_turn.role, MessageRole)
                                else str(chat_turn.role)
                            ),
                            "content": chat_turn.content,
                            "created_at": chat_turn.created_at,
                        },
                    )
                )
                continue

            if item.type == "user_state":
                estimator = StateEstimatorService(db)
                try:
                    snapshot = await estimator.get_snapshot_by_id(current_user.id, item.id)
                except Exception:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="invalid_id")
                    )
                    continue
                if not snapshot:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="not_found")
                    )
                    continue

                if snapshot.deleted_at is not None:
                    resolved.append(
                        EvidenceResolveItem(
                            type=item.type,
                            id=item.id,
                            status="redacted",
                            redaction_reason="deleted_by_user",
                        )
                    )
                    continue

                resolved.append(
                    EvidenceResolveItem(
                        type=item.type,
                        id=item.id,
                        status="ok",
                        state=UserStateSummary(
                            user_id=current_user.id,
                            snapshot_at=snapshot.snapshot_at,
                            window_start=snapshot.window_start,
                            window_end=snapshot.window_end,
                            cognitive_load=snapshot.cognitive_load,
                            interruptibility=snapshot.interruptibility,
                            strain_index=snapshot.strain_index,
                            focus_mode=snapshot.focus_mode,
                            sprint_mode=snapshot.sprint_mode,
                            time_context=snapshot.time_context,
                            derived_event_ids=snapshot.derived_event_ids,
                        ),
                    )
                )
                continue

            if item.type == "error":
                error_id = _coerce_uuid(item.id)
                if error_id is None:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="invalid_id")
                    )
                    continue
                result = await db.execute(
                    select(ErrorRecord).where(
                        ErrorRecord.id == error_id,
                        ErrorRecord.user_id == current_user.id,
                        ErrorRecord.is_deleted.is_(False),
                    )
                )
                error = result.scalar_one_or_none()
                if not error:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="not_found")
                    )
                    continue
                resolved.append(
                    EvidenceResolveItem(
                        type=item.type,
                        id=item.id,
                        status="ok",
                        error={
                            "id": str(error.id),
                            "subject_code": error.subject_code,
                            "root_cause": (error.latest_analysis or {}).get("root_cause"),
                            "study_suggestion": (error.latest_analysis or {}).get("study_suggestion"),
                        },
                    )
                )
                continue

            if item.type == "concept":
                result = await db.execute(
                    select(KnowledgeNode).where(KnowledgeNode.id == item.id)
                )
                node = result.scalar_one_or_none()
                if not node:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="not_found")
                    )
                    continue
                resolved.append(
                    EvidenceResolveItem(
                        type=item.type,
                        id=item.id,
                        status="ok",
                        concept={
                            "id": str(node.id),
                            "name": node.name,
                            "description": node.description,
                            "subject_id": node.subject_id,
                        },
                    )
                )
                continue

            if item.type == "strategy":
                result = await db.execute(
                    select(StrategyNode).where(
                        StrategyNode.id == item.id,
                        StrategyNode.user_id == current_user.id,
                        StrategyNode.deleted_at.is_(None),
                    )
                )
                strategy = result.scalar_one_or_none()
                if not strategy:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="not_found")
                    )
                    continue
                resolved.append(
                    EvidenceResolveItem(
                        type=item.type,
                        id=item.id,
                        status="ok",
                        strategy={
                            "id": str(strategy.id),
                            "title": strategy.title,
                            "description": strategy.description,
                            "subject_code": strategy.subject_code,
                        },
                    )
                )
                continue

            if item.type == "task":
                result = await db.execute(
                    select(Task).where(
                        Task.id == item.id,
                        Task.user_id == current_user.id,
                    )
                )
                task = result.scalar_one_or_none()
                if not task:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="not_found")
                    )
                    continue
                if task.deleted_at is not None:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="redacted")
                    )
                    continue
                resolved.append(
                    EvidenceResolveItem(
                        type=item.type,
                        id=item.id,
                        status="ok",
                        task={
                            "id": str(task.id),
                            "title": task.title,
                            "status": task.status.value if task.status else None,
                            "due_date": task.due_date,
                        },
                    )
                )
                continue

            if item.type == "practice_outcome":
                error_id = _coerce_uuid(item.id)
                if error_id is None:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="invalid_id")
                    )
                    continue
                memory_result = await db.execute(
                    select(EpisodicMemory).where(
                        EpisodicMemory.user_id == current_user.id,
                        EpisodicMemory.source_type == "practice_outcome",
                        EpisodicMemory.source_id == item.id,
                        EpisodicMemory.deleted_at.is_(None),
                        EpisodicMemory.archived_at.is_(None),
                        EpisodicMemory.retracted_at.is_(None),
                    ).order_by(EpisodicMemory.occurred_at.desc())
                )
                outcome = memory_result.scalars().first()
                if not outcome:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="not_found")
                    )
                    continue

                error_result = await db.execute(
                    select(ErrorRecord).where(
                        ErrorRecord.id == error_id,
                        ErrorRecord.user_id == current_user.id,
                        ErrorRecord.is_deleted.is_(False),
                    )
                )
                error = error_result.scalar_one_or_none()
                if not error:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="not_found")
                    )
                    continue

                resolved.append(
                    EvidenceResolveItem(
                        type=item.type,
                        id=item.id,
                        status="ok",
                        practice_outcome={
                            "id": str(error.id),
                            "error_id": str(error.id),
                            "subject_code": error.subject_code,
                            "review_performance": _tag_value(outcome.tags, "performance:"),
                            "mastery_level": error.mastery_level,
                            "review_count": error.review_count,
                            "reviewed_at": outcome.occurred_at,
                            "summary": outcome.summary,
                        },
                    )
                )
                continue

            if item.type == "summary":
                result = await db.execute(
                    select(NightlyReview).where(
                        NightlyReview.id == item.id,
                        NightlyReview.user_id == current_user.id,
                    )
                )
                review = result.scalar_one_or_none()
                if not review:
                    resolved.append(
                        EvidenceResolveItem(type=item.type, id=item.id, status="not_found")
                    )
                    continue
                resolved.append(
                    EvidenceResolveItem(
                        type=item.type,
                        id=item.id,
                        status="ok",
                        summary={
                            "id": str(review.id),
                            "review_date": review.review_date,
                            "summary_text": review.summary_text,
                        },
                    )
                )
                continue

            resolved.append(
                EvidenceResolveItem(type=item.type, id=item.id, status="unsupported")
            )
            continue

        event = await service.get_event(current_user.id, item.id)
        if not event:
            resolved.append(
                EvidenceResolveItem(type=item.type, id=item.id, status="not_found")
            )
            continue

        if event.deleted_at is not None:
            resolved.append(
                EvidenceResolveItem(
                    type=item.type,
                    id=item.id,
                    status="redacted",
                    redaction_reason="deleted_by_user",
                )
            )
            continue

        resolved.append(
            EvidenceResolveItem(
                type=item.type,
                id=item.id,
                status="ok",
                event=EventDetailResponse(
                    event_id=event.event_id,
                    user_id=event.user_id,
                    event_type=event.event_type,
                    schema_version=event.schema_version,
                    source=event.source,
                    ts_ms=event.ts_ms,
                    entities=event.entities,
                    payload=event.payload,
                    deleted=False,
                    created_at=event.created_at,
                ),
            )
        )

    return EvidenceResolveResponse(resolved=resolved)


@router.get("/state/summary", response_model=UserStateSummary)
async def get_state_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    estimator = StateEstimatorService(db)
    snapshot = await estimator.get_latest_snapshot(current_user.id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")
    return UserStateSummary(
        user_id=current_user.id,
        snapshot_at=snapshot.snapshot_at,
        window_start=snapshot.window_start,
        window_end=snapshot.window_end,
        cognitive_load=snapshot.cognitive_load,
        interruptibility=snapshot.interruptibility,
        strain_index=snapshot.strain_index,
        focus_mode=snapshot.focus_mode,
        sprint_mode=snapshot.sprint_mode,
        time_context=snapshot.time_context,
        derived_event_ids=snapshot.derived_event_ids,
    )


@router.delete("/{event_id}", response_model=EventDeleteResponse)
async def delete_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EventService(db)
    deleted = await service.soft_delete_event(current_user.id, event_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return EventDeleteResponse(event_id=event_id, status="deleted")
