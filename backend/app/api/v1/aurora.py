from __future__ import annotations

from datetime import date as date_type
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.aurora.runtime_v1.telemetry import AuroraDecisionTelemetryService
from app.core.cache import cache_service
from app.models.user import User
from app.services.aurora_calibration_card_service import AuroraCalibrationCardService

router = APIRouter(prefix="/aurora", tags=["aurora"])


class CalibrationCardRespondRequest(BaseModel):
    response: Literal["confirm", "incorrect", "mute"]
    reason: str | None = None
    corrected_assumption: str | None = None


class DailyStartupResponse(BaseModel):
    message: str
    today_focus: str
    estimated_minutes: int
    adjustment_reason: str


class ComebackContextResponse(BaseModel):
    title: str
    message: str
    days_away: int
    days_remaining: int
    subject: str
    next_task_title: str
    recent_task_summary: str
    light_restart_suggestion: str
    plan_id: str


# route-tier: authed
@router.get("/daily-startup", response_model=DailyStartupResponse)
async def get_daily_startup(
    plan_id: str = Query(..., min_length=1),
    user_id: UUID | None = Query(default=None),
    session_date: date_type | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailyStartupResponse:
    resolved_user_id = user_id or current_user.id
    if str(resolved_user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot request daily startup for another user",
        )

    service = AuroraRuntimeV1Service(cache_service.redis)
    try:
        payload = await service.get_daily_startup_message(
            active_db=db,
            user_id=resolved_user_id,
            plan_id=plan_id,
            session_date=session_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return DailyStartupResponse(**payload)


# route-tier: authed
@router.get("/comeback-context")
async def get_comeback_context(
    user_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    resolved_user_id = user_id or current_user.id
    if str(resolved_user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot request comeback context for another user",
        )

    service = AuroraRuntimeV1Service(cache_service.redis)
    payload = await service.get_comeback_context(
        active_db=db,
        user_id=resolved_user_id,
    )
    if payload is None:
        return {}
    return ComebackContextResponse(**payload).model_dump()


# route-tier: authed
@router.get("/calibration-cards")
async def get_calibration_cards(
    plan_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = AuroraCalibrationCardService(db, cache_service.redis)
    return await service.list_cards(user_id=current_user.id, plan_id=plan_id)


# route-tier: authed
@router.post("/calibration-cards/{card_id}/respond")
async def respond_calibration_card(
    payload: CalibrationCardRespondRequest,
    card_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = AuroraCalibrationCardService(db, cache_service.redis)
    try:
        return await service.respond(
            user_id=current_user.id,
            card_id=card_id,
            response=payload.response,
            reason=payload.reason,
            corrected_assumption=payload.corrected_assumption,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# route-tier: admin
@router.get("/telemetry/summary")
async def get_aurora_telemetry_summary(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> dict[str, Any]:
    del current_user
    return await AuroraDecisionTelemetryService(db).build_summary(days=days)
