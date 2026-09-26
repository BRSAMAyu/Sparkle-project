from __future__ import annotations

import calendar
import re
from datetime import UTC, datetime, timedelta

from app.core.time_utils import ensure_naive_utc


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# 中文星期表达 → Python weekday（周一=0 … 周日=6）。
_WEEKDAY_NUM: dict[str, int] = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6,
    "天": 6,
    "1": 0,
    "2": 1,
    "3": 2,
    "4": 3,
    "5": 4,
    "6": 5,
    "7": 6,
}

# "下周三" / "下下周三" / "下个周五" / "这周五" / "本周五" / "周三" / "星期五" / "礼拜五"。
_WEEKDAY_ANCHOR_RE = re.compile(
    r"(下下?个?(?:周|礼拜|星期)|(?:这|本)(?:周|礼拜|星期)|周|礼拜|星期)\s*([一二三四五六日天1-7])"
)


def resolve_weekday_anchor(
    text: str, *, reference_time: datetime | None = None
) -> tuple[datetime, str] | None:
    """解析中文星期表达，返回 (目标日 naive UTC, 语义 kind)；无法解析返回 None。

    - "下周X" → 下周（相对于 reference 所在周）的星期 X；
    - "这周X/本周X/周X/星期X/礼拜X" → 本周的星期 X，已过则顺延到下周同一天；
    - "下下周X" → 下下周的星期 X。
    """
    sentence = str(text or "")
    if not sentence:
        return None
    match = _WEEKDAY_ANCHOR_RE.search(sentence)
    if not match:
        return None
    target_weekday = _WEEKDAY_NUM.get(match.group(2))
    if target_weekday is None:
        return None

    now = reference_time or _utcnow()
    prefix = match.group(1)
    days_until_next_monday = (7 - now.weekday()) % 7 or 7
    if prefix.startswith("下下"):
        delta_days = days_until_next_monday + 7 + target_weekday
        kind = "week_after_next"
    elif prefix.startswith("下"):
        delta_days = days_until_next_monday + target_weekday
        kind = "next_week"
    else:
        delta_days = (target_weekday - now.weekday()) % 7
        kind = "this_week" if delta_days < days_until_next_monday else "next_week"

    target = now + timedelta(days=delta_days)
    if "上午" in sentence or "早上" in sentence:
        hour = 9
    elif "下午" in sentence:
        hour = 15
    elif "晚上" in sentence:
        hour = 20
    else:
        hour = 18
    target = target.replace(hour=hour, minute=0, second=0, microsecond=0)
    naive_target = ensure_naive_utc(target)
    if naive_target is None:
        return None
    return naive_target, kind


def parse_commitment_due_at(text: str, *, reference_time: datetime | None = None) -> datetime | None:
    sentence = str(text or "").strip()
    if not sentence:
        return None

    now = reference_time or _utcnow()
    lowered = sentence.lower()

    if "明天下午" in lowered:
        base = now + timedelta(days=1)
        return ensure_naive_utc(base.replace(hour=15, minute=0, second=0, microsecond=0))
    if "明天晚上" in lowered or "明晚" in lowered:
        base = now + timedelta(days=1)
        return ensure_naive_utc(base.replace(hour=20, minute=0, second=0, microsecond=0))
    if "明天" in lowered:
        base = now + timedelta(days=1)
        return ensure_naive_utc(base.replace(hour=9, minute=0, second=0, microsecond=0))
    if "今天晚上" in lowered or "今晚" in lowered:
        return ensure_naive_utc(now.replace(hour=20, minute=0, second=0, microsecond=0))
    if "今天下午" in lowered or "今天" in lowered:
        return ensure_naive_utc(now.replace(hour=15, minute=0, second=0, microsecond=0))

    # 中文星期表达必须先于"这周/本周"兜底分支（"这周五"包含"这周"子串）。
    weekday_anchor = resolve_weekday_anchor(sentence, reference_time=now)
    if weekday_anchor is not None:
        return weekday_anchor[0]

    if "这周" in lowered or "本周" in lowered:
        days_until_sunday = max(0, 6 - now.weekday())
        target = now + timedelta(days=days_until_sunday)
        return ensure_naive_utc(target.replace(hour=18, minute=0, second=0, microsecond=0))
    if "月底" in lowered or "月末" in lowered:
        last_day = calendar.monthrange(now.year, now.month)[1]
        return ensure_naive_utc(now.replace(day=last_day, hour=18, minute=0, second=0, microsecond=0))

    days_match = re.search(r"(\d+)\s*天内", sentence)
    if days_match:
        delta_days = int(days_match.group(1))
        target = now + timedelta(days=delta_days)
        return ensure_naive_utc(target.replace(hour=18, minute=0, second=0, microsecond=0))

    # MEM-AMNESIA（2026-09-22）：「N 天后/N天后/N天以后」与「N 天内」同构，
    # 此前缺失导致考试句「期末考试在 7 天后」due_at 永不解析 → commitment
    # 整条丢弃（NORTHSTAR-LOOP1 BP-2 断点①）。
    days_after_match = re.search(r"(\d+)\s*天(?:以后|后)", sentence)
    if days_after_match:
        delta_days = int(days_after_match.group(1))
        target = now + timedelta(days=delta_days)
        return ensure_naive_utc(target.replace(hour=18, minute=0, second=0, microsecond=0))

    absolute_match = re.search(r"(\d{1,2})月(\d{1,2})[日号]?", sentence)
    if absolute_match:
        month = int(absolute_match.group(1))
        day = int(absolute_match.group(2))
        try:
            return ensure_naive_utc(now.replace(month=month, day=day, hour=18, minute=0, second=0, microsecond=0))
        except ValueError:
            return None

    return None
