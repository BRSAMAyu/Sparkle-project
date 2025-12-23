"""
Authentication API
Login, Register, Refresh Token, Social Login
"""
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import ValidationError

from app.db.session import get_db
from app.core.security import (
    create_access_token, create_refresh_token,
    verify_password, get_password_hash,
    get_current_user, decode_token
)
from app.models.user import User
from app.schemas.user import (
    UserRegister, UserLogin, RefreshTokenRequest, 
    SocialLoginRequest, UserBase
)
from app.config import settings

router = APIRouter()

@router.post("/register", response_model=Any)
async def register(
    data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    """
    # Check existing user
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=get_password_hash(data.password),
        nickname=data.nickname or data.username,
        registration_source="email"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "user": user,
        "token": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    }

@router.post("/login", response_model=Any)
async def login(
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
    
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Update last login
    # user.last_login_at = datetime.utcnow()
    # await db.commit()

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
async def social_login(
    data: SocialLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Social login (Google, Apple, WeChat)
    """
    # Mock validation logic - in production, verify the token with the provider
    social_id = None
    
    # Simulate extraction of social ID from token
    # For dev: assume token IS the social ID if it starts with 'mock-'
    if data.token.startswith('mock-'):
        social_id = data.token
    else:
        # In real world: verify(data.token) -> get sub/uid
        social_id = f"{data.provider}_{hash(data.token)}" 

    # Determine which field to check
    query = select(User)
    if data.provider == 'google':
        query = query.where(User.google_id == social_id)
    elif data.provider == 'apple':
        query = query.where(User.apple_id == social_id)
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
            email=data.email or f"{username}@example.com", # Placeholder if email not provided
            hashed_password=get_password_hash(str(uuid.uuid4())), # Random password
            nickname=data.nickname or f"{data.provider.capitalize()} User",
            avatar_url=data.avatar_url,
            registration_source=data.provider,
            is_active=True
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
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token
    """
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
             raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
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