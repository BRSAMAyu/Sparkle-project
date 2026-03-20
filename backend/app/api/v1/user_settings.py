from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.user_settings import AiUsageSummaryResponse, UserSettingsResponse, UserSettingsUpdate
from app.services.state_notification_service import state_notification_service
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
        ai_reasoning_mode=record.ai_reasoning_mode,
        task_reminders_enabled=record.task_reminders_enabled,
        task_reminder_times=record.task_reminder_times,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


async def _update_user_settings_impl(
    payload: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    service = UserSettingsService(db)

    # Get old record to detect changes
    old_record = await service.get_or_create(current_user.id)

    # Update settings
    record = await service.update_settings(current_user.id, payload.model_dump())

    # Detect changes and send notifications
    try:
        if old_record.transparency_level != payload.transparency_level:
            await state_notification_service.notify_user_settings_updated(
                user_id=str(current_user.id),
                setting_field="transparency_level",
                old_value=old_record.transparency_level,
                new_value=payload.transparency_level,
                impact_description="这将影响你未来的学习体验",
                intervention_level="toast",
            )
        elif old_record.system_update_level != payload.system_update_level:
            await state_notification_service.notify_user_settings_updated(
                user_id=str(current_user.id),
                setting_field="system_update_level",
                old_value=old_record.system_update_level,
                new_value=payload.system_update_level,
                impact_description="这将影响系统自动更新的频率",
                intervention_level="toast",
            )
    except Exception as e:
        logger.error(f"Failed to send user_settings_updated notification: {e}")
        # Don't fail the request if notification fails

    return UserSettingsResponse(
        transparency_level=record.transparency_level,
        system_update_level=record.system_update_level,
        ai_reasoning_mode=record.ai_reasoning_mode,
        task_reminders_enabled=record.task_reminders_enabled,
        task_reminder_times=record.task_reminder_times,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    payload: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    return await _update_user_settings_impl(payload=payload, db=db, current_user=current_user)


@router.put("/settings", response_model=UserSettingsResponse)
async def replace_user_settings(
    payload: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    return await _update_user_settings_impl(payload=payload, db=db, current_user=current_user)


@router.get("/settings/ai-usage", response_model=AiUsageSummaryResponse)
async def get_user_ai_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AiUsageSummaryResponse:
    service = UserSettingsService(db)
    summary = await service.get_ai_usage_summary(current_user.id)
    return AiUsageSummaryResponse(**summary)
