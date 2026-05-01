from __future__ import annotations

import logging
from datetime import date as date_type
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.aurora.core_session import AuroraCoreSessionService
from app.aurora.predicted_reply_engine import PredictedReplyOptionEngine
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.aurora.runtime_v1.state import AuroraEnergyStore
from app.aurora.runtime_v1.telemetry import AuroraDecisionTelemetryService
from app.core.cache import cache_service
from app.models.user import User
from app.services.aurora_calibration_card_service import AuroraCalibrationCardService
from app.services.aurora_control_surface_service import AuroraControlSurfaceService  # noqa: F401 (used in predicted-options)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aurora", tags=["aurora"])


# ── Request / Response models ──────────────────────────────────────────────────

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


class CoreSessionStartRequest(BaseModel):
    conversation_id: str | None = None
    surface: str = "aurora_modeling"
    session_type: str = "user_initiated"
    scope: str | None = None
    wake_reasons: list[str] = Field(default_factory=list)
    band_status: str = "calibration_available"


class CoreSessionRespondRequest(BaseModel):
    session_id: str
    content: str
    option_id: str | None = None
    semantic_value: str | None = None
    model_write_effect: dict[str, Any] | None = None
    is_freeform: bool = False


class ChipSelectedTelemetryRequest(BaseModel):
    chip_id: str
    telemetry_id: str
    semantic_value: str
    is_freeform: bool = False
    is_disconfirming: bool = False
    context_source: str = ""
    band_status: str = ""
    conversation_id: str | None = None
    session_id: str | None = None
    group_id: str = ""


# ── Existing endpoints ─────────────────────────────────────────────────────────

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


# ── New: Core Session endpoints ────────────────────────────────────────────────

# route-tier: authed
@router.post("/core-session/start")
async def start_core_session(
    payload: CoreSessionStartRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Start or retrieve an active L3 Aurora Core Session for this user."""
    service = AuroraCoreSessionService(cache_service.redis)
    try:
        session = await service.start_session(
            user_id=str(current_user.id),
            conversation_id=payload.conversation_id,
            surface=payload.surface,
            session_type=payload.session_type,
            scope=payload.scope,
            wake_reasons=payload.wake_reasons,
            band_status=payload.band_status,
        )
    except Exception as exc:
        logger.exception("Failed to start Aurora core session")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start Aurora core session",
        ) from exc

    # Record L3 session start in energy store
    energy_store = AuroraEnergyStore(cache_service.redis)
    try:
        await energy_store.record_l3_session(current_user.id)
    except Exception:
        pass

    return session.to_dict()


# route-tier: authed
@router.post("/core-session/respond")
async def respond_core_session(
    payload: CoreSessionRespondRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Process a user response in an active Aurora Core Session."""
    service = AuroraCoreSessionService(cache_service.redis)
    try:
        session = await service.respond(
            user_id=str(current_user.id),
            session_id=payload.session_id,
            content=payload.content,
            option_id=payload.option_id,
            semantic_value=payload.semantic_value,
            model_write_effect=payload.model_write_effect,
            is_freeform=payload.is_freeform,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return session.to_dict()


# route-tier: authed
@router.get("/core-session/current")
async def get_current_core_session(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the user's current active Aurora Core Session, if any."""
    service = AuroraCoreSessionService(cache_service.redis)
    session = await service.get_active_session(str(current_user.id))
    if session is None:
        return {"active": False, "session": None}
    return {"active": True, "session": session.to_dict()}


# route-tier: authed
@router.post("/core-session/{session_id}/close")
async def close_core_session(
    session_id: str = Path(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Close an active Aurora Core Session (user-initiated exit)."""
    service = AuroraCoreSessionService(cache_service.redis)
    try:
        session = await service.close_session(
            user_id=str(current_user.id),
            session_id=session_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return session.to_dict()


# ── New: Predicted reply options endpoint ──────────────────────────────────────

# route-tier: authed
@router.get("/predicted-options")
async def get_predicted_options(
    conversation_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get Aurora-generated predicted reply options for the current state."""
    snapshot = await AuroraControlSurfaceService(db, cache_service.redis).build_snapshot(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )
    return {
        "predicted_reply_options": snapshot.get("predicted_reply_options", []),
        "band_status": snapshot.get("overall_status", "sensing"),
        "energy_level": snapshot.get("energy_level", "L0"),
    }


# ── New: Chip selected telemetry ───────────────────────────────────────────────

# route-tier: authed
@router.post("/telemetry/chip-selected")
async def record_chip_selected(
    payload: ChipSelectedTelemetryRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Record that the user selected a predicted reply chip.

    This feeds into Aurora's model update pipeline. Freeform corrections
    and disconfirming selections are especially important signal sources.
    """
    redis = cache_service.redis
    if redis is not None:
        import json
        import time
        telemetry_key = f"aurora:chip_telemetry:{current_user.id}"
        record = {
            "chip_id": payload.chip_id,
            "telemetry_id": payload.telemetry_id,
            "semantic_value": payload.semantic_value,
            "is_freeform": payload.is_freeform,
            "is_disconfirming": payload.is_disconfirming,
            "context_source": payload.context_source,
            "band_status": payload.band_status,
            "conversation_id": payload.conversation_id,
            "session_id": payload.session_id,
            "group_id": payload.group_id,
            "ts": time.time(),
        }
        try:
            await redis.lpush(telemetry_key, json.dumps(record, ensure_ascii=False))
            await redis.ltrim(telemetry_key, 0, 199)   # keep last 200 selections
            await redis.expire(telemetry_key, 7 * 24 * 3600)
        except Exception:
            pass

    return {"recorded": True, "semantic_value": payload.semantic_value}


