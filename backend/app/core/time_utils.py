"""Centralized UTC time utilities.

All datetime handling should use these functions instead of local _utcnow() definitions.
Three variants existed across 300+ files — this module unifies them.

- utcnow()        -> tz-naive datetime (the canonical form, ~286 call sites)
- utcnow_aware()  -> tz-aware datetime  (for the ~8 sites that need UTC tzinfo)
- utcnow_iso()    -> ISO 8601 string    (for the ~24 sites that serialize directly)
"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return the current UTC time as a tz-naive datetime.

    This is the canonical form used across the codebase.
    tz-naive UTC datetimes are stored in PostgreSQL and compared everywhere.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def utcnow_aware() -> datetime:
    """Return the current UTC time as a tz-aware datetime (with UTC tzinfo)."""
    return datetime.now(UTC)


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()
