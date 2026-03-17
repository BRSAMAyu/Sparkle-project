"""
API Dependencies
FastAPI 依赖注入函数
"""
from fastapi import Depends, HTTPException, status
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User  # Added import
from app.services.auth_session_service import auth_session_service

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    从 JWT token 中获取当前用户 ID
    用于需要认证的接口
    """
    try:
        token = credentials.credentials
        payload = await decode_token(token, expected_type="access")
        request.state.token_payload = payload
        user_id: str = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("登录信息已过期，请重新登录~")
        return user_id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录信息已过期，请重新登录~",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> User:
    from app.models.user import User  # Import here to avoid circular dependency
    user = await db.get(User, user_id)
    if not user:
        raise AuthenticationError("该用户不存在，请检查输入")
    try:
        payload = getattr(request.state, "token_payload", None)
        if payload:
            await auth_session_service.touch_from_payload(
                db,
                request=request,
                user_id=str(user.id),
                payload=payload,
            )
    except Exception as e:
        # H1 Security Fix: Log session touch failure but don't block (fail open)
        # Session will eventually expire naturally
        import structlog
        logger = structlog.get_logger()
        logger.warning(
            "session_touch_failed",
            user_id=str(user.id),
            error=str(e),
            error_type=type(e).__name__
        )
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise AuthenticationError("账号暂时无法使用，请联系客服")
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_superuser:
        from app.core.exceptions import AuthorizationError
        raise AuthorizationError("这个功能只有管理员才能使用哦")
    return current_user


# Database session dependency is already defined in app.db.session.get_db
# You can import it like: from app.api.deps import get_db
