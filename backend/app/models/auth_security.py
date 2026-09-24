"""
Authentication security models.
"""
from __future__ import annotations

import enum


# Python 3.9 compatible StrEnum
class StrEnum(enum.StrEnum):
    """String enum for Python 3.9 compatibility"""
    def __new__(cls, value):
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj


from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel, HardDeleteBaseModel


class AuthAuditAction(StrEnum):
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    SOCIAL_LINK = "social_link"
    SOCIAL_UNLINK = "social_unlink"
    ACCOUNT_DELETE = "account_delete"
    TOKEN_REFRESH = "token_refresh"
    GUEST_UPGRADE = "guest_upgrade"
    EMAIL_VERIFY = "email_verify"


class UserSession(BaseModel):
    """Active authentication session tracked by refresh-token session id."""

    __tablename__ = "user_sessions"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    device_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    device_name: Mapped[str] = mapped_column(String(255), nullable=True)
    device_type: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=True)
    refresh_token_jti: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AuthAuditLog(HardDeleteBaseModel):
    """Authentication activity audit log."""

    __tablename__ = "auth_audit_log"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=True)
    metadata_: Mapped[Any] = mapped_column("metadata", JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


Index("idx_user_sessions_user_active", UserSession.user_id, UserSession.is_active)
Index("idx_auth_audit_user_occurred", AuthAuditLog.user_id, AuthAuditLog.occurred_at)
