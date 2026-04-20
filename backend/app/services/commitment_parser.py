from __future__ import annotations

import calendar
import re
from datetime import datetime, timedelta, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_commitment_due_at(text: str, *, reference_time: datetime | None = None) -> datetime | None:
    sentence = str(text or "").strip()
    if not sentence:
        return None

    now = reference_time or _utcnow()
    lowered = sentence.lower()

    if "明天下午" in lowered:
        base = now + timedelta(days=1)
        return base.replace(hour=15, minute=0, second=0, microsecond=0)
    if "明天晚上" in lowered or "明晚" in lowered:
        base = now + timedelta(days=1)
        return base.replace(hour=20, minute=0, second=0, microsecond=0)
    if "明天" in lowered:
        base = now + timedelta(days=1)
        return base.replace(hour=9, minute=0, second=0, microsecond=0)
    if "今天晚上" in lowered or "今晚" in lowered:
        return now.replace(hour=20, minute=0, second=0, microsecond=0)
    if "今天下午" in lowered or "今天" in lowered:
        return now.replace(hour=15, minute=0, second=0, microsecond=0)
    if "这周" in lowered or "本周" in lowered:
        days_until_sunday = max(0, 6 - now.weekday())
        target = now + timedelta(days=days_until_sunday)
        return target.replace(hour=18, minute=0, second=0, microsecond=0)
    if "月底" in lowered or "月末" in lowered:
        last_day = calendar.monthrange(now.year, now.month)[1]
        return now.replace(day=last_day, hour=18, minute=0, second=0, microsecond=0)

    days_match = re.search(r"(\d+)\s*天内", sentence)
    if days_match:
        delta_days = int(days_match.group(1))
        target = now + timedelta(days=delta_days)
        return target.replace(hour=18, minute=0, second=0, microsecond=0)

    absolute_match = re.search(r"(\d{1,2})月(\d{1,2})[日号]?", sentence)
    if absolute_match:
        month = int(absolute_match.group(1))
        day = int(absolute_match.group(2))
        try:
            return now.replace(month=month, day=day, hour=18, minute=0, second=0, microsecond=0)
        except ValueError:
            return None

    return None
