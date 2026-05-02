"""Calendar busy/free context for Aurora planning surfaces."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_event import CalendarEvent
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.services.personalization.preference_service import PreferenceService


def _strip(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _naive(value: datetime) -> datetime:
    return value.replace(tzinfo=None) if value.tzinfo else value


def _safe_int(value: Any) -> int | None:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _parse_hhmm(value: Any) -> int | None:
    text = _strip(value)
    if not text:
        return None
    try:
        hour, minute = text[-5:].split(":", 1)
        parsed_hour = int(hour)
        parsed_minute = int(minute)
    except (TypeError, ValueError):
        return None
    if not (0 <= parsed_hour <= 23 and 0 <= parsed_minute <= 59):
        return None
    return parsed_hour * 60 + parsed_minute


class CalendarService:
    """Read-only calendar availability and conflict analysis."""

    DAY_START_HOUR = 7
    DAY_END_HOUR = 22
    PLANNING_DAYS = 7
    MIN_LONG_TASK_MINUTES = 60

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_busy_free_context(
        self,
        user_id: UUID,
        *,
        start_date: date | None = None,
        days: int = PLANNING_DAYS,
        include_conflicts: bool = True,
    ) -> dict[str, Any]:
        """Return the next ``days`` of busy events, free blocks, and pressure hints."""
        anchor = start_date or datetime.utcnow().date()
        days = max(1, min(int(days or self.PLANNING_DAYS), 14))
        window_start = datetime.combine(anchor, time.min)
        window_end = window_start + timedelta(days=days)

        events = await self._get_events(user_id, window_start, window_end)
        events_by_date = self._group_events_by_date(events, anchor=anchor, days=days)
        busy_events_by_date: dict[str, list[dict[str, Any]]] = {}
        time_blocks_by_date: dict[str, list[dict[str, str]]] = {}
        available_minutes_by_date: dict[str, int] = {}
        busy_minutes_by_date: dict[str, int] = {}

        for offset in range(days):
            target_day = anchor + timedelta(days=offset)
            day_key = target_day.isoformat()
            day_events = events_by_date.get(day_key, [])
            serialized = self.serialize_busy_events(day_events)
            if serialized:
                busy_events_by_date[day_key] = serialized
            blocks = self.derive_available_time_blocks(day_events, reference_day=target_day)
            time_blocks_by_date[day_key] = blocks
            available_minutes_by_date[day_key] = self._minutes_from_blocks(blocks)
            busy_minutes_by_date[day_key] = self._busy_minutes(day_events, reference_day=target_day)

        upcoming_deadlines = self._build_upcoming_deadlines(events)
        exam_urgency = await self._resolve_exam_urgency(user_id, events, anchor=anchor)
        workload_density = self.derive_workload_density(events)
        time_conflicts = (
            await self.detect_time_conflicts(
                user_id=user_id,
                start_date=anchor,
                days=days,
                busy_events_by_date=busy_events_by_date,
                available_minutes_by_date=available_minutes_by_date,
            )
            if include_conflicts
            else []
        )

        today_key = anchor.isoformat()
        next_three_keys = [(anchor + timedelta(days=offset)).isoformat() for offset in range(min(3, days))]
        next_three_available = sum(available_minutes_by_date.get(key, 0) for key in next_three_keys)
        next_three_busy = sum(
            1
            for key in next_three_keys
            if available_minutes_by_date.get(key, 0) < self.MIN_LONG_TASK_MINUTES * 2
        )
        planning_intensity_hint = "lower" if next_three_busy >= min(3, days) else "normal"

        return {
            "today": today_key,
            "day_type": "weekend" if anchor.weekday() >= 5 else "weekday",
            "upcoming_deadlines": upcoming_deadlines[:6],
            "time_blocks_today": time_blocks_by_date.get(today_key, []),
            "time_blocks_by_date": time_blocks_by_date,
            "available_minutes_by_date": available_minutes_by_date,
            "busy_minutes_by_date": busy_minutes_by_date,
            "busy_events": busy_events_by_date.get(today_key, []),
            "busy_events_by_date": busy_events_by_date,
            "workload_density": workload_density,
            "exam_urgency": exam_urgency or {},
            "time_conflicts": time_conflicts[:6],
            "next_time_conflict": time_conflicts[0] if time_conflicts else None,
            "capacity_summary": {
                "next_3_days_available_minutes": next_three_available,
                "next_3_days_tight_count": next_three_busy,
                "planning_intensity_hint": planning_intensity_hint,
            },
            "today_profile": {
                "date": today_key,
                "day_type": "weekend" if anchor.weekday() >= 5 else "weekday",
                "available_minutes": available_minutes_by_date.get(today_key, 0),
                "busy_minutes": busy_minutes_by_date.get(today_key, 0),
                "density": self.derive_daily_density(events_by_date.get(today_key, [])),
            },
        }

    async def detect_time_conflicts(
        self,
        *,
        user_id: UUID,
        start_date: date,
        days: int,
        busy_events_by_date: dict[str, list[dict[str, Any]]] | None = None,
        available_minutes_by_date: dict[str, int] | None = None,
    ) -> list[dict[str, Any]]:
        """Find task or plan deadlines that collide with a tight calendar day."""
        end_date = start_date + timedelta(days=days)
        busy_by_date = busy_events_by_date or {}
        available_by_date = available_minutes_by_date or {}
        conflicts: list[dict[str, Any]] = []

        task_result = await self.db.execute(
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.deleted_at.is_(None),
                Task.due_date.is_not(None),
                Task.due_date >= start_date,
                Task.due_date < end_date,
                Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.STUCK]),
            )
            .order_by(Task.due_date.asc(), Task.priority.desc(), Task.created_at.asc())
            .limit(20)
        )
        for task in task_result.scalars().all():
            due = task.due_date
            if due is None:
                continue
            day_key = due.isoformat()
            available = int(available_by_date.get(day_key, self._default_available_minutes()))
            estimated = int(task.estimated_minutes or 0)
            overlap = self._scheduled_task_overlap(task, busy_by_date.get(day_key, []))
            if overlap or (estimated >= self.MIN_LONG_TASK_MINUTES and available < estimated):
                conflicts.append(
                    {
                        "type": "task_deadline",
                        "title": task.title,
                        "date": day_key,
                        "task_id": str(task.id),
                        "plan_id": str(task.plan_id) if task.plan_id else None,
                        "estimated_minutes": estimated,
                        "available_minutes": available,
                        "message": "时间可能不够",
                        "conflicting_event": overlap,
                    }
                )

        plan_result = await self.db.execute(
            select(Plan)
            .where(
                Plan.user_id == user_id,
                Plan.deleted_at.is_(None),
                Plan.is_active.is_(True),
                Plan.target_date.is_not(None),
                Plan.target_date >= start_date,
                Plan.target_date < end_date,
            )
            .order_by(Plan.target_date.asc(), Plan.priority.desc())
            .limit(10)
        )
        for plan in plan_result.scalars().all():
            target = plan.target_date
            if target is None:
                continue
            day_key = target.isoformat()
            available = int(available_by_date.get(day_key, self._default_available_minutes()))
            required = int(plan.daily_available_minutes or 60)
            high_pressure = self._first_high_pressure_event(busy_by_date.get(day_key, []))
            if high_pressure and available < max(required, self.MIN_LONG_TASK_MINUTES):
                conflicts.append(
                    {
                        "type": "plan_deadline",
                        "title": plan.name,
                        "date": day_key,
                        "plan_id": str(plan.id),
                        "required_minutes": required,
                        "available_minutes": available,
                        "message": "时间可能不够",
                        "conflicting_event": high_pressure,
                    }
                )

        conflicts.sort(key=lambda item: (str(item.get("date") or ""), item.get("type") != "plan_deadline"))
        return conflicts

    async def _get_events(
        self,
        user_id: UUID,
        window_start: datetime,
        window_end: datetime,
    ) -> list[CalendarEvent]:
        result = await self.db.execute(
            select(CalendarEvent)
            .where(
                CalendarEvent.user_id == user_id,
                CalendarEvent.deleted_at.is_(None),
                CalendarEvent.start_time < window_end,
                CalendarEvent.end_time > window_start,
            )
            .order_by(CalendarEvent.start_time)
        )
        return list(result.scalars().all())

    async def _resolve_exam_urgency(
        self,
        user_id: UUID,
        events: list[CalendarEvent],
        *,
        anchor: date,
    ) -> dict[str, Any] | None:
        try:
            prefs = await PreferenceService(self.db).get_preferences(user_id)
            merged: dict[str, Any] = {}
            if prefs:
                merged.update(_as_dict(prefs.inferred))
                merged.update(_as_dict(prefs.explicit))
            raw = _as_dict(merged.get("exam_urgency"))
            if raw.get("days_left") is not None:
                return raw
        except Exception:
            pass

        exam_events = [event for event in events if self.calendar_event_kind(event) == "exam"]
        if not exam_events:
            return None
        event = min(exam_events, key=lambda item: _naive(item.start_time))
        event_day = _naive(event.start_time).date()
        days_left = max(0, (event_day - anchor).days)
        return {
            "days_left": days_left,
            "urgent": days_left <= 14,
            "title": event.title,
            "date": event_day.isoformat(),
            "source": "calendar",
        }

    def _build_upcoming_deadlines(self, events: list[CalendarEvent]) -> list[dict[str, Any]]:
        deadlines: list[dict[str, Any]] = []
        for event in events:
            kind = self.calendar_event_kind(event)
            if event.task_id is None and event.plan_id is None and kind not in {"exam", "deadline"}:
                continue
            deadlines.append(
                {
                    "title": event.title,
                    "start_time": event.start_time.isoformat(),
                    "end_time": event.end_time.isoformat(),
                    "source": "task" if event.task_id else "plan" if event.plan_id else "calendar",
                    "kind": kind,
                }
            )
        return deadlines

    @classmethod
    def serialize_busy_events(cls, events: list[CalendarEvent]) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        for event in events:
            start = _naive(event.start_time)
            end = _naive(event.end_time)
            if end <= start:
                continue
            kind = cls.calendar_event_kind(event)
            serialized.append(
                {
                    "title": event.title,
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                    "start": start.strftime("%H:%M"),
                    "end": end.strftime("%H:%M"),
                    "date": start.date().isoformat(),
                    "kind": kind,
                    "is_all_day": bool(event.is_all_day),
                    "source": event.source,
                    "task_id": str(event.task_id) if event.task_id else None,
                    "plan_id": str(event.plan_id) if event.plan_id else None,
                }
            )
        return serialized[:12]

    @classmethod
    def derive_available_time_blocks(cls, events: list[CalendarEvent], *, reference_day: date) -> list[dict[str, str]]:
        day_start = datetime.combine(reference_day, time.min).replace(hour=cls.DAY_START_HOUR)
        day_end = datetime.combine(reference_day, time.min).replace(hour=cls.DAY_END_HOUR)
        busy_blocks: list[tuple[datetime, datetime]] = []
        for event in events:
            start = _naive(event.start_time)
            end = _naive(event.end_time)
            if event.is_all_day:
                start = day_start
                end = day_end
            start = max(start, day_start)
            end = min(end, day_end)
            if start < end:
                busy_blocks.append((start, end))

        free_blocks: list[dict[str, str]] = []
        cursor = day_start
        for start, end in sorted(busy_blocks, key=lambda item: item[0]):
            if start > cursor:
                free_blocks.append({"start": cursor.strftime("%H:%M"), "end": start.strftime("%H:%M")})
            cursor = max(cursor, end)
        if cursor < day_end:
            free_blocks.append({"start": cursor.strftime("%H:%M"), "end": day_end.strftime("%H:%M")})
        return free_blocks[:6]

    @staticmethod
    def calendar_event_kind(event: CalendarEvent) -> str:
        metadata = _as_dict(event.source_metadata)
        raw_kind = _strip(
            metadata.get("kind")
            or metadata.get("event_type")
            or metadata.get("type")
            or metadata.get("category")
        ).lower()
        if raw_kind in {"exam", "test", "quiz", "deadline", "class", "course", "lecture"}:
            return "class" if raw_kind in {"course", "lecture"} else raw_kind

        title = _strip(event.title).lower()
        if any(token in title for token in ("考试", "期末", "测验", "exam", "quiz", "test")):
            return "exam"
        if any(token in title for token in ("截止", "ddl", "deadline", "due")):
            return "deadline"
        if any(token in title for token in ("上课", "课程", "课堂", "lecture", "class", "course", "seminar", "lab")):
            return "class"
        return "busy"

    @classmethod
    def derive_workload_density(cls, events: list[CalendarEvent]) -> str:
        if not events:
            return "low"
        by_day: defaultdict[date, int] = defaultdict(int)
        total_minutes = 0
        for event in events:
            event_day = _naive(event.start_time).date()
            by_day[event_day] += 1
            total_minutes += max(0, int((_naive(event.end_time) - _naive(event.start_time)).total_seconds() / 60))
        active_days = max(len(by_day), 1)
        avg_events = sum(by_day.values()) / active_days
        avg_minutes = total_minutes / active_days
        if avg_events >= 4 or avg_minutes >= 240:
            return "high"
        if avg_events >= 2 or avg_minutes >= 120:
            return "medium"
        return "low"

    @classmethod
    def derive_daily_density(cls, events: list[CalendarEvent]) -> str:
        total_minutes = cls._busy_minutes(events, reference_day=_naive(events[0].start_time).date()) if events else 0
        if len(events) >= 5 or total_minutes >= 360:
            return "high"
        if len(events) >= 3 or total_minutes >= 180:
            return "medium"
        return "low"

    @staticmethod
    def _group_events_by_date(
        events: list[CalendarEvent],
        *,
        anchor: date,
        days: int,
    ) -> dict[str, list[CalendarEvent]]:
        grouped: dict[str, list[CalendarEvent]] = {str(anchor + timedelta(days=offset)): [] for offset in range(days)}
        for event in events:
            start = _naive(event.start_time).date()
            end = _naive(event.end_time).date()
            cursor = max(start, anchor)
            last = min(end, anchor + timedelta(days=days - 1))
            while cursor <= last:
                grouped.setdefault(cursor.isoformat(), []).append(event)
                cursor += timedelta(days=1)
        return grouped

    @classmethod
    def _busy_minutes(cls, events: list[CalendarEvent], *, reference_day: date) -> int:
        day_start = datetime.combine(reference_day, time.min).replace(hour=cls.DAY_START_HOUR)
        day_end = datetime.combine(reference_day, time.min).replace(hour=cls.DAY_END_HOUR)
        total = 0
        for event in events:
            start = day_start if event.is_all_day else max(_naive(event.start_time), day_start)
            end = day_end if event.is_all_day else min(_naive(event.end_time), day_end)
            if end > start:
                total += int((end - start).total_seconds() / 60)
        return min(total, cls._default_available_minutes())

    @classmethod
    def _default_available_minutes(cls) -> int:
        return (cls.DAY_END_HOUR - cls.DAY_START_HOUR) * 60

    @staticmethod
    def _minutes_from_blocks(blocks: list[dict[str, str]]) -> int:
        total = 0
        for block in blocks:
            start = _parse_hhmm(block.get("start"))
            end = _parse_hhmm(block.get("end"))
            if start is not None and end is not None and end > start:
                total += end - start
        return total

    @staticmethod
    def _scheduled_task_overlap(task: Task, busy_events: list[dict[str, Any]]) -> dict[str, Any] | None:
        guide = _as_dict(task.guide_json)
        start = _parse_hhmm(guide.get("scheduled_start_time") or guide.get("start_time"))
        end = _parse_hhmm(guide.get("scheduled_end_time") or guide.get("end_time"))
        if start is None:
            return None
        if end is None:
            end = start + int(task.estimated_minutes or 30)
        for event in busy_events:
            event_start = _parse_hhmm(event.get("start") or event.get("start_time"))
            event_end = _parse_hhmm(event.get("end") or event.get("end_time"))
            if event_start is None or event_end is None:
                continue
            if start < event_end and event_start < end:
                return event
        return None

    @classmethod
    def _first_high_pressure_event(cls, events: list[dict[str, Any]]) -> dict[str, Any] | None:
        for event in events:
            kind = _strip(event.get("kind")).lower()
            title = _strip(event.get("title")).lower()
            if kind in {"exam", "quiz", "test", "class", "deadline"} or any(
                token in title
                for token in ("考试", "期末", "测验", "上课", "课程", "deadline", "exam", "quiz", "test", "class")
            ):
                return event
        return events[0] if events else None
