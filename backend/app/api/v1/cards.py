from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.event_bus import event_bus as _event_bus
from app.db.session import get_db
from app.models.card_protocol import (
    BindingMode,
    CardLifecycleStatus,
    CardType,
    EdgeType,
    ImportMode,
    SharePermission,
    ShareScope,
)
from app.models.user import User
from app.services.card_protocol.card_operations_service import CardOperationsService
from app.services.card_protocol.card_snapshot_service import CardSnapshotService
from app.services.card_protocol.share_service import ShareService
from app.services.card_protocol.temporal_engine import RecurrenceRule, TemporalEngine, TimeWindow

router = APIRouter()


class MoveCardRequest(BaseModel):
    new_parent_card_id: UUID | None = Field(default=None)
    position: int | None = Field(default=None, ge=0)


class BulkMoveCardsRequest(BaseModel):
    card_ids: list[UUID] = Field(min_length=1)
    new_parent_card_id: UUID | None = Field(default=None)


class LinkCardRequest(BaseModel):
    target_card_id: UUID
    edge_type: EdgeType
    binding_mode: BindingMode = BindingMode.REFERENCE
    metadata: dict | None = None


class TimeWindowRequest(BaseModel):
    start: str
    end: str


class SetRecurrenceRequest(BaseModel):
    pattern: str = Field(pattern="^(once|daily|weekly|monthly|custom)$")
    days_of_week: list[int] | None = None
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    time_window: TimeWindowRequest | None = None
    flexible: bool = True
    max_deferrals: int = Field(default=3, ge=1, le=12)
    end_condition: str = Field(default="phase_end", pattern="^(date|count|phase_end|never)$")
    end_value: str | int | None = None
    interval_days: int | None = Field(default=None, ge=1, le=30)


class DeferOccurrenceRequest(BaseModel):
    new_date: str | None = None


class CreateSnapshotRequest(BaseModel):
    include_children: bool = True
    max_depth: int = Field(default=3, ge=1, le=8)


class ShareCardRequest(BaseModel):
    scope: ShareScope
    target_id: UUID | None = None
    permission: SharePermission = SharePermission.ADOPT
    message: str | None = Field(default=None, max_length=500)
    include_children: bool = True
    max_depth: int = Field(default=3, ge=1, le=8)
    metadata: dict | None = None


class AdoptShareRequest(BaseModel):
    import_mode: ImportMode = ImportMode.ADOPT
    modifications: dict | None = None


