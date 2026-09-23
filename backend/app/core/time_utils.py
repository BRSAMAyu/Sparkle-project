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


def ensure_naive_utc(value: datetime | None) -> datetime | None:
    """Coerce a possibly tz-aware datetime to the canonical tz-naive UTC form.

    LLM-generated timestamps (ISO strings with 'Z'/'+00:00') parse as tz-aware;
    PostgreSQL columns are TIMESTAMP WITHOUT TIME ZONE and asyncpg raises
    DataError ("can't subtract offset-naive and offset-aware datetimes") when
    handed an aware value against them.
    """
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def to_epoch_seconds(value: datetime) -> int:
    """Convert a datetime (naive-UTC canonical or tz-aware) to true UTC epoch seconds.

    Naive datetimes are interpreted as UTC — the codebase canonical form —
    NOT as local time (which is what ``.timestamp()`` does on a naive value;
    on a +0800 host that shifted revocation watermarks by -28800s, letting
    tokens issued within 8h before a password reset survive the watermark).
    """
    import calendar

    if value.tzinfo is None:
        return calendar.timegm(value.utctimetuple())
    return int(value.timestamp())
