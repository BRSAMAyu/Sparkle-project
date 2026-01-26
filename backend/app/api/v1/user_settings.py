from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.user_settings import UserSettingsResponse, UserSettingsUpdate
from app.services.user_settings_service import UserSettingsService

router = APIRouter(prefix="/user", tags=["user_settings"])


@router.get("/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    service = UserSettingsService(db)
    record = await service.get_or_create(current_user.id)
    return UserSettingsResponse(
        transparency_level=record.transparency_level,
        system_update_level=record.system_update_level,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    payload: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    service = UserSettingsService(db)
    record = await service.update_settings(current_user.id, payload.model_dump())
    return UserSettingsResponse(
        transparency_level=record.transparency_level,
        system_update_level=record.system_update_level,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
