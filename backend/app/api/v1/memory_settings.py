from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.core.cache import cache_service
from app.core.memory_constants import PREFERENCE_KEYS
from app.models.user import User
from app.schemas.memory_settings import MemorySettingsResponse, MemorySettingsUpdate
from app.schemas.push_opt_in import PushOptInResponse, PushOptInUpdate
from app.services.memory_settings_service import MemorySettingsService
from app.services.user_push_opt_in_service import UserPushOptInService

router = APIRouter(prefix="/memory", tags=["memory"])


def _ensure_memory_controls_enabled() -> None:
    if not settings.ENABLE_USER_MEMORY_CONTROLS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory controls disabled")


@router.get("/settings", response_model=MemorySettingsResponse)
async def get_memory_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_controls_enabled()
    service = MemorySettingsService(db, cache_service.redis)
    record = await service.get_or_create(current_user.id)
    return _serialize_settings(record)


@router.put("/settings", response_model=MemorySettingsResponse)
async def update_memory_settings(
    payload: MemorySettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_memory_controls_enabled()

    if payload.blocked_pref_keys is not None:
        invalid = set(payload.blocked_pref_keys) - PREFERENCE_KEYS
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"blocked_pref_keys invalid: {sorted(invalid)}",
            )

    service = MemorySettingsService(db, cache_service.redis)
    record = await service.update_settings(current_user.id, payload.model_dump())
    return _serialize_settings(record)


def _serialize_settings(record: object) -> MemorySettingsResponse:
    return MemorySettingsResponse(
        enabled=getattr(record, "enabled", True),
        allow_preferences=getattr(record, "allow_preferences", True),
        allow_goals=getattr(record, "allow_goals", True),
        allow_episodic=getattr(record, "allow_episodic", True),
        allow_inferred_episodic=getattr(record, "allow_inferred_episodic", True),
        capture_level=getattr(record, "capture_level", "medium"),
        blocked_pref_keys=list(getattr(record, "blocked_pref_keys", []) or []),
        blocked_sources=list(getattr(record, "blocked_sources", []) or []),
        created_at=getattr(record, "created_at", None),
        updated_at=getattr(record, "updated_at", None),
    )


# route-tier: authed
@router.get("/push-settings", response_model=PushOptInResponse)
async def get_push_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = UserPushOptInService(db)
    record = await service.get_or_create(current_user.id)
    return _serialize_push_settings(record)


# route-tier: authed
@router.put("/push-settings", response_model=PushOptInResponse)
async def update_push_settings(
    payload: PushOptInUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = UserPushOptInService(db)
    record = await service.update(current_user.id, payload.model_dump())
    return _serialize_push_settings(record)


def _serialize_push_settings(record: object) -> PushOptInResponse:
    return PushOptInResponse(
        enabled=getattr(record, "enabled", False),
        allow_commitment_follow_up=getattr(record, "allow_commitment_follow_up", False),
        allow_engagement_recovery=getattr(record, "allow_engagement_recovery", False),
        quiet_hours_start=getattr(record, "quiet_hours_start", "22:00"),
        quiet_hours_end=getattr(record, "quiet_hours_end", "08:00"),
        timezone=getattr(record, "timezone", "Asia/Shanghai"),
        created_at=getattr(record, "created_at", None),
        updated_at=getattr(record, "updated_at", None),
    )
