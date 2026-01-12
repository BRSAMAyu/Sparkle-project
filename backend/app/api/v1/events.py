from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.events import (
    EventIngestRequest,
    EventIngestResponse,
    EventDetailResponse,
    EvidenceResolveRequest,
    EvidenceResolveResponse,
    EvidenceResolveItem,
    UserStateSummary,
    EventDeleteResponse,
)
from app.services.event_service import EventService
from app.services.state_estimator_service import StateEstimatorService
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode
from app.models.semantic_memory import StrategyNode
from sqlalchemy import select

router = APIRouter(prefix="/events", tags=["events"])


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
    await estimator.update_state(current_user.id, current_user.timezone)

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
    resolved: List[EvidenceResolveItem] = []
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
                result = await db.execute(
                    select(ErrorRecord).where(
                        ErrorRecord.id == item.id,
                        ErrorRecord.user_id == current_user.id,
                        ErrorRecord.is_deleted == False,
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
