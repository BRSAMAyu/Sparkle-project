from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.intervention import InterventionRequest
from app.models.intervention_adaptive import BehavioralOutcome
from app.models.user import User
from app.schemas.intervention import (
    BehavioralOutcomeRequest,
    InterventionFeedbackRequest,
    InterventionFeedbackResponse,
    InterventionRequestCreate,
    InterventionRequestResponse,
    InterventionSettingsResponse,
    InterventionSettingsUpdate,
    InterventionTriggerRequest,
    PassiveSignalRequest,
)
from app.services.behavioral_outcome_tracker import BehavioralOutcomeTracker
from app.services.intervention_outcome_tracker import InterventionOutcomeTracker
from app.services.intervention_service import InterventionService
from app.services.passive_signal_tracker import PassiveSignalTracker

router = APIRouter(prefix="/interventions", tags=["interventions"])


@router.get("/settings", response_model=InterventionSettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InterventionService(db)
    # Get timezone from push_preference or use default
    timezone = getattr(current_user.push_preference, 'timezone', 'Asia/Shanghai') if current_user.push_preference else 'Asia/Shanghai'
    settings_row = await service.get_or_create_settings(current_user.id, timezone)
    return settings_row


@router.put("/settings", response_model=InterventionSettingsResponse)
async def update_settings(
    payload: InterventionSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InterventionService(db)
    # Get timezone from push_preference or use default
    timezone = getattr(current_user.push_preference, 'timezone', 'Asia/Shanghai') if current_user.push_preference else 'Asia/Shanghai'
    settings_row = await service.get_or_create_settings(current_user.id, timezone)
    updated = await service.update_settings(settings_row, payload.model_dump())
    return updated


@router.post("/requests", response_model=InterventionRequestResponse)
async def create_request(
    payload: InterventionRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InterventionService(db)
    # Get timezone from push_preference or use default
    timezone = getattr(current_user.push_preference, 'timezone', 'Asia/Shanghai') if current_user.push_preference else 'Asia/Shanghai'
    try:
        request = await service.create_request(
            actor_id=current_user.id,
            actor_is_admin=current_user.is_superuser,
            payload=payload,
            default_timezone=timezone,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return request


@router.post("/request", response_model=InterventionRequestResponse)
async def request_intervention(
    payload: InterventionTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InterventionService(db)
    request, _delivery = await service.create_adaptive_intervention(
        user_id=current_user.id,
        trigger_event=payload.type,
        urgency=payload.urgency,
        context=payload.context,
        edge_state=payload.edge_state.model_dump() if payload.edge_state else None,
    )
    return request


@router.get("/requests/recent", response_model=list[InterventionRequestResponse])
async def list_recent(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InterventionService(db)
    return await service.list_recent(current_user.id, limit=limit)


@router.post("/requests/{request_id}/feedback", response_model=InterventionFeedbackResponse)
async def submit_feedback(
    request_id: UUID,
    payload: InterventionFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = await db.get(InterventionRequest, request_id)
    if not request or request.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    service = InterventionService(db)
    feedback = await service.record_feedback(
        request=request,
        user_id=current_user.id,
        feedback_type=payload.feedback_type,
        extra_data=payload.extra_data,
        idempotency_key=payload.idempotency_key,
    )
    return feedback


@router.post("/passive-signals")
async def record_passive_signal(
    payload: PassiveSignalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tracker = PassiveSignalTracker(db)
    signal = await tracker.record(
        user_id=current_user.id,
        signal_type=payload.signal_type,
        intervention_id=payload.intervention_id,
        context=payload.context,
        timestamp=payload.timestamp,
    )
    return {"id": str(signal.id), "status": "ok"}


@router.post("/outcomes")
async def record_outcome(
    payload: BehavioralOutcomeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tracker = BehavioralOutcomeTracker(db)
    outcome = await tracker.record(
        user_id=current_user.id,
        intervention_id=payload.intervention_id,
        outcome_type=payload.outcome_type,
        time_to_outcome=payload.time_to_outcome,
        success=payload.success,
        context=payload.context,
    )
    return {"id": str(outcome.id), "status": "ok"}


@router.get("/outcomes")
async def list_outcomes(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的行为结果记录列表"""
    stmt = (
        select(BehavioralOutcome)
        .where(BehavioralOutcome.user_id == current_user.id)
        .order_by(BehavioralOutcome.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    outcomes = result.scalars().all()

    return [
        {
            "id": str(o.id),
            "intervention_id": str(o.intervention_id) if o.intervention_id else None,
            "outcome_type": o.outcome_type,
            "time_to_outcome": o.time_to_outcome,
            "success": o.success,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in outcomes
    ]


# route-tier: authed
@router.get("/ai-outcome-effectiveness")
async def get_ai_outcome_effectiveness(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取AI干预效果汇总：有效率、按类型分组统计"""
    tracker = InterventionOutcomeTracker()
    summary = await tracker.get_effectiveness_summary(db, user_id=str(current_user.id))
    return summary
