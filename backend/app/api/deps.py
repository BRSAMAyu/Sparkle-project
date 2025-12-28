"""
API Dependencies
FastAPI 依赖注入函数
"""
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import decode_token
from app.core.exceptions import AuthenticationError
from app.models.user import User # Added import


# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    从 JWT token 中获取当前用户 ID
    用于需要认证的接口
    """
    try:
        token = credentials.credentials
        payload = decode_token(token, expected_type="access")
        user_id: str = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("无效的认证令牌")
        return user_id
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> User:
    from app.models.user import User # Import here to avoid circular dependency
    user = await db.get(User, user_id)
    if not user:
        raise AuthenticationError("User not found")
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise AuthenticationError("Inactive user")
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_superuser:
        from app.core.exceptions import AuthorizationError
        raise AuthorizationError("The user doesn't have enough privileges")
    return current_user


# Database session dependency is already defined in app.db.session.get_db
# You can import it like: from app.api.deps import get_db
