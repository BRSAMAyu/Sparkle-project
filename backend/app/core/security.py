"""
Security and Authentication Utilities
JWT token generation, password hashing, etc.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT access token
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update(
        {"exp": expire, "iat": now, "jti": str(uuid4()), "type": "access"}
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
    now = datetime.utcnow()
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update(
        {"exp": expire, "iat": now, "jti": str(uuid4()), "type": "refresh"}
    )
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str, expected_type: Optional[str] = None) -> dict:
    """
    解码 JWT token
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError as exc:
        raise exc

    if "exp" not in payload or "sub" not in payload:
        raise JWTError("Token missing required claims")

    token_type = payload.get("type")
    if expected_type and token_type != expected_type:
        raise JWTError("Invalid token type")

    return payload
