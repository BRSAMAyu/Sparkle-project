import os
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.core.cache import cache_service
from app.core.security import get_password_hash, verify_password
from app.db.session import get_db
from app.models.user import PushPreference, User
from app.schemas.user import (
    PasswordChange,
    PushPreferenceResponse,
    PushPreferenceUpdate,
    UserPreferences,
    UserProfile,
    UserUpdate,
)
from app.services.profile_write_service import ProfileWriteService
from app.utils.helpers import save_upload_file

router = APIRouter()

@router.get("/me", response_model=UserProfile)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user profile
    """
    # Eager load push_preference relationship
    from sqlalchemy import select
    result = await db.execute(
        select(PushPreference).where(PushPreference.user_id == current_user.id)
    )
    push_pref = result.scalar_one_or_none()

    # Construct response with push_preferences
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        avatar_status=current_user.avatar_status,
        pending_avatar_url=current_user.pending_avatar_url,
        flame_level=current_user.flame_level,
        flame_brightness=current_user.flame_brightness,
        depth_preference=current_user.depth_preference,
        curiosity_preference=current_user.curiosity_preference,
        is_active=current_user.is_active,
        status=current_user.status,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
        updated_at=current_user.updated_at.isoformat() if current_user.updated_at else "",
        photon_balance=current_user.photon_balance,
        equipped_skin=current_user.equipped_skin,
        equipped_skin_source=current_user.equipped_skin_source,
        equipped_title=current_user.equipped_title,
        equipped_title_source=current_user.equipped_title_source,
        push_preferences=PushPreferenceResponse(
            enable_curiosity=push_pref.enable_curiosity if push_pref else True,
            persona_type=push_pref.persona_type if push_pref else "coach",
            daily_cap=push_pref.daily_cap if push_pref else 5,
            active_slots=push_pref.active_slots if push_pref else [],
            timezone=push_pref.timezone if push_pref else "Asia/Shanghai"
        ) if push_pref else PushPreferenceResponse(
            enable_curiosity=True,
            persona_type="coach",
            daily_cap=5,
            active_slots=[],
            timezone="Asia/Shanghai"
        )
    )

@router.put("/me", response_model=UserProfile)
async def update_me(
    obj_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user profile (nickname, email, preferences)
    """
    if obj_in.nickname is not None:
        current_user.nickname = obj_in.nickname

    if obj_in.email is not None and obj_in.email != current_user.email:
        # Check if email is already taken
        result = await db.execute(select(User).filter(User.email == obj_in.email))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = obj_in.email

    pref_updates = {}
    if obj_in.depth_preference is not None:
        pref_updates["depth_preference"] = obj_in.depth_preference
    if obj_in.curiosity_preference is not None:
        pref_updates["curiosity_preference"] = obj_in.curiosity_preference

    db.add(current_user)
    await db.commit()
    if pref_updates:
        profile_write_service = ProfileWriteService(db, cache_service.redis)
        for pref_key, pref_value in pref_updates.items():
            await profile_write_service.set_explicit_preference(
                user_id=current_user.id,
                pref_key=pref_key,
                pref_value={"value": pref_value},
                evidence_refs=[
                    {"type": "user_state", "id": "profile_edit", "schema_version": "profile_edit.v1"}
                ],
                source_type="user_state",
                source="manual_edit",
            )
    await db.refresh(current_user)

    # Load push_preferences for response
    result = await db.execute(
        select(PushPreference).where(PushPreference.user_id == current_user.id)
    )
    push_pref = result.scalar_one_or_none()

    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        avatar_status=current_user.avatar_status,
        pending_avatar_url=current_user.pending_avatar_url,
        flame_level=current_user.flame_level,
        flame_brightness=current_user.flame_brightness,
        depth_preference=current_user.depth_preference,
        curiosity_preference=current_user.curiosity_preference,
        is_active=current_user.is_active,
        status=current_user.status,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
        updated_at=current_user.updated_at.isoformat() if current_user.updated_at else "",
        photon_balance=current_user.photon_balance,
        equipped_skin=current_user.equipped_skin,
        equipped_skin_source=current_user.equipped_skin_source,
        equipped_title=current_user.equipped_title,
        equipped_title_source=current_user.equipped_title_source,
        push_preferences=PushPreferenceResponse(
            enable_curiosity=push_pref.enable_curiosity if push_pref else True,
            persona_type=push_pref.persona_type if push_pref else "coach",
            daily_cap=push_pref.daily_cap if push_pref else 5,
            active_slots=push_pref.active_slots if push_pref else [],
            timezone=push_pref.timezone if push_pref else "Asia/Shanghai"
        ) if push_pref else PushPreferenceResponse(
            enable_curiosity=True,
            persona_type="coach",
            daily_cap=5,
            active_slots=[],
            timezone="Asia/Shanghai"
        )
    )

