"""
Authentication API
Login, Register, Refresh Token, Social Login
"""
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.account_lockout import account_lockout_service
from app.core.rate_limiting import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import RefreshTokenRequest, SocialLoginRequest, UserBase, UserLogin, UserRegister, UserProfile

router = APIRouter()

# Relax rate limits in development to avoid blocking during iterative testing.
AUTH_RATE_LIMIT = "50/15minutes" if settings.DEBUG else "5/15minutes"
SOCIAL_RATE_LIMIT = "50/15minutes" if settings.DEBUG else "5/15minutes"
REFRESH_RATE_LIMIT = "100/15minutes" if settings.DEBUG else "10/15minutes"

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
            is_active=True
        )

        if data.provider == 'google':
            user.google_id = social_id
        elif data.provider == 'wechat':
            user.wechat_unionid = social_id

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
        payload = decode_token(data.refresh_token, expected_type="refresh")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="登录令牌无效，请重新登录")

        user = await db.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="登录令牌无效，请重新登录")

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id}, expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except Exception:
        raise HTTPException(status_code=401, detail="刷新令牌无效，请重新登录")


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
            is_active=True,
            # 标记为guest用户
            user_type="guest"  # 需要在User模型中添加此字段，如果没有则忽略
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
            "id": str(user.id),
            "username": user.username,
            "nickname": user.nickname,
            "is_guest": True
        }
    }
