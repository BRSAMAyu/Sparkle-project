"""
API Dependencies
FastAPI 依赖注入函数
"""
import asyncio
import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.security import decode_token, is_token_revoked
from app.db.session import get_db
from app.models.user import User  # Added import
from app.services.auth_session_service import auth_session_service

# HTTP Bearer token scheme
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


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

        # AUTH-DEEP A2 收敛：黑名单唯一读口是 security.is_token_revoked
        # （token_blacklist: 命名空间，prod fail-closed）——旧 token_revocation_service
        # 写错命名空间，其拉黑对 decode_token/网关不可见，已退役删除。
        if await is_token_revoked(payload.get("jti")):
            raise AuthenticationError("登录已失效，请重新登录")

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
        ) from None

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> User:
    from app.models.user import User  # Import here to avoid circular dependency
    user = await db.get(User, user_id)
    if not user:
        raise AuthenticationError("该用户不存在，请检查输入")
    payload = getattr(request.state, "token_payload", None)
    if payload:
        # engine-restore-storm 修复：会话 touch 改为独立短事务后台执行。
        # 旧路径在请求事务里 upsert user_sessions 并把行锁持有到请求结束，
        # 恢复风暴下同一 session 的并发请求全部在该行锁上串行化超时。
        # detached touch 锁持有 ~ms、失败不影响请求（H1 fail-open 语义保持）。
        _schedule_detached_touch(
            auth_session_service.touch_from_payload_detached(
                user_id=str(user.id), payload=payload, request=request
            )
        )
    return user


# 防止 fire-and-forget task 被 GC（asyncio 只持弱引用）
_detached_touch_tasks: set[asyncio.Task] = set()


def _schedule_detached_touch(coro) -> None:
    task = asyncio.get_running_loop().create_task(coro)
    _detached_touch_tasks.add(task)
    task.add_done_callback(_detached_touch_tasks.discard)


async def get_optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
) -> User | None:
    if credentials is None or not credentials.credentials:
        return None

    try:
        token = credentials.credentials
        payload = await decode_token(token, expected_type="access")

        # AUTH-DEEP A2 收敛：同 get_current_user_id，黑名单读口统一到
        # security.is_token_revoked（旧 token_revocation_service 已退役）。
        if await is_token_revoked(payload.get("jti")):
            raise AuthenticationError("登录已失效，请重新登录")

        request.state.token_payload = payload
        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None
        user = await db.get(User, user_id)
        if not user:
            return None
        # engine-restore-storm 修复：与 get_current_user 相同，touch 改为 detached 短事务，
        # 消除 user_sessions 行锁在请求生命周期内的串行化。
        _schedule_detached_touch(
            auth_session_service.touch_from_payload_detached(
                user_id=str(user.id), payload=payload, request=request
            )
        )
        return user
    except Exception:
        return None

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


# ---------------------------------------------------------------------------
# i18n helper – bilingual message support
# ---------------------------------------------------------------------------

def _zh(request: Request | None = None) -> bool:
    """Return True when the client prefers Chinese (zh) locale.

    Defaults to True for backward compatibility when no request is available.
    """
    if request is not None:
        accept = request.headers.get("Accept-Language", "")
        if accept:
            return "zh" in accept.lower()
    return True  # default to Chinese for backward compatibility


# Database session dependency is already defined in app.db.session.get_db
# You can import it like: from app.api.deps import get_db
