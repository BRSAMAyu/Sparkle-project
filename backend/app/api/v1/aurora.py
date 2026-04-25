from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.models.user import User
from app.services.aurora_calibration_card_service import AuroraCalibrationCardService

router = APIRouter(prefix="/aurora", tags=["aurora"])


class CalibrationCardRespondRequest(BaseModel):
    response: Literal["confirm", "incorrect", "mute"]
    reason: str | None = None
    corrected_assumption: str | None = None

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
