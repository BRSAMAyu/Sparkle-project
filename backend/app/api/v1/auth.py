"""
Authentication API
Login, Register, Refresh Token, Social Login
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
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
from app.core.email_service import email_service
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    ForgotPasswordRequest,
    LogoutRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SocialLoginRequest,
    UserBase,
    UserLogin,
    UserRegister,
    UserProfile,
    VerifyEmailRequest,
)
from app.api.deps import get_current_user

router = APIRouter()

# Relax rate limits in development to avoid blocking during iterative testing.
AUTH_RATE_LIMIT = "50/15minutes" if settings.DEBUG else "5/15minutes"
SOCIAL_RATE_LIMIT = "50/15minutes" if settings.DEBUG else "5/15minutes"
REFRESH_RATE_LIMIT = "100/15minutes" if settings.DEBUG else "10/15minutes"
FORGOT_RATE_LIMIT = "30/15minutes" if settings.DEBUG else "3/15minutes"
VERIFY_RATE_LIMIT = "30/15minutes" if settings.DEBUG else "5/15minutes"
RESET_RATE_LIMIT = "30/15minutes" if settings.DEBUG else "5/15minutes"

PASSWORD_RESET_TTL_SECONDS = 15 * 60
EMAIL_VERIFY_TTL_SECONDS = 24 * 60 * 60

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
    logger.info(f"Registration attempt: username={data.username}, email={data.email}")
    # Check existing user
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalars().first():
        logger.warning(f"Registration failed: username {data.username} already exists")
        raise HTTPException(status_code=400, detail="这个用户名已经被注册了")

    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        logger.warning(f"Registration failed: email {data.email} already exists")
        raise HTTPException(status_code=400, detail="这个邮箱已经被注册了")

    # Create user
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=get_password_hash(data.password),
        nickname=data.nickname or data.username,
        registration_source="email",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"User registered successfully: {user.username} (ID: {user.id})")

    # Send verification email (async, non-blocking)
    try:
        verify_token = uuid.uuid4().hex
        await cache_service.set(
            f"email_verify:{verify_token}",
            str(user.id),
            ttl=EMAIL_VERIFY_TTL_SECONDS,
        )
        asyncio.create_task(
            email_service.send_verification_email(
                to_email=user.email,
                verify_token=verify_token,
                username=user.nickname or user.username,
            )
        )
    except Exception as e:
        logger.warning(f"Failed to schedule verification email: {e}")

    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "user": UserProfile.model_validate(user),
        "token": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
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

    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # P1 Fix: Return full user profile and standardized structure
    # Keeping top-level token fields for backward compatibility
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "token": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        },
        "user": UserProfile.model_validate(user)
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
    # Validate provider
    if data.provider not in ['google', 'wechat']:
        if data.provider == 'apple':
             raise HTTPException(
                 status_code=400,
                 detail="Apple 登录请通过 /api/v1/auth/apple 在 Gateway 上进行"
             )
        raise HTTPException(status_code=400, detail="暂不支持这种登录方式")

    # Verify social token with provider
    social_id = None
    user_info = {}

    try:
        if data.provider == 'google':
            # Google token verification
            import httpx
            timeout = httpx.Timeout(5.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Verify Google ID token
                response = await client.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"id_token": data.token}
                )
                if response.status_code != 200:
                    raise HTTPException(status_code=401, detail="Google 令牌验证失败，请重试")

                token_info = response.json()
                if token_info.get('iss') not in ['https://accounts.google.com', 'accounts.google.com']:
                    raise HTTPException(status_code=401, detail="Google 令牌验证失败，请重试")
                if settings.GOOGLE_CLIENT_ID and token_info.get("aud") != settings.GOOGLE_CLIENT_ID:
                    raise HTTPException(status_code=401, detail="Google 令牌验证失败，请重试")
                if token_info.get("email_verified") not in (True, "true", "True", "1"):
                    raise HTTPException(status_code=401, detail="Google 令牌验证失败，请重试")

                social_id = token_info.get('sub')
                user_info = {
                    'email': token_info.get('email'),
                    'name': token_info.get('name'),
                    'picture': token_info.get('picture')
                }

        elif data.provider == 'wechat':
            import httpx
            timeout = httpx.Timeout(5.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                if not data.openid:
                    # Code Exchange Flow (Preferred)
                    if not settings.WECHAT_APP_ID or not settings.WECHAT_APP_SECRET:
                        raise HTTPException(status_code=500, detail="服务器未配置微信登录")
                    
                    # 1. Exchange code for access_token and openid
                    token_resp = await client.get(
                        "https://api.weixin.qq.com/sns/oauth2/access_token",
                        params={
                            "appid": settings.WECHAT_APP_ID,
                            "secret": settings.WECHAT_APP_SECRET,
                            "code": data.token,
                            "grant_type": "authorization_code"
                        }
                    )
                    token_data = token_resp.json()
                    
                    if "errcode" in token_data and token_data["errcode"] != 0:
                        logger.error(f"WeChat code exchange failed: {token_data}")
                        raise HTTPException(status_code=401, detail="微信登录失败，请重试")
                        
                    social_id = token_data['openid']
                    access_token = token_data['access_token']
                    
                    # 2. Get User Info
                    user_resp = await client.get(
                        "https://api.weixin.qq.com/sns/userinfo",
                        params={
                            "access_token": access_token,
                            "openid": social_id,
                            "lang": "zh_CN"
                        }
                    )
                    user_data = user_resp.json()
                    
                    if "errcode" in user_data and user_data["errcode"] != 0:
                        logger.error(f"WeChat user info failed: {user_data}")
                        raise HTTPException(status_code=401, detail="获取微信用户信息失败")
                        
                    user_info = {
                        'email': None,
                        'name': user_data.get('nickname'),
                        'picture': user_data.get('headimgurl')
                    }
                    
                else:
                    # Token Verification Flow (Legacy)
                    response = await client.get(
                        "https://api.weixin.qq.com/sns/auth",
                        params={"access_token": data.token, "openid": data.openid}
                    )
                    if response.status_code != 200:
                        raise HTTPException(status_code=401, detail="微信令牌验证失败，请重试")

                    result = response.json()
                    if result.get('errcode') != 0:
                        raise HTTPException(status_code=401, detail="微信令牌验证失败，请重试")

                    social_id = data.openid
                    user_info = {
                        'email': None,
                        'name': None,
                        'picture': None
                    }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Social login verification failed for {data.provider}: {e}")
        raise HTTPException(status_code=401, detail="社交登录验证失败")

    if not social_id:
        raise HTTPException(status_code=401, detail="无法验证登录令牌")

    # Determine which field to check
    query = select(User)
    if data.provider == 'google':
        query = query.where(User.google_id == social_id)
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
            nickname=user_info.get('name') or (data.nickname or f"{data.provider.capitalize()} User"),
            avatar_url=user_info.get('picture') or data.avatar_url,
            registration_source=data.provider,
            is_active=True,
            email_verified=(data.provider == "google" or data.provider == "apple")
        )

        if data.provider == 'google':
            user.google_id = social_id
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

    # Generate tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "token": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        },
        "user": UserProfile.model_validate(user)
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
        if not user_id:
            raise HTTPException(status_code=401, detail="登录令牌无效，请重新登录")

        user = await db.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="登录令牌无效，请重新登录")

        # Rotate refresh token: revoke old refresh token jti
        await blacklist_token(payload.get("jti"), payload.get("exp"))

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id}, expires_delta=access_token_expires
        )
        new_refresh_token = create_refresh_token(data={"sub": user_id})

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "token": {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }
        }
    except Exception:
        raise HTTPException(status_code=401, detail="刷新令牌无效，请重新登录")


@router.post("/logout", response_model=Any)
@limiter.limit(REFRESH_RATE_LIMIT)
async def logout(
    request: Request,
    data: LogoutRequest | None = None,
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
    user.token_revoked_before = datetime.utcnow()
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await cache_service.delete(key)
    await set_user_revoked_before(str(user.id), user.token_revoked_before)

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

    # 如果不存在，创建一个临时guest用户
    if not user:
        user = User(
            username=guest_id,
            email=f"{guest_id}@guest.local",  # 临时邮箱
            hashed_password=get_password_hash(str(uuid.uuid4())), # 随机密码
            nickname=f"访客{guest_id[-4:]}",
            registration_source="guest",
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # 生成一个长期有效的token (7天)
    access_token_expires = timedelta(days=7)
    access_token = create_access_token(
        data={"sub": str(user.id), "is_guest": True},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "is_guest": True}
    )

    logger.info(f"Guest login: guest_id={guest_id}, user_id={user.id}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "token": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        },
        "user": {
            **UserProfile.model_validate(user).model_dump(mode="json"),
            "is_guest": True,
        },
    }
