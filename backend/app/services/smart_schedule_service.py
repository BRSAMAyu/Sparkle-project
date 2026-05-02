"""Smart Schedule Service - 智能排程服务"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_event import CalendarEvent
from app.schemas.smart_schedule import (
    SmartScheduleRequest,
    SmartScheduleResponse,
    TimeSlotQuality,
    TimeSlotSuggestion,
)
from app.services.personalization.preference_service import PreferenceService


class SmartScheduleService:
    """智能排程服务"""

    HISTORY_WINDOW_DAYS = 28

    def __init__(self, db: AsyncSession):
        self.db = db

    async def suggest_time_slots(
        self,
        user_id: UUID,
        request: SmartScheduleRequest,
    ) -> SmartScheduleResponse:
        """生成智能时间槽建议。"""
        target_date = request.preferred_date or date.today()
        existing_events = await self._get_existing_events(user_id, target_date)
        schedule_profile = await self._build_schedule_profile(user_id, target_date, existing_events)

        available_slots = self._generate_available_slots(
            target_date,
            existing_events,
            request.exclude_event_ids,
            estimated_minutes=request.estimated_minutes,
        )

        scored_slots: list[tuple[tuple[int, int], float, list[str]]] = []
        for slot in available_slots:
            score, reasons = self._score_time_slot(
                slot=slot,
                energy_cost=request.energy_cost,
                difficulty=request.difficulty,
                schedule_profile=schedule_profile,
            )
            scored_slots.append((slot, score, reasons))

        scored_slots.sort(key=lambda item: (-item[1], item[0][0], item[0][1]))
        suggestions = [
            self._build_suggestion(
                slot=slot,
                score=score,
                target_date=target_date,
                reasons=reasons,
            )
            for slot, score, reasons in scored_slots[:3]
        ]

        return SmartScheduleResponse(
            suggestions=suggestions,
            cognitive_insights=self._build_cognitive_insights(schedule_profile),
            fallback_used=bool(schedule_profile.get("fallback_used")),
        )

    async def _build_schedule_profile(
        self,
        user_id: UUID,
        target_date: date,
        existing_events: list[CalendarEvent],
    ) -> dict[str, object]:
        prefs = await PreferenceService(self.db).get_preferences(user_id)
        explicit = dict(prefs.explicit or {})
        inferred = dict(prefs.inferred or {})

        recent_events = await self._get_recent_events(user_id, target_date)
        focus_hours, focus_source = self._resolve_focus_hours(explicit, inferred)
        inactive_hours = self._normalize_hours(explicit.get("inactive_push_hours", inferred.get("inactive_push_hours")))
        recurring_windows = self._detect_recurring_windows(recent_events, target_date)
        busy_windows = self._derive_busy_windows(existing_events)
        density_level = self._density_level(existing_events)
        exam_urgency = self._resolve_exam_urgency(explicit, inferred)

        signals_used = []
        if focus_source:
            signals_used.append(focus_source)
        if recurring_windows:
            signals_used.append("recurring_calendar_windows")
        if busy_windows:
            signals_used.append("busy_window_density")
        if inactive_hours:
            signals_used.append("inactive_push_hours")
        if exam_urgency:
            signals_used.append("exam_urgency")

        return {
            "focus_hours": focus_hours,
            "focus_source": focus_source,
            "inactive_hours": inactive_hours,
            "recurring_windows": recurring_windows,
            "busy_windows": busy_windows,
            "density_level": density_level,
            "exam_urgency": exam_urgency,
            "signals_used": signals_used,
            "fallback_used": focus_source in {"generic_hours", ""},
        }

    async def _get_existing_events(
        self,
        user_id: UUID,
        target_date: date,
    ) -> list[CalendarEvent]:
        """获取用户指定日期的已有事件。"""
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())

        query = select(CalendarEvent).where(
            CalendarEvent.user_id == user_id,
            CalendarEvent.deleted_at.is_(None),
            CalendarEvent.start_time < day_end,
            CalendarEvent.end_time > day_start,
        ).order_by(CalendarEvent.start_time)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_recent_events(
        self,
        user_id: UUID,
        target_date: date,
    ) -> list[CalendarEvent]:
        since = datetime.combine(target_date, datetime.min.time()) - timedelta(days=self.HISTORY_WINDOW_DAYS)
        until = datetime.combine(target_date, datetime.max.time())
        result = await self.db.execute(
            select(CalendarEvent).where(
                CalendarEvent.user_id == user_id,
                CalendarEvent.deleted_at.is_(None),
                CalendarEvent.start_time >= since,
                CalendarEvent.start_time <= until,
            )
        )
        return list(result.scalars().all())

    def _resolve_focus_hours(
        self,
        explicit: dict[str, object],
        inferred: dict[str, object],
    ) -> tuple[list[int], str]:
        peak_focus_hours = self._normalize_hours(inferred.get("peak_focus_hours"))
        achievement_hours = self._normalize_hours(
            explicit.get("achievement_peak_hours", inferred.get("achievement_peak_hours"))
        )

        if len(peak_focus_hours) >= 2:
            return peak_focus_hours[:3], "peak_focus_hours"
        if achievement_hours:
            return achievement_hours[:3], "achievement_peak_hours"
        if peak_focus_hours:
            return peak_focus_hours[:3], "peak_focus_hours"
        return [9, 10, 14], "generic_hours"

    @staticmethod
    def _normalize_hours(raw_hours: object) -> list[int]:
        hours: list[int] = []
        if not isinstance(raw_hours, list):
            return hours
        for raw in raw_hours:
            try:
                hour = int(raw)
            except (TypeError, ValueError):
                continue
            if 0 <= hour <= 23 and hour not in hours:
                hours.append(hour)
        return hours

    @staticmethod
    def _detect_recurring_windows(events: list[CalendarEvent], target_date: date) -> set[int]:
        pattern_counts: dict[tuple[int, int, int], int] = {}
        for event in events:
            weekday = event.start_time.weekday()
            start_hour = int(event.start_time.hour)
            end_hour = min(23, int(event.end_time.hour) + (1 if event.end_time.minute > 0 else 0))
            pattern = (weekday, start_hour, end_hour)
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        recurring_hours: set[int] = set()
        for (weekday, start_hour, end_hour), count in pattern_counts.items():
            if weekday != target_date.weekday() or count < 2:
                continue
            recurring_hours.update(range(start_hour, end_hour))
        return recurring_hours

    @staticmethod
    def _derive_busy_windows(events: list[CalendarEvent]) -> set[int]:
        busy_windows: set[int] = set()
        ordered = sorted(events, key=lambda item: item.start_time)
        for index, event in enumerate(ordered):
            duration_minutes = max(0, int((event.end_time - event.start_time).total_seconds() / 60))
            end_hour = min(22, event.end_time.hour)
            if duration_minutes >= 90:
                busy_windows.add(end_hour)
            if index + 1 < len(ordered):
                next_event = ordered[index + 1]
                gap_minutes = int((next_event.start_time - event.end_time).total_seconds() / 60)
                if gap_minutes < 60:
                    busy_windows.add(end_hour)
                    busy_windows.add(next_event.start_time.hour)
        return busy_windows

    @staticmethod
    def _density_level(events: list[CalendarEvent]) -> str:
        total_minutes = sum(max(0, int((event.end_time - event.start_time).total_seconds() / 60)) for event in events)
        if len(events) >= 5 or total_minutes >= 360:
            return "high"
        if len(events) >= 3 or total_minutes >= 180:
            return "medium"
        return "low"

    @staticmethod
    def _resolve_exam_urgency(
        explicit: dict[str, object],
        inferred: dict[str, object],
    ) -> dict[str, object] | None:
        for source in (explicit, inferred):
            raw = source.get("exam_urgency")
            if isinstance(raw, dict) and raw.get("days_left") is not None:
                return raw
        return None

    def _generate_available_slots(
        self,
        target_date: date,
        existing_events: list[CalendarEvent],
        exclude_ids: list[str] | None,
        *,
        estimated_minutes: int,
    ) -> list[tuple[int, int]]:
        """生成可用时间槽。"""
        day_start = 6 * 60
        day_end = 23 * 60
        duration = max(5, min(480, int(estimated_minutes or 60)))
        step = 15 if duration <= 45 else 30

        slots: list[tuple[int, int]] = []
        cursor = day_start
        while cursor + duration <= day_end:
            slots.append((cursor, cursor + duration))
            cursor += step

        target_start = datetime.combine(target_date, datetime.min.time())
        target_end = datetime.combine(target_date, datetime.max.time())
        for event in existing_events:
            if exclude_ids and str(event.id) in exclude_ids:
                continue
            event_start = max(event.start_time, target_start)
            event_end = min(event.end_time, target_end)
            start_minutes = event_start.hour * 60 + event_start.minute
            end_minutes = min(day_end, event_end.hour * 60 + event_end.minute)
            if event_end.second or event_end.microsecond:
                end_minutes += 1
            slots = [(start, end) for start, end in slots if end <= start_minutes or start >= end_minutes]
        return slots

    def _score_time_slot(
        self,
        *,
        slot: tuple[int, int],
        energy_cost: int,
        difficulty: int,
        schedule_profile: dict[str, object],
    ) -> tuple[float, list[str]]:
        start_hour = slot[0] // 60
        score = 0.35
        reasons: list[str] = []

        focus_hours = set(schedule_profile.get("focus_hours") or [])
        inactive_hours = set(schedule_profile.get("inactive_hours") or [])
        recurring_windows = set(schedule_profile.get("recurring_windows") or [])
        busy_windows = set(schedule_profile.get("busy_windows") or [])
        density_level = str(schedule_profile.get("density_level") or "low")
        exam_urgency = schedule_profile.get("exam_urgency")
        task_intensity = (energy_cost + difficulty) / 10.0

        if start_hour in focus_hours:
            score += 0.26
            reasons.append("命中用户更容易进入状态的时段")
        elif 9 <= start_hour <= 11:
            score += 0.18
            reasons.append("上午通用高效时段")
        elif 14 <= start_hour <= 17:
            score += 0.13
            reasons.append("下午稳定时段")
        elif 18 <= start_hour <= 21:
            score += 0.06
        else:
            score += 0.02

        if task_intensity >= 0.7:
            if start_hour in focus_hours:
                score += 0.16
                reasons.append("高强度任务与高专注时段匹配")
            elif 9 <= start_hour <= 17:
                score += 0.08
            else:
                score -= 0.08
        elif task_intensity <= 0.4 and start_hour >= 18:
            score += 0.08
            reasons.append("低强度任务可放在较轻松时段")

        if start_hour in recurring_windows:
            score -= 0.24
            reasons.append("该时段与近期重复日程模式重叠")
        if start_hour in busy_windows:
            score -= 0.14
            reasons.append("该时段紧邻密集事件窗口")
        if start_hour in inactive_hours:
            score -= 0.12
            reasons.append("该时段通常不适合打断或推进任务")

        if density_level == "high":
            score -= 0.07
            reasons.append("当天事件密度较高")
        elif density_level == "low":
            score += 0.04

        if isinstance(exam_urgency, dict):
            try:
                days_left = int(exam_urgency.get("days_left"))
            except (TypeError, ValueError):
                days_left = None
            if days_left is not None and days_left <= 14:
                score += max(0.0, (18 - start_hour) * 0.01)
                reasons.append("考试临近，优先更早的可执行时段")

        return (max(0.0, min(score, 1.0)), reasons[:3])

    def _build_suggestion(
        self,
        *,
        slot: tuple[int, int],
        score: float,
        target_date: date,
        reasons: list[str],
    ) -> TimeSlotSuggestion:
        start_minute, end_minute = slot
        start_hour = start_minute // 60
        if score >= 0.74:
            quality = TimeSlotQuality.PEAK
        elif score >= 0.48:
            quality = TimeSlotQuality.NORMAL
        else:
            quality = TimeSlotQuality.LOW

        if reasons:
            reason = "；".join(reasons[:2])
        elif 9 <= start_hour <= 11:
            reason = "上午高效期，适合专注任务"
        elif 14 <= start_hour <= 17:
            reason = "下午稳定期，适合常规推进"
        else:
            reason = "当前可用时段"

        confidence = min(0.95, 0.62 + score * 0.28)
        return TimeSlotSuggestion(
            start_time=self._format_minutes(start_minute),
            end_time=self._format_minutes(end_minute),
            date=target_date,
            quality=quality,
            score=round(score, 2),
            confidence=round(confidence, 2),
            reason=reason,
        )

    @staticmethod
    def _format_minutes(value: int) -> str:
        value = max(0, min(24 * 60, int(value)))
        return f"{value // 60:02d}:{value % 60:02d}"

    def _build_cognitive_insights(self, schedule_profile: dict[str, object]) -> dict[str, object]:
        exam_urgency = schedule_profile.get("exam_urgency")
        exam_pressure = None
        if isinstance(exam_urgency, dict) and exam_urgency.get("days_left") is not None:
            exam_pressure = {
                "days_left": exam_urgency.get("days_left"),
                "urgent": bool(exam_urgency.get("urgent")),
            }

        return {
            "focus_hours": list(schedule_profile.get("focus_hours") or []),
            "busy_windows": [f"{hour:02d}:00" for hour in sorted(schedule_profile.get("busy_windows") or [])],
            "density_level": schedule_profile.get("density_level"),
            "exam_pressure": exam_pressure,
            "signals_used": list(schedule_profile.get("signals_used") or []),
        }
