"""
Security and Authentication Utilities
JWT token generation, password hashing, etc.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import JWTError, jwt
from loguru import logger
from passlib.context import CryptContext
from sqlalchemy import select

from app.config import settings
from app.core.cache import cache_service
from app.services.auth_session_service import auth_session_service

TOKEN_BLACKLIST_PREFIX = "token_blacklist:"
USER_REVOKED_BEFORE_PREFIX = "user_revoked_before:"

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as exc:
        # Intentional fail-closed behavior: verifier errors must never authenticate a password.
        logger.warning("Password verification failed closed: {}", exc)
        return False


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    try:
        return pwd_context.hash(password)
    except Exception:
        # Remove dangerous fallback - raise exception for hashing failures
        raise ValueError("Failed to hash password") from None


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    创建 JWT access token
    """
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + expires_delta if expires_delta else now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update(
        {
            "exp": expire,
            "iat": now,
            "jti": str(uuid4()),
            "type": "access",
            "iss": getattr(settings, 'JWT_ISSUER', 'sparkle-gateway'),
            "aud": getattr(settings, 'JWT_AUDIENCE', 'sparkle-app')
        }
    )
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    创建 JWT refresh token
    """
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update(
        {
            "exp": expire,
            "iat": now,
            "jti": str(uuid4()),
            "type": "refresh",
            "iss": getattr(settings, 'JWT_ISSUER', 'sparkle-gateway'),
            "aud": getattr(settings, 'JWT_AUDIENCE', 'sparkle-app')
        }
    )
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def decode_token(token: str, expected_type: str | None = None) -> dict:
    """
    解码 JWT token
    """
    try:
        audience = settings.JWT_AUDIENCE or None
        issuer = settings.JWT_ISSUER or None
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=audience,
            issuer=issuer,
            options={"verify_aud": bool(audience)},
        )
    except JWTError as exc:
        raise exc

    if "exp" not in payload or "sub" not in payload:
        raise JWTError("Token missing required claims")

    token_type = payload.get("type")
    if expected_type and token_type != expected_type:
        raise JWTError("Invalid token type")

    jti = payload.get("jti")
    if jti:
        if await is_token_revoked(jti):
            raise JWTError("Token revoked")

    user_id = payload.get("sub")
    token_iat = payload.get("iat")
    if user_id and token_iat is not None:
        revoked_before = await get_user_revoked_before(str(user_id))
        if revoked_before is not None:
            try:
                iat_ts = int(token_iat)
            except Exception:
                iat_ts = None
            if iat_ts is not None and iat_ts < revoked_before:
                raise JWTError("Token revoked")

    session_id = payload.get("sid")
    if session_id:
        if await is_session_revoked(str(session_id)):
            raise JWTError("Session revoked")

    return payload


def decode_token_sync(token: str, expected_type: str | None = None) -> dict:
    """
    Synchronous wrapper for decode_token (for tests or sync contexts).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(decode_token(token, expected_type=expected_type))
    raise RuntimeError("decode_token_sync cannot be used inside a running event loop")


async def is_token_revoked(jti: str) -> bool:
    """
    Check whether token jti exists in blacklist.
    """
    if not jti:
        return False
    key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"
    try:
        value = await cache_service.get(key)
        return value is not None
    except Exception as exc:
        # Intentional fail-open behavior: Redis blacklist outages should not block existing valid JWTs.
        logger.warning("Token blacklist lookup failed open for jti={}: {}", jti, exc)
        return False


async def get_user_revoked_before(user_id: str) -> int | None:
    """
    Fetch per-user revocation timestamp from Redis, with DB fallback.
    """
    if not user_id:
        return None
    key = f"{USER_REVOKED_BEFORE_PREFIX}{user_id}"
    try:
        value = await cache_service.get(key)
        if value is not None:
            return int(value)
    except Exception as exc:
        logger.warning("Revocation timestamp cache lookup failed for user {}: {}", user_id, exc)

    try:
        from app.db.session import AsyncSessionLocal
        from app.models.user import User

        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user or user.token_revoked_before is None:
                return None
            revoked_before_ts = int(user.token_revoked_before.timestamp())
            await set_user_revoked_before(user_id, user.token_revoked_before)
            return revoked_before_ts
    except Exception as exc:
        logger.warning("Revocation timestamp DB fallback failed for user {}: {}", user_id, exc)
        return None

    return None


async def is_session_revoked(session_id: str) -> bool:
    """
    Check whether a session id has been revoked.
    """
    if not session_id:
        return False
    try:
        if await auth_session_service.is_session_revoked(session_id):
            return True
    except Exception as exc:
        # Intentional fail-open behavior: session service outages fall back to the DB session record.
        logger.warning("Session revocation service lookup failed open to DB fallback for session {}: {}", session_id, exc)

    try:
        from app.db.session import AsyncSessionLocal
        from app.models.auth_security import UserSession

        async with AsyncSessionLocal() as session:
            db_session = await session.scalar(
                select(UserSession).where(UserSession.session_id == session_id),
            )
            if db_session is None:
                return False
            return (not db_session.is_active) or (db_session.revoked_at is not None)
    except Exception as exc:
        # Intentional fail-open behavior: revocation DB outages should not block existing valid sessions.
        logger.warning("Session revocation DB lookup failed open for session {}: {}", session_id, exc)
        return False


async def set_user_revoked_before(user_id: str, revoked_before: datetime) -> None:
    """
    Store per-user revocation timestamp in Redis with TTL aligned to refresh token TTL.
    """
    if not user_id or revoked_before is None:
        return
    try:
        ts = int(revoked_before.timestamp())
    except Exception as exc:
        logger.warning("Invalid revoked_before timestamp for user {}: {}", user_id, exc)
        return
    ttl = int(settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    key = f"{USER_REVOKED_BEFORE_PREFIX}{user_id}"
    try:
        await cache_service.set(key, ts, ttl=ttl)
    except Exception as exc:
        logger.warning("Failed to cache revoked_before timestamp for user {}: {}", user_id, exc)
        return


async def blacklist_token(jti: str, exp: int | float | datetime | None) -> None:
    """
    Add token jti to blacklist with TTL based on exp claim.
    """
    if not jti or exp is None:
        return
    try:
        if isinstance(exp, datetime):
            exp_ts = int(exp.timestamp())
        else:
            exp_ts = int(exp)
    except Exception as exc:
        logger.warning("Invalid blacklist expiration for jti {}: {}", jti, exc)
        return

    now_ts = int(datetime.now(UTC).timestamp())
    ttl = exp_ts - now_ts
    if ttl <= 0:
        return True  # Already expired, no need to blacklist

    key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"

    # H4 Security Fix: Add retry mechanism for blacklist write
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await cache_service.set(key, "revoked", ttl=ttl)
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                # Log failure on final attempt
                logger.error(
                    "token_blacklist_failed",
                    jti_prefix=jti[:8] if len(jti) > 8 else jti,
                    error=str(e),
                    error_type=type(e).__name__,
                    attempts=max_retries
                )
                return False
            # Exponential backoff: 100ms, 200ms, 300ms
            import asyncio
            await asyncio.sleep(0.1 * (attempt + 1))

    return True
