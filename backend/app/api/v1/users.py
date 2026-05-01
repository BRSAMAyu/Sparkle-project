"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations
import os
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.core.auth_audit_service import auth_audit_service
from app.core.cache import cache_service
from app.core.security import get_password_hash, set_user_revoked_before, verify_password
from app.db.session import get_db
from app.models.auth_security import AuthAuditAction, AuthAuditLog
from app.models.user import PushPreference, User, UserStatus
from app.schemas.user import (
    AvatarStatus,
    AuthAuditLogInfo,
    DeleteAccountRequest,
    LinkSocialRequest,
    PasswordChange,
    PushPreferenceResponse,
    PushPreferenceUpdate,
    SetPasswordRequest,
    SocialAccountStatus,
    UnlinkSocialRequest,
    UserPreferences,
    UserProfile,
    UserSessionInfo,
    UserUpdate,
)
from app.services.auth_session_service import auth_session_service
from app.services.profile_write_service import ProfileWriteService
from app.utils.helpers import save_upload_file

router = APIRouter()
SESSION_TTL_SECONDS = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _linked_providers(user: User) -> list[str]:
    providers: list[str] = []
    if user.google_id:
        providers.append("google")
    if user.apple_id:
        providers.append("apple")
    if user.wechat_unionid:
        providers.append("wechat")
    return providers


async def _get_push_pref(db: AsyncSession, user_id: str) -> PushPreference | None:
    result = await db.execute(select(PushPreference).where(PushPreference.user_id == user_id))
    return result.scalar_one_or_none()


def _push_pref_response(push_pref: PushPreference | None) -> PushPreferenceResponse:
    if push_pref:
        return PushPreferenceResponse(
            enable_curiosity=push_pref.enable_curiosity,
            persona_type=push_pref.persona_type,
            daily_cap=push_pref.daily_cap,
            active_slots=push_pref.active_slots,
            timezone=push_pref.timezone,
        )
    return PushPreferenceResponse(
        enable_curiosity=True,
        persona_type="coach",
        daily_cap=5,
        active_slots=[],
        timezone="Asia/Shanghai",
    )


def _build_user_profile(user: User, push_pref: PushPreference | None) -> UserProfile:
    return UserProfile(
        id=user.id,
        username=user.username,
        email=user.email,
        email_verified=user.email_verified,
        password_login_enabled=user.password_login_enabled,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        avatar_status=user.avatar_status,
        pending_avatar_url=user.pending_avatar_url,
        flame_level=user.flame_level,
        flame_brightness=user.flame_brightness,
        depth_preference=user.depth_preference,
        curiosity_preference=user.curiosity_preference,
        schedule_preferences=user.schedule_preferences,
        weather_preferences=user.weather_preferences,
        is_active=user.is_active,
        status=user.status,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else "",
        photon_balance=user.photon_balance,
        equipped_skin=user.equipped_skin,
        equipped_skin_source=user.equipped_skin_source,
        equipped_title=user.equipped_title,
        equipped_title_source=user.equipped_title_source,
        registration_source=user.registration_source,
        linked_providers=_linked_providers(user),
        tos_version=user.tos_version,
        privacy_version=user.privacy_version,
        push_preferences=_push_pref_response(push_pref),
    )


def _current_session_id(request: Request) -> str | None:
    payload = getattr(request.state, "token_payload", None)
    if not payload:
        return None
    session_id = payload.get("sid")
    return str(session_id) if session_id else None


async def _require_social_reauth(current_user: User, provider: str, provider_token: str) -> None:
    from app.api.v1.auth import _verify_social_identity
    from app.schemas.user import SocialLoginRequest

    social_id, _ = await _verify_social_identity(SocialLoginRequest(provider=provider, token=provider_token))
    expected = {
        "google": current_user.google_id,
        "apple": current_user.apple_id,
        "wechat": current_user.wechat_unionid,
    }.get(provider)
    if not expected or expected != social_id:
        raise HTTPException(status_code=403, detail="社交账号验证失败")


