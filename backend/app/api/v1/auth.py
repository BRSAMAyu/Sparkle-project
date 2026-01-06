"""
Authentication API
Login, Register, Refresh Token, Social Login
"""
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import (
    create_access_token, create_refresh_token,
    verify_password, get_password_hash,
    decode_token
)
from app.models.user import User
from app.schemas.user import (
    UserRegister, UserLogin, RefreshTokenRequest,
    SocialLoginRequest, UserBase
)
from app.config import settings
from app.core.rate_limiting import limiter
from app.core.account_lockout import account_lockout_service

from loguru import logger

router = APIRouter()

@router.post("/register", response_model=Any)
@limiter.limit("5/15minutes")
async def register(
    request: Request,
    data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    """
    # Check existing user
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalars().first():
        logger.warning(f"Registration failed: username {data.username} already exists")
        raise HTTPException(status_code=400, detail="Username already registered")
    
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        logger.warning(f"Registration failed: email {data.email} already exists")
        raise HTTPException(status_code=400, detail="Email already registered")

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
        "user": UserBase.model_validate(user),
        "token": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    }

@router.post("/login", response_model=Any)
@limiter.limit("5/15minutes")
async def login(
    request: Request,
    data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    User login with username/email and password
    """
    # Check username or email
    result = await db.execute(
        select(User).where((User.username == data.username) | (User.email == data.username))
    )
    user = result.scalars().first()
    
    if not user:
        logger.warning(f"Login attempt for non-existent user: {data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is locked
    if await account_lockout_service.check_and_handle_lockout(str(user.id), db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account locked due to too many failed attempts. Please try again in 15 minutes."
        )
    
    if not verify_password(data.password, user.hashed_password):
        logger.warning(f"Login failed for user: {data.username}")
        # Record failed attempt
        await account_lockout_service.record_failed_login(str(user.id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {user.username}")
        raise HTTPException(status_code=400, detail="Inactive user")

    # Successful login - reset failed attempts
    await account_lockout_service.handle_successful_login(str(user.id))

    logger.info(f"User logged in: {user.username} (ID: {user.id})")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url
        }
    }

@router.post("/social-login", response_model=Any)
@limiter.limit("5/15minutes")
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
                 detail="Apple login should be performed via /api/v1/auth/apple on the Gateway"
             )
        raise HTTPException(status_code=400, detail="Unsupported provider")
    
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
                    raise HTTPException(status_code=401, detail="Invalid Google token")
                
                token_info = response.json()
                if token_info.get('iss') not in ['https://accounts.google.com', 'accounts.google.com']:
                    raise HTTPException(status_code=401, detail="Invalid token issuer")
                if settings.GOOGLE_CLIENT_ID and token_info.get("aud") != settings.GOOGLE_CLIENT_ID:
                    raise HTTPException(status_code=401, detail="Invalid token audience")
                if token_info.get("email_verified") not in (True, "true", "True", "1"):
                    raise HTTPException(status_code=401, detail="Email not verified")
                
                social_id = token_info.get('sub')
                user_info = {
                    'email': token_info.get('email'),
                    'name': token_info.get('name'),
                    'picture': token_info.get('picture')
                }
        
        elif data.provider == 'wechat':
            if not data.openid:
                raise HTTPException(status_code=400, detail="Missing openid for WeChat login")
            # WeChat token verification
            import httpx
            timeout = httpx.Timeout(5.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                # WeChat uses different flow - verify access token
                response = await client.get(
                    "https://api.weixin.qq.com/sns/auth",
                    params={"access_token": data.token, "openid": data.openid}
                )
                if response.status_code != 200:
                    raise HTTPException(status_code=401, detail="Invalid WeChat token")
                
                result = response.json()
                if result.get('errcode') != 0:
                    raise HTTPException(status_code=401, detail="Invalid WeChat token")
                
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
        raise HTTPException(status_code=401, detail=f"Social login verification failed: {str(e)}")
    
    if not social_id:
        raise HTTPException(status_code=401, detail="Failed to verify social token")
    
    # Determine which field to check
    query = select(User)
    if data.provider == 'google':
        query = query.where(User.google_id == social_id)
    elif data.provider == 'wechat':
        query = query.where(User.wechat_unionid == social_id)
    else:
        raise HTTPException(status_code=400, detail="Unsupported provider")

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
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url
        }
    }

@router.post("/refresh", response_model=Any)
@limiter.limit("10/15minutes")
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
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await db.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