@router.post("/me/avatar", response_model=UserProfile)
async def update_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's avatar
    """
    # Create upload directory if not exists
    upload_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    file_extension = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid image format")

    filename = f"{current_user.id}_{uuid4().hex}{file_extension}"
    file_path = os.path.join(upload_dir, filename)

    # Save file
    await save_upload_file(
        file,
        file_path,
        max_size=settings.MAX_UPLOAD_SIZE,
        allowed_extensions=allowed_extensions,
        allowed_content_types=allowed_types,
    )

    # Update user avatar_url
    # In a real app, this should be a full URL
    current_user.avatar_url = f"/uploads/avatars/{filename}"

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    # Load push_preferences for response
    result = await db.execute(
        select(PushPreference).where(PushPreference.user_id == current_user.id)
    )
    push_pref = result.scalar_one_or_none()

    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        avatar_status=current_user.avatar_status,
        pending_avatar_url=current_user.pending_avatar_url,
        flame_level=current_user.flame_level,
        flame_brightness=current_user.flame_brightness,
        depth_preference=current_user.depth_preference,
        curiosity_preference=current_user.curiosity_preference,
        is_active=current_user.is_active,
        status=current_user.status,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
        updated_at=current_user.updated_at.isoformat() if current_user.updated_at else "",
        photon_balance=current_user.photon_balance,
        equipped_skin=current_user.equipped_skin,
        equipped_skin_source=current_user.equipped_skin_source,
        equipped_title=current_user.equipped_title,
        equipped_title_source=current_user.equipped_title_source,
        push_preferences=PushPreferenceResponse(
            enable_curiosity=push_pref.enable_curiosity if push_pref else True,
            persona_type=push_pref.persona_type if push_pref else "coach",
            daily_cap=push_pref.daily_cap if push_pref else 5,
            active_slots=push_pref.active_slots if push_pref else [],
            timezone=push_pref.timezone if push_pref else "Asia/Shanghai"
        ) if push_pref else PushPreferenceResponse(
            enable_curiosity=True,
            persona_type="coach",
            daily_cap=5,
            active_slots=[],
            timezone="Asia/Shanghai"
        )
    )

@router.post("/me/password")
async def change_password(
    obj_in: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change current user's password
    """
    if not verify_password(obj_in.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")

    current_user.hashed_password = get_password_hash(obj_in.new_password)

    db.add(current_user)
    await db.commit()
    return {"detail": "Password updated successfully"}

@router.put("/me/preferences", response_model=UserProfile)
async def update_my_preferences(
    preferences: UserPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's depth and curiosity preferences
    """
    profile_write_service = ProfileWriteService(db, cache_service.redis)
    await profile_write_service.set_explicit_preferences(
        user_id=current_user.id,
        updates={
            "depth_preference": {"value": preferences.learning_depth},
            "curiosity_preference": {"value": preferences.curiosity_level},
        },
        evidence_refs_by_key={
            "depth_preference": [
                {"type": "user_state", "id": "preferences_api", "schema_version": "preferences_api.v1"}
            ],
            "curiosity_preference": [
                {"type": "user_state", "id": "preferences_api", "schema_version": "preferences_api.v1"}
            ],
        },
        source_type="user_state",
        source="manual_edit",
    )
    await db.refresh(current_user)

    # Load push_preferences for response
    result = await db.execute(
        select(PushPreference).where(PushPreference.user_id == current_user.id)
    )
    push_pref = result.scalar_one_or_none()

    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        avatar_status=current_user.avatar_status,
        pending_avatar_url=current_user.pending_avatar_url,
        flame_level=current_user.flame_level,
        flame_brightness=current_user.flame_brightness,
        depth_preference=current_user.depth_preference,
        curiosity_preference=current_user.curiosity_preference,
        is_active=current_user.is_active,
        status=current_user.status,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
        updated_at=current_user.updated_at.isoformat() if current_user.updated_at else "",
        photon_balance=current_user.photon_balance,
        equipped_skin=current_user.equipped_skin,
        equipped_skin_source=current_user.equipped_skin_source,
        equipped_title=current_user.equipped_title,
        equipped_title_source=current_user.equipped_title_source,
        push_preferences=PushPreferenceResponse(
            enable_curiosity=push_pref.enable_curiosity if push_pref else True,
            persona_type=push_pref.persona_type if push_pref else "coach",
            daily_cap=push_pref.daily_cap if push_pref else 5,
            active_slots=push_pref.active_slots if push_pref else [],
            timezone=push_pref.timezone if push_pref else "Asia/Shanghai"
        ) if push_pref else PushPreferenceResponse(
            enable_curiosity=True,
            persona_type="coach",
            daily_cap=5,
            active_slots=[],
            timezone="Asia/Shanghai"
        )
    )


@router.get("/me/push-preference", response_model=PushPreferenceResponse)
async def get_push_preference(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's push notification preferences
    """
    # Fetch or create push preference
    from sqlalchemy import select
    result = await db.execute(
        select(PushPreference).where(PushPreference.user_id == current_user.id)
    )
    push_pref = result.scalar_one_or_none()

    # Create default if not exists
    if not push_pref:
        push_pref = PushPreference(
            user_id=current_user.id,
            enable_curiosity=True,
            persona_type="coach",
            daily_cap=5,
            active_slots=[],
            timezone="Asia/Shanghai"
        )
        db.add(push_pref)
        await db.commit()
        await db.refresh(push_pref)

    return PushPreferenceResponse(
        enable_curiosity=push_pref.enable_curiosity,
        persona_type=push_pref.persona_type,
        daily_cap=push_pref.daily_cap,
        active_slots=push_pref.active_slots,
        timezone=push_pref.timezone
    )


@router.put("/me/push-preference", response_model=PushPreferenceResponse)
async def update_push_preference(
    payload: PushPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's push notification preferences
    """
    updates: dict[str, Any] = {}
    if payload.enable_curiosity is not None:
        updates["enable_curiosity_push"] = payload.enable_curiosity
    if payload.persona_type is not None:
        updates["persona_type"] = payload.persona_type
    if payload.daily_cap is not None:
        updates["daily_cap"] = payload.daily_cap
    if payload.active_slots is not None:
        updates["active_slots"] = payload.active_slots
    if payload.timezone is not None:
        updates["timezone"] = payload.timezone

    if updates:
        profile_write_service = ProfileWriteService(db, cache_service.redis)
        await profile_write_service.set_explicit_preferences(
            user_id=current_user.id,
            updates=updates,
            evidence_refs_by_key={
                key: [{"type": "user_state", "id": "push_preference", "schema_version": "push_preference.v1"}]
                for key in updates
            },
            source_type="user_state",
            source="manual_edit",
        )

    result = await db.execute(
        select(PushPreference).where(PushPreference.user_id == current_user.id)
    )
    push_pref = result.scalar_one_or_none()

    return PushPreferenceResponse(
        enable_curiosity=push_pref.enable_curiosity,
        persona_type=push_pref.persona_type,
        daily_cap=push_pref.daily_cap,
        active_slots=push_pref.active_slots,
        timezone=push_pref.timezone
    )


@router.put("/me/schedule-preferences", response_model=UserProfile)
async def update_schedule_preferences(
    schedule_prefs: dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's weekly schedule preferences (time slots grid)
    """
    profile_write_service = ProfileWriteService(db, cache_service.redis)
    await profile_write_service.set_explicit_preference(
        user_id=current_user.id,
        pref_key="schedule_preferences",
        pref_value=schedule_prefs,
        evidence_refs=[
            {"type": "user_state", "id": "schedule_preferences", "schema_version": "schedule_preferences.v1"}
        ],
        source_type="user_state",
        source="manual_edit",
    )
    await db.refresh(current_user)

    # Load push_preferences for response
    result = await db.execute(
        select(PushPreference).where(PushPreference.user_id == current_user.id)
    )
    push_pref = result.scalar_one_or_none()

    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        avatar_status=current_user.avatar_status,
        pending_avatar_url=current_user.pending_avatar_url,
        flame_level=current_user.flame_level,
        flame_brightness=current_user.flame_brightness,
        depth_preference=current_user.depth_preference,
        curiosity_preference=current_user.curiosity_preference,
        is_active=current_user.is_active,
        status=current_user.status,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
        updated_at=current_user.updated_at.isoformat() if current_user.updated_at else "",
        photon_balance=current_user.photon_balance,
        equipped_skin=current_user.equipped_skin,
        equipped_skin_source=current_user.equipped_skin_source,
        equipped_title=current_user.equipped_title,
        equipped_title_source=current_user.equipped_title_source,
        push_preferences=PushPreferenceResponse(
            enable_curiosity=push_pref.enable_curiosity if push_pref else True,
            persona_type=push_pref.persona_type if push_pref else "coach",
            daily_cap=push_pref.daily_cap if push_pref else 5,
            active_slots=push_pref.active_slots if push_pref else [],
            timezone=push_pref.timezone if push_pref else "Asia/Shanghai"
        ) if push_pref else PushPreferenceResponse(
            enable_curiosity=True,
            persona_type="coach",
            daily_cap=5,
            active_slots=[],
            timezone="Asia/Shanghai"
        )
    )
