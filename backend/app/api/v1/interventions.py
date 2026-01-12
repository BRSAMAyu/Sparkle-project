from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.intervention import InterventionRequest
from app.schemas.intervention import (
    InterventionRequestCreate,
    InterventionRequestResponse,
    InterventionSettingsUpdate,
    InterventionSettingsResponse,
    InterventionFeedbackRequest,
    InterventionFeedbackResponse,
)
from app.services.intervention_service import InterventionService

router = APIRouter(prefix="/interventions", tags=["interventions"])


@router.get("/settings", response_model=InterventionSettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InterventionService(db)
    settings_row = await service.get_or_create_settings(current_user.id, current_user.timezone)
    return settings_row


@router.put("/settings", response_model=InterventionSettingsResponse)
async def update_settings(
    payload: InterventionSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InterventionService(db)
    settings_row = await service.get_or_create_settings(current_user.id, current_user.timezone)
    updated = await service.update_settings(settings_row, payload.model_dump())
    return updated


@router.post("/requests", response_model=InterventionRequestResponse)
async def create_request(
    payload: InterventionRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InterventionService(db)
    try:
        request = await service.create_request(
            actor_id=current_user.id,
            actor_is_admin=current_user.is_superuser,
            payload=payload,
            default_timezone=current_user.timezone,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return request


@router.get("/requests/recent", response_model=List[InterventionRequestResponse])
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
    )
    return feedback
