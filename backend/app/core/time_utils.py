"""Centralized UTC time utilities.

All datetime handling should use these functions instead of local _utcnow() definitions.
Three variants existed across 300+ files — this module unifies them.

- utcnow()        -> tz-naive datetime (the canonical form, ~286 call sites)
- utcnow_aware()  -> tz-aware datetime  (for the ~8 sites that need UTC tzinfo)
- utcnow_iso()    -> ISO 8601 string    (for the ~24 sites that serialize directly)

用户本地日界（stats 聚合对齐，V3-FIX-37）：
- 仓库存在两种 naive 存储钟：**UTC naive**（服务端 utcnow 写入，如
  Task.completed_at / StudyRecord.created_at）与**用户本地墙上时间 naive**
  （客户端写 FocusSession.start_time 时发本地 ISO 串、无时区后缀）。
- 对 UTC 存储列切「用户今天」须把本地日界换算成 UTC naive 瞬间
  （:func:`local_midnight_as_utc_naive`）；对墙上时间存储列则直接用本地
  零点 naive 作窗口（:func:`local_midnight_wall`），两侧同钟。
"""

from datetime import UTC, date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

DEFAULT_USER_TIMEZONE = "Asia/Shanghai"


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


def valid_timezone_name(name: str | None) -> str:
    """Validate an IANA timezone name, falling back to the market default."""
    normalized = str(name or "").strip()
    if not normalized:
        return DEFAULT_USER_TIMEZONE
    try:
        ZoneInfo(normalized)
    except Exception:
        return DEFAULT_USER_TIMEZONE
    return normalized


def user_timezone_name(user: Any | None) -> str:
    """Resolve the user's IANA timezone name from push_preference, market default fallback.

    与 app/tasks/accountability_tasks.py 的既定口径一致：push_preference.timezone
    （User.push_preference 为 lazy="joined" 关系，同步上下文可直接读）缺省或非法时
    回落主市场 Asia/Shanghai。注意：身份映射命中的 ORM 实例该关系可能未加载
    （async 下触发 lazy load 会炸）——那种路径请改用
    ``valid_timezone_name(await db.scalar(select(PushPreference.timezone)...))``。
    """
    pref = getattr(getattr(user, "push_preference", None), "timezone", None)
    return valid_timezone_name(str(pref) if pref is not None else None)


def local_date(now_utc_naive: datetime, timezone_name: str) -> date:
    """User-local calendar date for a naive-UTC instant (the stats "today")."""
    return now_utc_naive.replace(tzinfo=UTC).astimezone(ZoneInfo(timezone_name)).date()


def local_midnight_as_utc_naive(day: date, timezone_name: str) -> datetime:
    """Naive-UTC instant of the local midnight that starts ``day`` (for UTC-stored columns)."""
    local_midnight = datetime.combine(day, time.min).replace(tzinfo=ZoneInfo(timezone_name))
    return local_midnight.astimezone(UTC).replace(tzinfo=None)


def local_midnight_wall(day: date) -> datetime:
    """Naive local-wall midnight of ``day`` (for columns stored in the user's wall clock).

    FocusSession.start_time 存客户端本地墙上时间 naive（V3-FIX-37 定界），
    过滤窗口必须用同一墙钟的零点 naive，而非换算成 UTC 瞬间。
    """
    return datetime.combine(day, time.min)
