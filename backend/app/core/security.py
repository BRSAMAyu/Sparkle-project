"""
Security and Authentication Utilities
JWT token generation, password hashing, etc.
"""
import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.core.cache import cache_service

TOKEN_BLACKLIST_PREFIX = "token_blacklist:"
USER_REVOKED_BEFORE_PREFIX = "user_revoked_before:"

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Remove dangerous fallback - always return False for invalid passwords
        return False


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    try:
        return pwd_context.hash(password)
    except Exception:
        # Remove dangerous fallback - raise exception for hashing failures
        raise ValueError("Failed to hash password")


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
    except Exception:
        # Fail open if Redis is unavailable to avoid blocking logins.
        return False


async def get_user_revoked_before(user_id: str) -> int | None:
    """
    Fetch per-user revocation timestamp from Redis.
    """
    if not user_id:
        return None
    key = f"{USER_REVOKED_BEFORE_PREFIX}{user_id}"
    try:
        value = await cache_service.get(key)
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


async def set_user_revoked_before(user_id: str, revoked_before: datetime) -> None:
    """
    Store per-user revocation timestamp in Redis with TTL aligned to refresh token TTL.
    """
    if not user_id or revoked_before is None:
        return
    try:
        ts = int(revoked_before.timestamp())
    except Exception:
        return
    ttl = int(settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    key = f"{USER_REVOKED_BEFORE_PREFIX}{user_id}"
    try:
        await cache_service.set(key, ts, ttl=ttl)
    except Exception:
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
    except Exception:
        return

    now_ts = int(datetime.now(UTC).timestamp())
    ttl = exp_ts - now_ts
    if ttl <= 0:
        return
    key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"
    try:
        await cache_service.set(key, "revoked", ttl=ttl)
    except Exception:
        # If blacklist write fails, do not block logout/refresh.
        return
