"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

Authentication API
Login, Register, Refresh Token, Social Login
"""

from __future__ import annotations
import asyncio
import uuid
from datetime import timezone, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth_audit_service import auth_audit_service
from app.core.account_lockout import account_lockout_service
from app.core.rate_limiting import limiter
from app.core.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    set_user_revoked_before,
    verify_password,
)
from app.core.cache import cache_service
from app.core.event_bus import UserRegisteredEvent
from app.core.email_service import email_service
from app.db.session import get_db
from app.models.auth_security import AuthAuditAction
from app.models.community import GroupRole
from app.models.user import User
from app.schemas.user import (
    ForgotPasswordRequest,
    LogoutRequest,
    SocialLoginRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    UpgradeGuestRequest,
    UpgradeGuestSocialRequest,
    UserBase,
    UserLogin,
    UserRegister,
    UserProfile,
    VerifyEmailRequest,
)
from app.api.deps import get_current_user
from app.services.permission_service import PermissionService
from app.services.auth_session_service import auth_session_service
from app.services.stage33_journey_event_service import Stage33JourneyEventService

router = APIRouter()

# Relax rate limits in development to avoid blocking during iterative testing.
AUTH_RATE_LIMIT = "50/15minutes" if settings.DEBUG else "5/15minutes"
SOCIAL_RATE_LIMIT = "50/15minutes" if settings.DEBUG else "5/15minutes"
REFRESH_RATE_LIMIT = "100/15minutes" if settings.DEBUG else "10/15minutes"
LOGOUT_RATE_LIMIT = "500/15minutes" if settings.DEBUG else "30/15minutes"
FORGOT_RATE_LIMIT = "30/15minutes" if settings.DEBUG else "3/15minutes"
VERIFY_RATE_LIMIT = "30/15minutes" if settings.DEBUG else "5/15minutes"
RESET_RATE_LIMIT = "30/15minutes" if settings.DEBUG else "5/15minutes"

PASSWORD_RESET_TTL_SECONDS = 15 * 60
EMAIL_VERIFY_TTL_SECONDS = 24 * 60 * 60
SESSION_TTL_SECONDS = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def _linked_providers(user: User) -> list[str]:
    providers: list[str] = []
    if user.google_id:
        providers.append("google")
    if user.apple_id:
        providers.append("apple")
    if user.wechat_unionid:
        providers.append("wechat")
    return providers


def _build_user_profile(user: User) -> UserProfile:
    return UserProfile.model_validate(user).model_copy(
        update={
            "linked_providers": _linked_providers(user),
            "password_login_enabled": user.password_login_enabled,
            "tos_version": user.tos_version,
            "privacy_version": user.privacy_version,
        },
    )


def _validate_terms_acceptance(
    accepted_tos: bool,
    accepted_privacy: bool,
) -> None:
    if not accepted_tos or not accepted_privacy:
        raise HTTPException(status_code=400, detail="请先同意用户协议和隐私政策")


def _apply_terms_acceptance(
    user: User,
    *,
    tos_version: str | None,
    privacy_version: str | None,
    agreed_locale: str | None,
) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user.agreed_to_tos_at = now
    user.agreed_to_privacy_at = now
    user.tos_version = tos_version or "v1"
    user.privacy_version = privacy_version or "v1"
    user.agreed_locale = agreed_locale


def _default_community_permissions() -> list[str]:
    return sorted(
        permission.value
        for permission in PermissionService.get_role_permissions(GroupRole.MEMBER)
    )


async def _issue_auth_tokens(
    *,
    db: AsyncSession,
    user: User,
    request: Request,
    session_id: str | None = None,
    access_expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effective_session_id = session_id or uuid.uuid4().hex
    claims = {"sub": str(user.id), "sid": effective_session_id, **(extra_claims or {})}
    access_token_expires = access_expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data=claims,
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(data=claims)
    refresh_payload = await decode_token(refresh_token, expected_type="refresh")
    await auth_session_service.upsert_session(
        db,
        user_id=str(user.id),
        session_id=effective_session_id,
        refresh_token_jti=refresh_payload.get("jti"),
        request=request,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "token": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
    }


async def _verify_apple_identity_token(token: str) -> tuple[str, dict[str, Any]]:
    import httpx
    from jose import jwt

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    alg = header.get("alg", "RS256")

    timeout = httpx.Timeout(5.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get("https://appleid.apple.com/auth/keys")
        response.raise_for_status()
        keys = response.json().get("keys", [])

    key = next((item for item in keys if item.get("kid") == kid), None)
    if key is None:
        raise HTTPException(status_code=401, detail="Apple 令牌验证失败，请重试")

    claims = jwt.decode(
        token,
        key,
        algorithms=[alg],
        audience=settings.APPLE_CLIENT_ID or None,
        issuer="https://appleid.apple.com",
        options={"verify_aud": bool(settings.APPLE_CLIENT_ID)},
    )
    return str(claims.get("sub") or ""), claims


async def _verify_social_identity(data: SocialLoginRequest) -> tuple[str, dict[str, Any]]:
    social_id = None
    user_info: dict[str, Any] = {}

    try:
        if data.provider == "google":
            import httpx

            timeout = httpx.Timeout(5.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"id_token": data.token},
                )
                if response.status_code != 200:
                    raise HTTPException(status_code=401, detail="Google 令牌验证失败，请重试")

                token_info = response.json()
                if token_info.get("iss") not in ["https://accounts.google.com", "accounts.google.com"]:
                    raise HTTPException(status_code=401, detail="Google 令牌验证失败，请重试")
                if settings.GOOGLE_CLIENT_ID and token_info.get("aud") != settings.GOOGLE_CLIENT_ID:
                    raise HTTPException(status_code=401, detail="Google 令牌验证失败，请重试")
                if token_info.get("email_verified") not in (True, "true", "True", "1"):
                    raise HTTPException(status_code=401, detail="Google 令牌验证失败，请重试")

                social_id = token_info.get("sub")
                user_info = {
                    "email": token_info.get("email"),
                    "name": token_info.get("name"),
                    "picture": token_info.get("picture"),
                    "email_verified": True,
                }

        elif data.provider == "apple":
            social_id, claims = await _verify_apple_identity_token(data.token)
            user_info = {
                "email": claims.get("email") or data.email,
                "name": data.nickname,
                "picture": data.avatar_url,
                "email_verified": True,
            }

        elif data.provider == "wechat":
            import httpx

            timeout = httpx.Timeout(5.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                if not data.openid:
                    if not settings.WECHAT_APP_ID or not settings.WECHAT_APP_SECRET:
                        raise HTTPException(status_code=500, detail="服务器未配置微信登录")

                    token_resp = await client.get(
                        "https://api.weixin.qq.com/sns/oauth2/access_token",
                        params={
                            "appid": settings.WECHAT_APP_ID,
                            "secret": settings.WECHAT_APP_SECRET,
                            "code": data.token,
                            "grant_type": "authorization_code",
                        },
                    )
                    token_data = token_resp.json()
                    if "errcode" in token_data and token_data["errcode"] != 0:
                        logger.error(f"WeChat code exchange failed: {token_data}")
                        raise HTTPException(status_code=401, detail="微信登录失败，请重试")

                    social_id = token_data["openid"]
                    access_token = token_data["access_token"]
                    user_resp = await client.get(
                        "https://api.weixin.qq.com/sns/userinfo",
                        params={
                            "access_token": access_token,
                            "openid": social_id,
                            "lang": "zh_CN",
                        },
                    )
                    user_data = user_resp.json()
                    if "errcode" in user_data and user_data["errcode"] != 0:
                        logger.error(f"WeChat user info failed: {user_data}")
                        raise HTTPException(status_code=401, detail="获取微信用户信息失败")
                    user_info = {
                        "email": None,
                        "name": user_data.get("nickname"),
                        "picture": user_data.get("headimgurl"),
                        "email_verified": False,
                    }
                else:
                    response = await client.get(
                        "https://api.weixin.qq.com/sns/auth",
                        params={"access_token": data.token, "openid": data.openid},
                    )
                    if response.status_code != 200:
                        raise HTTPException(status_code=401, detail="微信令牌验证失败，请重试")

                    result = response.json()
                    if result.get("errcode") != 0:
                        raise HTTPException(status_code=401, detail="微信令牌验证失败，请重试")

                    social_id = data.openid
                    user_info = {
                        "email": None,
                        "name": data.nickname,
                        "picture": data.avatar_url,
                        "email_verified": False,
                    }
        else:
            raise HTTPException(status_code=400, detail="暂不支持这种登录方式")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Social login verification failed for {data.provider}: {e}")
        raise HTTPException(status_code=401, detail="社交登录验证失败")

    if not social_id:
        raise HTTPException(status_code=401, detail="无法验证登录令牌")
    return social_id, user_info

@router.post("/register", response_model=Any)
@limiter.limit(AUTH_RATE_LIMIT)
async def register(
    request: Request,
    data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    """
    _validate_terms_acceptance(data.accepted_tos, data.accepted_privacy)
    logger.info(f"Registration attempt: username={data.username}")

    # C1 Security Fix: 统一检查用户名和邮箱，返回通用错误消息（防止枚举攻击）
    existing_user = await db.execute(
        select(User).where(
            (User.username == data.username) | (User.email == data.email)
        )
    )
    if existing_user.scalars().first():
        # 统一返回通用消息，无法区分是用户名还是邮箱已存在
        logger.warning(f"Registration failed: duplicate username or email")
        raise HTTPException(
            status_code=400,
            detail="注册失败，请检查输入的用户名和邮箱"
        )

    # Create user
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=get_password_hash(data.password),
        password_login_enabled=True,
        nickname=data.nickname or data.username,
        registration_source="email",
        is_active=True,
    )
    _apply_terms_acceptance(
        user,
        tos_version=data.tos_version,
        privacy_version=data.privacy_version,
        agreed_locale=data.agreed_locale,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"User registered successfully: {user.username} (ID: {user.id})")

    # M2 Security Fix: Send verification email via Celery queue (rate-limited)
    try:
        verify_token = uuid.uuid4().hex
        await cache_service.set(
            f"email_verify:{verify_token}",
            str(user.id),
            ttl=EMAIL_VERIFY_TTL_SECONDS,
        )
        # 使用 Celery 任务替代 asyncio.create_task
        from app.core.celery_tasks import send_verification_email_task
        send_verification_email_task.delay(
            to_email=user.email,
            verify_token=verify_token,
            username=user.nickname or user.username
        )
    except Exception as e:
        logger.warning(f"Failed to schedule verification email: {e}")

    auth_audit_service.schedule_log(
        AuthAuditAction.REGISTER,
        user_id=str(user.id),
        request=request,
        metadata={
            "registration_source": "email",
            "default_community_permissions": _default_community_permissions(),
        },
    )
    await Stage33JourneyEventService.publish(
        "user.registered",
        UserRegisteredEvent(
            user_id=str(user.id),
            username=user.username,
            registration_source="email",
            metadata={
                "nickname": user.nickname or user.username,
                "default_community_permissions": _default_community_permissions(),
            },
        ).to_dict(),
    )

    return {
        "user": _build_user_profile(user),
        **await _issue_auth_tokens(db=db, user=user, request=request),
    }