@router.get("/me", response_model=UserProfile)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user profile.
    """
    push_pref = await _get_push_pref(db, current_user.id)
    return _build_user_profile(current_user, push_pref)


@router.put("/me", response_model=UserProfile)
async def update_me(
    obj_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user profile (nickname, email, preferences).
    """
    if obj_in.nickname is not None:
        current_user.nickname = obj_in.nickname

    if obj_in.email is not None and obj_in.email != current_user.email:
        result = await db.execute(select(User).filter(User.email == obj_in.email, User.id != current_user.id))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = obj_in.email
        current_user.email_verified = False

    if obj_in.avatar_url is not None:
        current_user.avatar_url = obj_in.avatar_url
        current_user.pending_avatar_url = None
        current_user.avatar_status = AvatarStatus.APPROVED

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
    push_pref = await _get_push_pref(db, current_user.id)
    return _build_user_profile(current_user, push_pref)


@router.post("/me/avatar", response_model=UserProfile)
async def update_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user's avatar.
    """
    upload_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(upload_dir, exist_ok=True)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    file_extension = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid image format")

    filename = f"{current_user.id}_{uuid4().hex}{file_extension}"
    file_path = os.path.join(upload_dir, filename)

    await save_upload_file(
        file,
        file_path,
        max_size=settings.MAX_UPLOAD_SIZE,
        allowed_extensions=allowed_extensions,
        allowed_content_types=allowed_types,
    )

    current_user.avatar_url = f"/uploads/avatars/{filename}"
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    push_pref = await _get_push_pref(db, current_user.id)
    return _build_user_profile(current_user, push_pref)


@router.post("/me/password")
async def change_password(
    obj_in: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change current user's password.
    """
    if not current_user.email_verified:
        raise HTTPException(status_code=403, detail="请先验证邮箱后再修改密码")

    if not verify_password(obj_in.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")

    current_user.hashed_password = get_password_hash(obj_in.new_password)
    current_user.password_login_enabled = True

    db.add(current_user)
    await db.commit()
    auth_audit_service.schedule_log(
        AuthAuditAction.PASSWORD_CHANGE,
        user_id=str(current_user.id),
        request=request,
    )
    return {"detail": "Password updated successfully"}


@router.post("/me/set-password")
async def set_password(
    obj_in: SetPasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Set password for social-login users or verified accounts without requiring the old password.
    """
    trusted_social_sources = {"google", "apple", "wechat"}
    if not current_user.email_verified and current_user.registration_source not in trusted_social_sources:
        raise HTTPException(status_code=403, detail="请先验证邮箱后再设置密码")

    current_user.hashed_password = get_password_hash(obj_in.new_password)
    current_user.password_login_enabled = True
    current_user.token_revoked_before = _utcnow_naive()

    db.add(current_user)
    await db.flush()
    await set_user_revoked_before(str(current_user.id), current_user.token_revoked_before)
    await auth_session_service.revoke_all_sessions_for_user(
        db,
        user_id=str(current_user.id),
        ttl_seconds=SESSION_TTL_SECONDS,
    )
    auth_audit_service.schedule_log(
        AuthAuditAction.PASSWORD_CHANGE,
        user_id=str(current_user.id),
        request=request,
        metadata={"mode": "set_password"},
    )
    return {"detail": "Password set successfully. Please log in again."}


@router.get("/me/social-accounts", response_model=list[SocialAccountStatus])
async def get_social_accounts(current_user: User = Depends(get_current_user)):
    return [
        SocialAccountStatus(provider="google", linked=bool(current_user.google_id)),
        SocialAccountStatus(provider="apple", linked=bool(current_user.apple_id)),
        SocialAccountStatus(provider="wechat", linked=bool(current_user.wechat_unionid)),
    ]


@router.post("/me/link-social")
async def link_social(
    payload: LinkSocialRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.email_verified:
        raise HTTPException(status_code=403, detail="请先验证邮箱后再绑定社交账号")

    from app.api.v1.auth import _verify_social_identity
    from app.schemas.user import SocialLoginRequest

    social_id, user_info = await _verify_social_identity(
        SocialLoginRequest(provider=payload.provider, token=payload.token, openid=payload.openid),
    )

    if payload.provider == "google":
        existing = await db.execute(select(User).where(User.google_id == social_id, User.id != current_user.id))
        if existing.scalars().first():
            raise HTTPException(status_code=409, detail="该 Google 账号已绑定其他用户")
        current_user.google_id = social_id
    elif payload.provider == "apple":
        existing = await db.execute(select(User).where(User.apple_id == social_id, User.id != current_user.id))
        if existing.scalars().first():
            raise HTTPException(status_code=409, detail="该 Apple 账号已绑定其他用户")
        current_user.apple_id = social_id
    elif payload.provider == "wechat":
        existing = await db.execute(select(User).where(User.wechat_unionid == social_id, User.id != current_user.id))
        if existing.scalars().first():
            raise HTTPException(status_code=409, detail="该微信账号已绑定其他用户")
        current_user.wechat_unionid = social_id
    else:
        raise HTTPException(status_code=400, detail="暂不支持这种登录方式")

    if payload.provider in {"google", "apple"}:
        current_user.email_verified = True
    if user_info.get("picture") and not current_user.avatar_url:
        current_user.avatar_url = user_info["picture"]

    db.add(current_user)
    await db.commit()
    auth_audit_service.schedule_log(
        AuthAuditAction.SOCIAL_LINK,
        user_id=str(current_user.id),
        request=request,
        metadata={"provider": payload.provider},
    )
    return {"detail": f"{payload.provider} 绑定成功"}


@router.post("/me/unlink-social")
async def unlink_social(
    payload: UnlinkSocialRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    linked = _linked_providers(current_user)
    if payload.provider not in linked:
        raise HTTPException(status_code=400, detail="该社交账号未绑定")

    remaining_social = [provider for provider in linked if provider != payload.provider]
    if not current_user.password_login_enabled and not remaining_social:
        raise HTTPException(status_code=400, detail="无法解绑最后一个登录方式，请先设置密码或绑定其他账号")

    if payload.provider == "google":
        current_user.google_id = None
    elif payload.provider == "apple":
        current_user.apple_id = None
    elif payload.provider == "wechat":
        current_user.wechat_unionid = None
    else:
        raise HTTPException(status_code=400, detail="暂不支持这种登录方式")

    db.add(current_user)
    await db.commit()
    auth_audit_service.schedule_log(
        AuthAuditAction.SOCIAL_UNLINK,
        user_id=str(current_user.id),
        request=request,
        metadata={"provider": payload.provider},
    )
    return {"detail": f"{payload.provider} 已解绑"}


@router.get("/me/sessions", response_model=list[UserSessionInfo])
async def get_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_sid = _current_session_id(request)
    sessions = await auth_session_service.list_sessions(db, str(current_user.id))
    return [
        UserSessionInfo(
            session_id=session.session_id,
            device_id=session.device_id,
            device_name=session.device_name,
            device_type=session.device_type,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            is_active=session.is_active,
            is_current=session.session_id == current_sid,
            created_at=session.created_at,
            last_active_at=session.last_active_at,
        )
        for session in sessions
    ]


@router.delete("/me/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_sid = _current_session_id(request)
    if session_id == current_sid:
        raise HTTPException(status_code=400, detail="请使用注销功能退出当前设备")

    session = await auth_session_service.revoke_session_by_id(
        db,
        user_id=str(current_user.id),
        session_id=session_id,
        ttl_seconds=SESSION_TTL_SECONDS,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    auth_audit_service.schedule_log(
        AuthAuditAction.LOGOUT,
        user_id=str(current_user.id),
        request=request,
        metadata={"session_id": session_id, "mode": "remote_revoke"},
    )
    return {"detail": "该设备已下线"}


@router.delete("/me/sessions")
async def revoke_other_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    revoked = await auth_session_service.revoke_all_other_sessions(
        db,
        user_id=str(current_user.id),
        current_session_id=_current_session_id(request),
        ttl_seconds=SESSION_TTL_SECONDS,
    )
    auth_audit_service.schedule_log(
        AuthAuditAction.LOGOUT,
        user_id=str(current_user.id),
        request=request,
        metadata={"mode": "revoke_others", "revoked": revoked},
    )
    return {"detail": f"已下线 {revoked} 个其他设备"}


@router.get("/me/security-log", response_model=list[AuthAuditLogInfo])
async def get_security_log(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuthAuditLog)
        .where(AuthAuditLog.user_id == current_user.id)
        .order_by(AuthAuditLog.occurred_at.desc())
        .offset(offset)
        .limit(limit),
    )
    items = result.scalars().all()
    return [
        AuthAuditLogInfo(
            action=item.action,
            ip_address=item.ip_address,
            user_agent=item.user_agent,
            metadata=item.metadata_ or {},
            occurred_at=item.occurred_at,
        )
        for item in items
    ]


@router.post("/me/delete-account")
async def delete_account(
    payload: DeleteAccountRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.confirmation.strip().upper() != "DELETE":
        raise HTTPException(status_code=400, detail="请输入 DELETE 以确认注销")

    if current_user.registration_source == "guest":
        pass
    elif payload.password:
        if not current_user.password_login_enabled:
            raise HTTPException(status_code=400, detail="当前账号未启用密码登录，请使用社交验证")
        if not verify_password(payload.password, current_user.hashed_password):
            raise HTTPException(status_code=403, detail="密码错误")
    elif payload.provider and payload.provider_token:
        await _require_social_reauth(current_user, payload.provider, payload.provider_token)
    else:
        raise HTTPException(status_code=400, detail="请使用密码或社交账号重新验证身份")

    deleted_marker = uuid4().hex
    auth_audit_service.schedule_log(
        AuthAuditAction.ACCOUNT_DELETE,
        user_id=str(current_user.id),
        request=request,
        metadata={"registration_source": current_user.registration_source},
    )

    current_user.is_active = False
    current_user.status = UserStatus.OFFLINE
    current_user.username = f"deleted_{deleted_marker[:12]}"
    current_user.email = f"deleted_{deleted_marker}@deleted.local"
    current_user.nickname = "Deleted User"
    current_user.avatar_url = None
    current_user.pending_avatar_url = None
    current_user.google_id = None
    current_user.apple_id = None
    current_user.wechat_unionid = None
    current_user.email_verified = False
    current_user.password_login_enabled = False
    current_user.registration_source = "deleted"
    current_user.token_revoked_before = _utcnow_naive()
    current_user.soft_delete()

    db.add(current_user)
    await set_user_revoked_before(str(current_user.id), current_user.token_revoked_before)
    await auth_session_service.revoke_all_sessions_for_user(
        db,
        user_id=str(current_user.id),
        ttl_seconds=SESSION_TTL_SECONDS,
    )
    await db.commit()

    # Schedule hard-delete 30 days from now (GDPR compliance)
    _THIRTY_DAYS = 30 * 24 * 60 * 60
    try:
        from app.core.celery_tasks import purge_deleted_account
        purge_deleted_account.apply_async(
            args=[str(current_user.id)],
            countdown=_THIRTY_DAYS,
        )
    except Exception:
        pass  # Purge will be retried; anonymisation already completed

    return {"detail": "账号已注销，个人数据已匿名化。30天后将永久删除全部数据，期间如需恢复请联系客服。"}


@router.put("/me/preferences", response_model=UserProfile)
async def update_my_preferences(
    preferences: UserPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user's depth and curiosity preferences.
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

    push_pref = await _get_push_pref(db, current_user.id)
    return _build_user_profile(current_user, push_pref)


@router.get("/me/push-preference", response_model=PushPreferenceResponse)
async def get_push_preference(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    push_pref = await _get_push_pref(db, current_user.id)
    if not push_pref:
        push_pref = PushPreference(
            user_id=current_user.id,
            enable_curiosity=True,
            persona_type="coach",
            daily_cap=5,
            active_slots=[],
            timezone="Asia/Shanghai",
        )
        db.add(push_pref)
        await db.commit()
        await db.refresh(push_pref)

    return _push_pref_response(push_pref)


@router.put("/me/push-preference", response_model=PushPreferenceResponse)
async def update_push_preference(
    payload: PushPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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

    push_pref = await _get_push_pref(db, current_user.id)
    return _push_pref_response(push_pref)


@router.put("/me/schedule-preferences", response_model=UserProfile)
async def update_schedule_preferences(
    schedule_prefs: dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user's weekly schedule preferences (time slots grid).
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

    push_pref = await _get_push_pref(db, current_user.id)
    return _build_user_profile(current_user, push_pref)


@router.get("/{user_id}", summary="获取用户公开资料")
async def get_user_public_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a user's public profile by ID."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "id": str(target_user.id),
        "username": target_user.username,
        "nickname": target_user.nickname,
        "avatar_url": target_user.avatar_url,
        "flame_level": target_user.flame_level,
        "flame_brightness": target_user.flame_brightness,
        "status": target_user.status.value if target_user.status else "offline",
    }
