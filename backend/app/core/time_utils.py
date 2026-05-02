"""Centralized UTC time utilities."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return the current UTC time as a tz-naive datetime."""
    return datetime.now(UTC).replace(tzinfo=None)


def utcnow_aware() -> datetime:
    """Return the current UTC time as a tz-aware datetime."""
    return datetime.now(UTC)


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()
