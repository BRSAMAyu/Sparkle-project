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

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, String

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

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(64), nullable=False, unique=True, index=True)
    device_id = Column(String(255), nullable=True, index=True)
    device_name = Column(String(255), nullable=True)
    device_type = Column(String(50), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    refresh_token_jti = Column(String(64), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    last_active_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AuthAuditLog(HardDeleteBaseModel):
    """Authentication activity audit log."""

    __tablename__ = "auth_audit_log"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


Index("idx_user_sessions_user_active", UserSession.user_id, UserSession.is_active)
Index("idx_auth_audit_user_occurred", AuthAuditLog.user_id, AuthAuditLog.occurred_at)
