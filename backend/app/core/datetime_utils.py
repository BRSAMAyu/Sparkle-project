"""
Datetime and user utility functions.

Provides shared utilities for timezone-aware datetime handling and user display names.
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.models.user import User


def _utcnow() -> datetime:
    """Return current UTC time as a naive datetime (no timezone info).

    This is the standard pattern for database timestamps across the codebase.
    Use this instead of datetime.utcnow() which is deprecated.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def _user_display_name(user: User | None, default: str = "用户") -> str:
    """Get display name from a user object, falling back to default."""
    if not user:
        return default
    return user.nickname or user.full_name or user.username or default