# route-tier: authed
@router.post("/{card_id}/move", response_model=dict)
async def move_card(
    card_id: UUID,
    request: MoveCardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CardOperationsService(db, event_bus=_event_bus)
    try:
        result = await service.move_card(
            card_id=card_id,
            new_parent_card_id=request.new_parent_card_id,
            user_id=current_user.id,
            position=request.position,
        )
        await db.commit()
        return {"success": True, "data": result.__dict__}
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# route-tier: authed
@router.post("/bulk-move", response_model=dict)
async def bulk_move_cards(
    request: BulkMoveCardsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CardOperationsService(db, event_bus=_event_bus)
    try:
        results = await service.bulk_move_cards(
            card_ids=request.card_ids,
            new_parent_card_id=request.new_parent_card_id,
            user_id=current_user.id,
        )
        await db.commit()
        return {"success": True, "data": [result.__dict__ for result in results]}
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# route-tier: authed
@router.post("/{card_id}/link", response_model=dict)
async def link_card(
    card_id: UUID,
    request: LinkCardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CardOperationsService(db, event_bus=_event_bus)
    try:
        edge = await service.link_cards(
            source_card_id=card_id,
            target_card_id=request.target_card_id,
            link_type=request.edge_type,
            binding_mode=request.binding_mode,
            metadata=request.metadata,
            user_id=current_user.id,
        )
        await db.commit()
        return {
            "success": True,
            "data": {
                "edge_id": str(edge.id),
                "from_card_id": str(edge.from_card_id),
                "to_card_id": str(edge.to_card_id),
                "edge_type": edge.edge_type.value,
                "binding_mode": edge.binding_mode.value,
            },
        }
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# route-tier: authed
@router.delete("/{card_id}/link/{target_id}/{edge_type}", response_model=dict)
async def unlink_card(
    card_id: UUID,
    target_id: UUID,
    edge_type: EdgeType,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CardOperationsService(db, event_bus=_event_bus)
    try:
        await service.unlink_cards(
            source_card_id=card_id,
            target_card_id=target_id,
            link_type=edge_type,
            user_id=current_user.id,
        )
        await db.commit()
        return {"success": True}
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# route-tier: authed
@router.get("/{card_id}/tree", response_model=dict)
async def get_card_tree(
    card_id: UUID,
    max_depth: int = Query(default=3, ge=1, le=8),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CardOperationsService(db, event_bus=_event_bus)
    try:
        tree = await service.get_card_tree(root_card_id=card_id, max_depth=max_depth)
        return {"success": True, "data": tree}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# route-tier: authed
@router.get("/search", response_model=dict)
async def search_cards(
    card_type: CardType | None = Query(default=None),
    status: CardLifecycleStatus | None = Query(default=None),
    tags: list[str] | None = Query(default=None),
    text_query: str | None = Query(default=None),
    parent_card_id: UUID | None = Query(default=None),
    legacy_task_id: UUID | None = Query(default=None),
    legacy_plan_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CardOperationsService(db, event_bus=_event_bus)
    cards = await service.search_cards(
        user_id=current_user.id,
        card_type=card_type,
        status=status,
        tags=tags,
        text_query=text_query,
        parent_card_id=parent_card_id,
        legacy_task_id=legacy_task_id,
        legacy_plan_id=legacy_plan_id,
        limit=limit,
        offset=offset,
    )
    return {
        "success": True,
        "data": [
            {
                "card_id": str(card.id),
                "card_type": card.card_type.value,
                "lifecycle_status": card.lifecycle_status.value,
                "tags": list(card.tags or []),
                "metadata": dict(card.metadata_ or {}),
            }
            for card in cards
        ],
    }


# route-tier: authed
@router.post("/{card_id}/recurrence", response_model=dict)
async def set_task_recurrence(
    card_id: UUID,
    request: SetRecurrenceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TemporalEngine(db, event_bus=_event_bus)
    try:
        rule = RecurrenceRule(
            pattern=request.pattern,  # type: ignore[arg-type]
            days_of_week=request.days_of_week,
            day_of_month=request.day_of_month,
            time_window=TimeWindow(
                start=request.time_window.start,
                end=request.time_window.end,
            ) if request.time_window else None,
            flexible=request.flexible,
            max_deferrals=request.max_deferrals,
            end_condition=request.end_condition,  # type: ignore[arg-type]
            end_value=request.end_value,
            interval_days=request.interval_days,
        )
        card = await service.set_task_recurrence(
            task_card_id=card_id,
            rule=rule,
            user_id=current_user.id,
        )
        await db.commit()
        return {"success": True, "data": {"card_id": str(card.id), "metadata": dict(card.metadata_ or {})}}
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# route-tier: authed
@router.post("/occurrences/{occurrence_id}/defer", response_model=dict)
async def defer_occurrence(
    occurrence_id: UUID,
    request: DeferOccurrenceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TemporalEngine(db, event_bus=_event_bus)
    try:
        new_date = None
        if request.new_date:
            from datetime import date

            new_date = date.fromisoformat(request.new_date)
        occurrence = await service.defer_occurrence(
            occurrence_id=occurrence_id,
            user_id=current_user.id,
            new_date=new_date,
        )
        await db.commit()
        return {
            "success": True,
            "data": {
                "occurrence_id": str(occurrence.id),
                "status": occurrence.occurrence_status.value,
                "scheduled_for": occurrence.scheduled_for.isoformat() if occurrence.scheduled_for else None,
                "deferral_count": occurrence.deferral_count,
            },
        }
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# route-tier: authed
@router.post("/{card_id}/snapshot", response_model=dict)
async def create_card_snapshot(
    card_id: UUID,
    request: CreateSnapshotRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CardSnapshotService(db)
    try:
        card = await CardOperationsService(db, event_bus=_event_bus).card_service.get_card(card_id)
        if not card or card.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Card not found")
        snapshot = await service.create_snapshot(
            card_id=card_id,
            include_children=request.include_children,
            max_depth=request.max_depth,
        )
        await db.commit()
        return {
            "success": True,
            "data": {
                "snapshot_id": str(snapshot.id),
                "root_card_id": str(snapshot.root_card_id) if snapshot.root_card_id else None,
                "schema_version": snapshot.schema_version,
                "payload": dict(snapshot.payload or {}),
                "metadata": dict(snapshot.metadata_ or {}),
            },
        }
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# route-tier: authed
@router.post("/{card_id}/share", response_model=dict)
async def share_card(
    card_id: UUID,
    request: ShareCardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ShareService(db, event_bus=_event_bus)
    try:
        share = await service.share_card(
            card_id=card_id,
            user_id=current_user.id,
            scope=request.scope,
            target_id=request.target_id,
            permission=request.permission,
            message=request.message,
            include_children=request.include_children,
            max_depth=request.max_depth,
            metadata=request.metadata,
        )
        await db.commit()
        return {
            "success": True,
            "data": {
                "share_record_id": str(share.id),
                "snapshot_id": str(share.snapshot_id),
                "root_card_id": str(share.root_card_id) if share.root_card_id else None,
                "scope": share.scope.value,
                "permission": share.permission.value,
                "message": share.message,
            },
        }
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# route-tier: authed
@router.get("/shares/{share_record_id}", response_model=dict)
async def get_card_share(
    share_record_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ShareService(db, event_bus=_event_bus)
    share = await service.get_share_record(share_record_id)
    if not share:
        raise HTTPException(status_code=404, detail="Share record not found")
    if share.target_user_id and share.target_user_id != current_user.id and share.shared_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No access to this share")
    return {
        "success": True,
        "data": {
            "share_record_id": str(share.id),
            "snapshot_id": str(share.snapshot_id),
            "root_card_id": str(share.root_card_id) if share.root_card_id else None,
            "shared_by_user_id": str(share.shared_by_user_id),
            "target_user_id": str(share.target_user_id) if share.target_user_id else None,
            "group_id": str(share.group_id) if share.group_id else None,
            "scope": share.scope.value,
            "permission": share.permission.value,
            "message": share.message,
            "adoption_count": share.adoption_count,
            "view_count": share.view_count,
            "snapshot_payload": dict(share.snapshot.payload or {}) if share.snapshot else {},
        },
    }


# route-tier: authed
@router.post("/shares/{share_record_id}/adopt", response_model=dict)
async def adopt_card_share(
    share_record_id: UUID,
    request: AdoptShareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ShareService(db, event_bus=_event_bus)
    try:
        result = await service.adopt_shared_card(
            share_record_id=share_record_id,
            user_id=current_user.id,
            import_mode=request.import_mode,
            modifications=request.modifications,
        )
        await db.commit()
        return {
            "success": True,
            "data": {
                "root_card_id": str(result.root_card.id),
                "root_card_type": result.root_card.card_type.value,
                "legacy_plan_id": str(result.imported_root_plan_id) if result.imported_root_plan_id else None,
                "legacy_task_id": str(result.imported_root_task_id) if result.imported_root_task_id else None,
                "created_card_ids": [str(card.id) for card in result.created_cards],
                "import_mode": request.import_mode.value,
            },
        }
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
