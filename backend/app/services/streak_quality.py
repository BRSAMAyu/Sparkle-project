"""Quality-weighted streak signals for experience surfaces."""

from __future__ import annotations

import json
import logging

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import StreakDayStatus, UserStreakDay, UserStreakStats
from app.models.galaxy import StudyRecord
from app.models.task import Task, TaskStatus, TaskType

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    return datetime.combine(day, time.min), datetime.combine(day + timedelta(days=1), time.min)


def _ratio(numerator: int | float, denominator: int | float) -> float:
    if denominator <= 0:
        return 0.0
    return max(0.0, min(1.0, float(numerator) / float(denominator)))


@dataclass(frozen=True)
class StreakQuality:
    effective_minutes: int
    core_tasks_completed: int
    difficult_breakthroughs: int
    plan_consistency: float
    recovery_score: float
    quality_score: float
    is_quality_day: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["plan_consistency"] = round(self.plan_consistency, 3)
        payload["recovery_score"] = round(self.recovery_score, 3)
        payload["quality_score"] = round(self.quality_score, 3)
        return payload


class StreakQualityService:
    """Compute streak quality from existing learning, task, and streak records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._fatigue_cache: dict[str, dict[str, Any]] = {}
        self._crisis_cache: dict[str, bool] = {}

    async def compute_quality(self, user_id: UUID | str, target_date: date | None = None) -> StreakQuality:
        day = target_date or _utcnow().date()
        start, end = _day_bounds(day)

        effective_minutes = await self._effective_minutes(user_id, start, end)
        core_tasks_completed = await self._core_tasks_completed(user_id, start, end)
        difficult_breakthroughs = await self._difficult_breakthroughs(user_id, start, end)
        plan_consistency = await self._plan_consistency(user_id, day, start, end)
        recovery_score = await self._recovery_score(user_id, day)

        minute_score = _ratio(effective_minutes, 90)
        core_task_score = _ratio(core_tasks_completed, 2)
        breakthrough_score = _ratio(difficult_breakthroughs, 1)
        quality_score = (
            minute_score * 0.32
            + core_task_score * 0.26
            + breakthrough_score * 0.20
            + plan_consistency * 0.14
            + recovery_score * 0.08
        )
        quality_score = max(0.0, min(1.0, quality_score))

        # ── GROW-002: integrate fatigue/crisis/late-night into quality ──
        fatigue_state = await self._read_fatigue_state(user_id)
        crisis_active = await self._read_crisis_state(user_id)
        fatigue_level = fatigue_state.get("fatigue_level", "low")
        is_late_night = any("深夜" in e for e in fatigue_state.get("evidence", []))

        if fatigue_level == "critical":
            quality_score = 0.0
        elif fatigue_level == "high":
            quality_score = max(0.0, quality_score - 0.20)
            if is_late_night:
                quality_score = min(quality_score, 0.55)
        elif fatigue_level == "medium":
            quality_score = max(0.0, quality_score - 0.10)
            if is_late_night:
                quality_score = min(quality_score, 0.65)
        elif is_late_night:
            quality_score = min(quality_score, 0.75)

        if crisis_active:
            quality_score = max(0.0, quality_score - 0.10)

        is_quality_day = quality_score >= 0.60 and (
            effective_minutes >= 25 or core_tasks_completed > 0 or difficult_breakthroughs > 0
        )

        return StreakQuality(
            effective_minutes=effective_minutes,
            core_tasks_completed=core_tasks_completed,
            difficult_breakthroughs=difficult_breakthroughs,
            plan_consistency=plan_consistency,
            recovery_score=recovery_score,
            quality_score=quality_score,
            is_quality_day=is_quality_day,
        )

    async def current_streak(self, user_id: UUID | str) -> int:
        result = await self.db.execute(select(UserStreakStats).where(UserStreakStats.user_id == user_id))
        stats = result.scalar_one_or_none()
        return int(stats.current_streak or 0) if stats else 0

    async def quality_streak(self, user_id: UUID | str, target_date: date | None = None) -> int:
        day = target_date or _utcnow().date()
        count = 0
        for offset in range(0, 90):
            quality = await self.compute_quality(user_id, day - timedelta(days=offset))
            if not quality.is_quality_day:
                break
            count += 1
        return count

    async def weekly_quality_trend(
        self,
        user_id: UUID | str,
        target_date: date | None = None,
    ) -> list[dict[str, Any]]:
        today = target_date or _utcnow().date()
        trend: list[dict[str, Any]] = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            quality = await self.compute_quality(user_id, day)
            trend.append(
                {
                    "date": day.isoformat(),
                    "quality_score": round(quality.quality_score, 3),
                    "breakdown": quality.to_dict(),
                }
            )
        return trend

    async def celebration_trigger(
        self,
        user_id: UUID | str,
        today_quality: StreakQuality,
        quality_streak: int,
    ) -> dict[str, str] | None:
        if not today_quality.is_quality_day:
            return None

        strongest_signal = max(
            [
                ("effective_minutes", today_quality.effective_minutes),
                ("core_tasks_completed", today_quality.core_tasks_completed),
                ("difficult_breakthroughs", today_quality.difficult_breakthroughs),
            ],
            key=lambda item: item[1],
        )[0]

        if strongest_signal == "difficult_breakthroughs":
            evidence = f"You broke through {today_quality.difficult_breakthroughs} difficult node today."
            reason = "difficult_breakthrough"
        elif strongest_signal == "core_tasks_completed":
            evidence = f"You completed {today_quality.core_tasks_completed} core task today."
            reason = "core_task_completed"
        else:
            evidence = f"You logged {today_quality.effective_minutes} effective learning minutes today."
            reason = "effective_learning_time"

        return {
            "reason": reason,
            "evidence": evidence,
            "suggested_message": (
                f"Quality streak day {quality_streak}: {evidence} "
                "This streak is counting real progress, not just opening the app."
            ),
        }

    async def build_payload(self, user_id: UUID | str) -> dict[str, Any]:
        today_quality = await self.compute_quality(user_id)
        quality_streak = await self.quality_streak(user_id)
        return {
            "current_streak": await self.current_streak(user_id),
            "quality_streak": quality_streak,
            "today_quality": today_quality.to_dict(),
            "weekly_quality_trend": await self.weekly_quality_trend(user_id),
            "celebration_trigger": await self.celebration_trigger(user_id, today_quality, quality_streak),
        }

    async def _effective_minutes(self, user_id: UUID | str, start: datetime, end: datetime) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.sum(StudyRecord.study_minutes), 0)).where(
                and_(
                    StudyRecord.user_id == user_id,
                    StudyRecord.created_at >= start,
                    StudyRecord.created_at < end,
                    StudyRecord.deleted_at.is_(None),
                )
            )
        )
        return int(result.scalar_one() or 0)

    async def _core_tasks_completed(self, user_id: UUID | str, start: datetime, end: datetime) -> int:
        result = await self.db.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.user_id == user_id,
                    Task.status == TaskStatus.COMPLETED,
                    Task.completed_at >= start,
                    Task.completed_at < end,
                    Task.deleted_at.is_(None),
                    (
                        (Task.priority >= 2)
                        | (Task.type.in_([TaskType.LEARNING, TaskType.TRAINING, TaskType.ERROR_FIX]))
                        | (Task.difficulty >= 4)
                    ),
                )
            )
        )
        return int(result.scalar_one() or 0)

    async def _difficult_breakthroughs(self, user_id: UUID | str, start: datetime, end: datetime) -> int:
        mastery_result = await self.db.execute(
            select(func.count(StudyRecord.id)).where(
                and_(
                    StudyRecord.user_id == user_id,
                    StudyRecord.created_at >= start,
                    StudyRecord.created_at < end,
                    StudyRecord.mastery_delta >= 0.15,
                    StudyRecord.deleted_at.is_(None),
                )
            )
        )
        task_result = await self.db.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.user_id == user_id,
                    Task.status == TaskStatus.COMPLETED,
                    Task.completed_at >= start,
                    Task.completed_at < end,
                    Task.difficulty >= 4,
                    Task.deleted_at.is_(None),
                )
            )
        )
        return int(mastery_result.scalar_one() or 0) + int(task_result.scalar_one() or 0)

    async def _plan_consistency(self, user_id: UUID | str, day: date, start: datetime, end: datetime) -> float:
        due_result = await self.db.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.user_id == user_id,
                    Task.due_date == day,
                    Task.deleted_at.is_(None),
                )
            )
        )
        due_count = int(due_result.scalar_one() or 0)
        if due_count == 0:
            return 1.0 if await self._effective_minutes(user_id, start, end) >= 25 else 0.0

        completed_result = await self.db.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.user_id == user_id,
                    Task.due_date == day,
                    Task.status == TaskStatus.COMPLETED,
                    Task.completed_at >= start,
                    Task.completed_at < end,
                    Task.deleted_at.is_(None),
                )
            )
        )
        return _ratio(int(completed_result.scalar_one() or 0), due_count)

    async def _recovery_score(self, user_id: UUID | str, day: date) -> float:
        start_day = day - timedelta(days=30)
        result = await self.db.execute(
            select(UserStreakDay)
            .where(
                and_(
                    UserStreakDay.user_id == user_id,
                    UserStreakDay.day >= start_day,
                    UserStreakDay.day <= day,
                    UserStreakDay.deleted_at.is_(None),
                )
            )
            .order_by(UserStreakDay.day.asc())
        )
        records = result.scalars().all()
        if not records:
            return 0.0

        recoveries = 0
        previous_missed = False
        for record in records:
            status = record.status.value if hasattr(record.status, "value") else str(record.status)
            if status == StreakDayStatus.ACTIVE.value and previous_missed:
                recoveries += 1
            previous_missed = status in {StreakDayStatus.MISSED.value, StreakDayStatus.FROZEN.value}
        return min(1.0, recoveries / 2)

    async def _read_fatigue_state(self, user_id: UUID | str) -> dict[str, Any]:
        uid = str(user_id)
        if uid in self._fatigue_cache:
            return self._fatigue_cache[uid]
        try:
            from app.core.cache import cache_service

            raw = await cache_service.get(f"spine:fatigue:{uid}:latest")
            if raw:
                result: dict[str, Any] = json.loads(raw)
            else:
                result = {"fatigue_level": "low", "evidence": []}
        except Exception:
            logger.warning("Failed to read fatigue state for user %s", uid, exc_info=True)
            result = {"fatigue_level": "low", "evidence": []}
        self._fatigue_cache[uid] = result
        return result

    async def _read_crisis_state(self, user_id: UUID | str) -> bool:
        uid = str(user_id)
        if uid in self._crisis_cache:
            return self._crisis_cache[uid]
        try:
            from app.core.cache import cache_service

            raw = await cache_service.get(f"spine:crisis:{uid}:latest")
            result = bool(json.loads(raw)) if raw else False
        except Exception:
            logger.warning("Failed to read crisis state for user %s", uid, exc_info=True)
            result = False
        self._crisis_cache[uid] = result
        return result
