import json
from typing import Any

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.models.user import User
from app.schemas.user_settings import (
    AiOpsDashboardResponse,
    AiOpsExportResponse,
    AiUsageExportResponse,
    AiUsageSummaryResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
)
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
        notification_preferences=await _load_notification_preferences(current_user.id, db),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


async def _update_user_settings_impl(
    payload: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    service = UserSettingsService(db)

    old_record = await service.get_or_create(current_user.id)
    old_values = {
        "transparency_level": old_record.transparency_level,
        "system_update_level": old_record.system_update_level,
        "ai_reasoning_mode": old_record.ai_reasoning_mode,
        "task_reminders_enabled": old_record.task_reminders_enabled,
        "task_reminder_times": old_record.task_reminder_times,
    }
    submitted = payload.model_dump(exclude_none=True)

    record = await service.update_settings(current_user.id, submitted)

    try:
        if "transparency_level" in submitted and old_values["transparency_level"] != record.transparency_level:
            await state_notification_service.notify_user_settings_updated(
                user_id=str(current_user.id),
                setting_field="transparency_level",
                old_value=old_values["transparency_level"],
                new_value=record.transparency_level,
                impact_description="这将影响你未来的学习体验",
                intervention_level="toast",
            )
        elif "system_update_level" in submitted and old_values["system_update_level"] != record.system_update_level:
            await state_notification_service.notify_user_settings_updated(
                user_id=str(current_user.id),
                setting_field="system_update_level",
                old_value=old_values["system_update_level"],
                new_value=record.system_update_level,
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
        notification_preferences=await _load_notification_preferences(current_user.id, db),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


async def _load_notification_preferences(user_id, db: AsyncSession) -> dict[str, Any]:
    try:
        from app.services.personalization.preference_service import PreferenceService

        pref_service = PreferenceService(db, cache_service.redis)
        prefs_center = await pref_service.get_preferences(user_id)
        notif_raw = (prefs_center.explicit or {}).get("notification_preferences", {})
        if isinstance(notif_raw, dict):
            return notif_raw
        if isinstance(notif_raw, str):
            parsed = json.loads(notif_raw)
            return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass
    return {}


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


@router.get("/settings/ai-usage/export", response_model=AiUsageExportResponse)
async def export_user_ai_usage(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AiUsageExportResponse:
    service = UserSettingsService(db)
    payload = await service.get_ai_usage_export(current_user.id, days=days)
    return AiUsageExportResponse(**payload)


@router.get("/settings/ai-ops", response_model=AiOpsDashboardResponse)
async def get_user_ai_ops_dashboard(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AiOpsDashboardResponse:
    service = UserSettingsService(db)
    payload = await service.get_ai_ops_dashboard(current_user.id, days=days)
    return AiOpsDashboardResponse(**payload)


@router.get("/settings/ai-ops/export", response_model=AiOpsExportResponse)
async def export_user_ai_ops_dashboard(
    days: int = Query(default=14, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AiOpsExportResponse:
    service = UserSettingsService(db)
    payload = await service.get_ai_ops_export(current_user.id, days=days)
    return AiOpsExportResponse(**payload)