@router.post("/login", response_model=Any)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(
    request: Request,
    data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    User login with username/email and password
    """
    logger.info(f"Login attempt: identifier={data.username or data.email}")
    login_id = data.username or data.email
    if not login_id:
        raise HTTPException(status_code=422, detail="用户名或邮箱不能为空")

    # Check username or email
    result = await db.execute(
        select(User).where((User.username == login_id) | (User.email == login_id))
    )
    user = result.scalars().first()

    if not user:
        logger.warning(f"Login attempt for non-existent user: {login_id}")
        auth_audit_service.schedule_log(
            AuthAuditAction.LOGIN_FAILED,
            request=request,
            metadata={"identifier": login_id, "reason": "user_not_found"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确，请重试",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is locked
    if await account_lockout_service.check_and_handle_lockout(str(user.id), db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="登录失败次数过多，账号已临时锁定，请15分钟后再试"
        )

    if not verify_password(data.password, user.hashed_password):
        logger.warning(f"Login failed for user: {login_id}")
        # Record failed attempt
        await account_lockout_service.record_failed_login(str(user.id))
        auth_audit_service.schedule_log(
            AuthAuditAction.LOGIN_FAILED,
            user_id=str(user.id),
            request=request,
            metadata={"identifier": login_id, "reason": "bad_password"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确，请重试",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {user.username}")
        raise HTTPException(status_code=400, detail="账号暂时无法使用，请联系客服")

    # Successful login - reset failed attempts
    await account_lockout_service.handle_successful_login(str(user.id))
    auth_audit_service.schedule_log(
        AuthAuditAction.LOGIN,
        user_id=str(user.id),
        request=request,
        metadata={"registration_source": user.registration_source},
    )

    return {
        **await _issue_auth_tokens(db=db, user=user, request=request),
        "user": _build_user_profile(user),
    }

@router.post("/social-login", response_model=Any)
@limiter.limit(SOCIAL_RATE_LIMIT)
async def social_login(
    request: Request,
    data: SocialLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Social login (Google, Apple, WeChat)
    Note: Apple login is handled by Go Gateway for performance and security.
    This endpoint remains for Google and WeChat.
    """
    if data.provider not in ["google", "apple", "wechat"]:
        raise HTTPException(status_code=400, detail="暂不支持这种登录方式")

    social_id, user_info = await _verify_social_identity(data)

    # Determine which field to check
    query = select(User)
    if data.provider == 'google':
        query = query.where(User.google_id == social_id)
    elif data.provider == 'apple':
        query = query.where(User.apple_id == social_id)
    elif data.provider == 'wechat':
        query = query.where(User.wechat_unionid == social_id)
    else:
        raise HTTPException(status_code=400, detail="暂不支持这种登录方式")

    result = await db.execute(query)
    user = result.scalars().first()

    if not user:
        # Create new user
        import uuid
        random_suffix = str(uuid.uuid4())[:8]
        username = f"{data.provider}_{random_suffix}"

        user = User(
            username=username,
            email=user_info.get('email') or (data.email or f"{username}@example.com"),
            hashed_password=get_password_hash(str(uuid.uuid4())), # Random password
            password_login_enabled=False,
            nickname=user_info.get('name') or (data.nickname or f"{data.provider.capitalize()} User"),
            avatar_url=user_info.get('picture') or data.avatar_url,
            registration_source=data.provider,
            is_active=True,
            email_verified=bool(user_info.get("email_verified")),
        )

        if data.provider == 'google':
            user.google_id = social_id
        elif data.provider == 'apple':
            user.apple_id = social_id
        elif data.provider == 'wechat':
            user.wechat_unionid = social_id

        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Ensure verified flag for trusted providers
        if data.provider in ("google", "apple") and not user.email_verified:
            user.email_verified = True
            db.add(user)
            await db.commit()
            await db.refresh(user)

        if data.provider == "google" and not user.google_id:
            user.google_id = social_id
        elif data.provider == "apple" and not user.apple_id:
            user.apple_id = social_id
        elif data.provider == "wechat" and not user.wechat_unionid:
            user.wechat_unionid = social_id
        db.add(user)

    auth_audit_service.schedule_log(
        AuthAuditAction.LOGIN,
        user_id=str(user.id),
        request=request,
        metadata={"registration_source": data.provider, "provider": data.provider},
    )

    return {
        **await _issue_auth_tokens(db=db, user=user, request=request),
        "user": _build_user_profile(user),
    }

@router.post("/refresh", response_model=Any)
@limiter.limit(REFRESH_RATE_LIMIT)
async def refresh_token(
    request: Request,
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token
    """
    try:
        payload = await decode_token(data.refresh_token, expected_type="refresh")
        user_id = payload.get("sub")
        session_id = payload.get("sid")
        if not user_id:
            raise HTTPException(status_code=401, detail="登录令牌无效，请重新登录")

        user = await db.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="登录令牌无效，请重新登录")

        # Rotate refresh token: revoke old refresh token jti
        await blacklist_token(payload.get("jti"), payload.get("exp"))
        auth_audit_service.schedule_log(
            AuthAuditAction.TOKEN_REFRESH,
            user_id=str(user.id),
            request=request,
            metadata={"session_id": session_id},
        )
        extra_claims = {"is_guest": True} if payload.get("is_guest") else None
        return await _issue_auth_tokens(
            db=db,
            user=user,
            request=request,
            session_id=str(session_id) if session_id else None,
            extra_claims=extra_claims,
        )
    except Exception as e:
        logger.warning(f"Refresh token request failed: {e}")
        raise HTTPException(status_code=401, detail="刷新令牌无效，请重新登录")


@router.post("/logout", response_model=Any)
@limiter.limit(LOGOUT_RATE_LIMIT)
async def logout(
    request: Request,
    data: LogoutRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Logout by revoking refresh/access tokens via Redis blacklist.
    """
    # Revoke refresh token if provided
    refresh_token = data.refresh_token if data else None
    if refresh_token:
        try:
            payload = await decode_token(refresh_token, expected_type="refresh")
            await blacklist_token(payload.get("jti"), payload.get("exp"))
            if payload.get("sid"):
                await auth_session_service.revoke_session_by_id(
                    db,
                    user_id=str(payload.get("sub")),
                    session_id=str(payload.get("sid")),
                    ttl_seconds=SESSION_TTL_SECONDS,
                )
        except Exception:
            # Ignore invalid/revoked refresh tokens
            pass

    # Revoke access token from Authorization header if present
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header.removeprefix("Bearer ").strip()
        if access_token:
            try:
                payload = await decode_token(access_token, expected_type="access")
                await blacklist_token(payload.get("jti"), payload.get("exp"))
                if payload.get("sid"):
                    await auth_session_service.revoke_session_by_id(
                        db,
                        user_id=str(payload.get("sub")),
                        session_id=str(payload.get("sid")),
                        ttl_seconds=SESSION_TTL_SECONDS,
                    )
                auth_audit_service.schedule_log(
                    AuthAuditAction.LOGOUT,
                    user_id=str(payload.get("sub")),
                    request=request,
                    metadata={"session_id": payload.get("sid")},
                )
            except Exception:
                pass

    return {"detail": "Logged out"}


@router.post("/forgot-password", response_model=Any)
@limiter.limit(FORGOT_RATE_LIMIT)
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request password reset email (always returns success message).
    """
    response = {"detail": "如果该邮箱已注册，重置邮件已发送"}
    try:
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalars().first()
        if not user:
            return response

        reset_token = uuid.uuid4().hex
        await cache_service.set(
            f"pwd_reset:{reset_token}",
            str(user.id),
            ttl=PASSWORD_RESET_TTL_SECONDS,
        )
        asyncio.create_task(
            email_service.send_password_reset_email(
                to_email=user.email,
                reset_token=reset_token,
                username=user.nickname or user.username,
            )
        )
    except Exception as e:
        logger.warning(f"Failed to handle forgot-password: {e}")
    return response


@router.post("/reset-password", response_model=Any)
@limiter.limit(RESET_RATE_LIMIT)
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password with reset token.
    """
    key = f"pwd_reset:{data.token}"
    user_id = await cache_service.get(key)
    if not user_id:
        raise HTTPException(status_code=400, detail="重置码无效或已过期")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="用户不存在")

    user.hashed_password = get_password_hash(data.new_password)
    user.password_login_enabled = True
    user.token_revoked_before = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await cache_service.delete(key)
    await set_user_revoked_before(str(user.id), user.token_revoked_before)
    await auth_session_service.revoke_all_sessions_for_user(
        db,
        user_id=str(user.id),
        ttl_seconds=SESSION_TTL_SECONDS,
    )
    auth_audit_service.schedule_log(
        AuthAuditAction.PASSWORD_RESET,
        user_id=str(user.id),
        request=request,
    )

    return {"detail": "密码已重置，请重新登录"}


@router.post("/send-verification", response_model=Any)
@limiter.limit(VERIFY_RATE_LIMIT)
async def send_verification_email(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Send email verification code to current user.
    """
    if current_user.email_verified:
        return {"detail": "邮箱已验证"}

    verify_token = uuid.uuid4().hex
    await cache_service.set(
        f"email_verify:{verify_token}",
        str(current_user.id),
        ttl=EMAIL_VERIFY_TTL_SECONDS,
    )
    asyncio.create_task(
        email_service.send_verification_email(
            to_email=current_user.email,
            verify_token=verify_token,
            username=current_user.nickname or current_user.username,
        )
    )
    return {"detail": "验证邮件已发送"}


@router.post("/verify-email", response_model=Any)
@limiter.limit(VERIFY_RATE_LIMIT)
async def verify_email(
    request: Request,
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify email with token.
    """
    key = f"email_verify:{data.token}"
    user_id = await cache_service.get(key)
    if not user_id:
        raise HTTPException(status_code=400, detail="验证码无效或已过期")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="用户不存在")

    if not user.email_verified:
        user.email_verified = True
        db.add(user)
        await db.commit()
        await db.refresh(user)

    await cache_service.delete(key)
    auth_audit_service.schedule_log(
        AuthAuditAction.EMAIL_VERIFY,
        user_id=str(user.id),
        request=request,
    )
    return {"detail": "邮箱验证成功"}


@router.post("/guest", response_model=Any)
@limiter.limit("100/15minutes")
async def guest_login(
    request: Request,
    guest_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Guest login - 返回访客模式的JWT token
    用于测试和体验，不需要注册账号
    """
    import uuid

    # 如果没有提供guest_id，生成一个简短的ID
    if not guest_id:
        # 生成一个6字符的简短guest ID
        import random
        import string
        guest_id = 'guest_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

    # 检查是否已存在guest用户（用于保持会话连续性）
    existing_user = await db.execute(
        select(User).where(User.username == guest_id)
    )
    user = existing_user.scalars().first()

    # 如果不存在，创建一个临时guest用户并播种演示数据
    is_new_guest = not user
    if is_new_guest:
        user = User(
            username=guest_id,
            email=f"{guest_id}@guest.local",  # 临时邮箱
            hashed_password=get_password_hash(str(uuid.uuid4())), # 随机密码
            password_login_enabled=False,
            nickname=f"访客{guest_id[-4:]}",
            registration_source="guest",
            is_active=True,
        )
        db.add(user)
        await db.flush()  # 获取 user.id 但不 commit，保持事务

        # 为新游客播种演示数据，确保完整体验
        # 整个 user 创建 + seed 在同一个事务中，失败全部回滚
        try:
            from app.services.guest_seed_service import seed_guest_user_data
            await seed_guest_user_data(db, user)
            await db.commit()
            await db.refresh(user)
        except Exception as e:
            logger.error(f"Guest seed failed, rolling back: {e}")
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="访客账号初始化失败，请稍后重试",
            )
    else:
        # 已有访客账户 — 检查数据是否完整（seed 可能之前失败过）
        from app.services.guest_seed_service import seed_guest_user_data
        try:
            await seed_guest_user_data(db, user)  # 幂等，已有数据会跳过
            await db.commit()
            await db.refresh(user)
        except Exception as e:
            logger.warning(f"Guest re-seed failed (non-fatal): {e}")
            await db.rollback()
            # rollback 后需要重新加载 user 对象（session 状态已重置）
            result = await db.execute(select(User).where(User.username == guest_id))
            user = result.scalars().first()
            if not user:
                raise HTTPException(status_code=500, detail="访客账号异常，请稍后重试")

    logger.info(f"Guest login: guest_id={guest_id}, user_id={user.id}, new={is_new_guest}")

    return {
        **await _issue_auth_tokens(
            db=db,
            user=user,
            request=request,
            access_expires_delta=timedelta(days=7),
            extra_claims={"is_guest": True},
        ),
        "user": {
            **_build_user_profile(user).model_dump(mode="json"),
            "is_guest": True,
        },
    }


@router.post("/upgrade-guest", response_model=Any)
@limiter.limit(AUTH_RATE_LIMIT)
async def upgrade_guest(
    request: Request,
    data: UpgradeGuestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upgrade a guest account to a full email/password account.
    """
    if current_user.registration_source != "guest":
        raise HTTPException(status_code=400, detail="当前账号不是游客账号")

    _validate_terms_acceptance(data.accepted_tos, data.accepted_privacy)

    existing_username = await db.execute(select(User).where(User.username == data.username, User.id != current_user.id))
    if existing_username.scalars().first():
        raise HTTPException(status_code=400, detail="这个用户名已经被注册了")
    existing_email = await db.execute(select(User).where(User.email == data.email, User.id != current_user.id))
    if existing_email.scalars().first():
        raise HTTPException(status_code=400, detail="这个邮箱已经被注册了")

    current_user.username = data.username
    current_user.email = data.email
    current_user.nickname = data.nickname or data.username
    current_user.hashed_password = get_password_hash(data.password)
    current_user.password_login_enabled = True
    current_user.registration_source = "email"
    current_user.email_verified = False
    _apply_terms_acceptance(
        current_user,
        tos_version=data.tos_version,
        privacy_version=data.privacy_version,
        agreed_locale=data.agreed_locale,
    )
    db.add(current_user)
    await db.flush()

    try:
        verify_token = uuid.uuid4().hex
        await cache_service.set(f"email_verify:{verify_token}", str(current_user.id), ttl=EMAIL_VERIFY_TTL_SECONDS)
        asyncio.create_task(
            email_service.send_verification_email(
                to_email=current_user.email,
                verify_token=verify_token,
                username=current_user.nickname or current_user.username,
            ),
        )
    except Exception as e:
        logger.warning(f"Failed to schedule verification email after guest upgrade: {e}")

    auth_audit_service.schedule_log(
        AuthAuditAction.GUEST_UPGRADE,
        user_id=str(current_user.id),
        request=request,
        metadata={"mode": "email"},
    )
    return {
        **await _issue_auth_tokens(db=db, user=current_user, request=request),
        "user": _build_user_profile(current_user),
    }


@router.post("/upgrade-guest/social", response_model=Any)
@limiter.limit(SOCIAL_RATE_LIMIT)
async def upgrade_guest_social(
    request: Request,
    data: UpgradeGuestSocialRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upgrade a guest account by linking a social provider.
    """
    if current_user.registration_source != "guest":
        raise HTTPException(status_code=400, detail="当前账号不是游客账号")

    _validate_terms_acceptance(data.accepted_tos, data.accepted_privacy)
    social_data = SocialLoginRequest(provider=data.provider, token=data.token, openid=data.openid)
    social_id, user_info = await _verify_social_identity(social_data)

    if data.provider == "google":
        stmt = select(User).where(User.google_id == social_id, User.id != current_user.id)
    elif data.provider == "apple":
        stmt = select(User).where(User.apple_id == social_id, User.id != current_user.id)
    elif data.provider == "wechat":
        stmt = select(User).where(User.wechat_unionid == social_id, User.id != current_user.id)
    else:
        raise HTTPException(status_code=400, detail="暂不支持这种登录方式")

    existing = await db.execute(stmt)
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="该社交账号已绑定其他用户")

    social_email = user_info.get("email")
    if social_email:
        existing_email = await db.execute(
            select(User).where(User.email == social_email, User.id != current_user.id),
        )
        if existing_email.scalars().first():
            raise HTTPException(status_code=409, detail="该邮箱已被其他账号使用")

    current_user.registration_source = data.provider
    current_user.password_login_enabled = False
    current_user.email = social_email or current_user.email
    current_user.nickname = user_info.get("name") or current_user.nickname
    current_user.avatar_url = user_info.get("picture") or current_user.avatar_url
    current_user.email_verified = bool(user_info.get("email_verified"))
    if data.provider == "google":
        current_user.google_id = social_id
    elif data.provider == "apple":
        current_user.apple_id = social_id
    elif data.provider == "wechat":
        current_user.wechat_unionid = social_id
    _apply_terms_acceptance(
        current_user,
        tos_version=data.tos_version,
        privacy_version=data.privacy_version,
        agreed_locale=data.agreed_locale,
    )
    db.add(current_user)

    auth_audit_service.schedule_log(
        AuthAuditAction.GUEST_UPGRADE,
        user_id=str(current_user.id),
        request=request,
        metadata={"mode": "social", "provider": data.provider},
    )
    return {
        **await _issue_auth_tokens(db=db, user=current_user, request=request),
        "user": _build_user_profile(current_user),
    }
