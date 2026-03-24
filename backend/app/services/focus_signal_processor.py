"""
Focus signal processor - translate focus sessions into inferred preferences.
"""
from __future__ import annotations

from datetime import timezone, datetime, timedelta
from statistics import median
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.focus import FocusSession, FocusStatus
from app.services.cognitive_service import CognitiveService
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_write_service import ProfileWriteService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FocusSignalProcessor:
    """Process focus session events and update inferred preferences."""

    WINDOW_DAYS = 14

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis or cache_service.redis
        self.pref_service = PreferenceService(db, self.redis)
        self.profile_write_service = ProfileWriteService(db, self.redis)

    async def process_focus_event(self, user_id: UUID) -> None:
        now = _utcnow()
        since = now - timedelta(days=self.WINDOW_DAYS)
        result = await self.db.execute(
            select(FocusSession).where(
                FocusSession.user_id == user_id,
                FocusSession.start_time >= since,
            )
        )
        sessions = list(result.scalars().all())
        if not sessions:
            return

        completed_sessions = [s for s in sessions if s.status == FocusStatus.COMPLETED]
        updates: dict[str, object] = {}

        durations = [s.duration_minutes for s in completed_sessions if s.duration_minutes]
        if durations:
            preferred_duration = int(median(durations))
            prefs = await self.pref_service.get_preferences(user_id)
            explicit_focus = (prefs.explicit or {}).get("focus_duration_preference")
            if explicit_focus:
                delta_ratio = abs(preferred_duration - explicit_focus) / max(1, explicit_focus)
                if delta_ratio > 0.3:
                    updates["preferred_focus_duration"] = preferred_duration
            else:
                updates["preferred_focus_duration"] = preferred_duration

        peak_hours = self._compute_peak_focus_hours(sessions)
        if peak_hours:
            updates["peak_focus_hours"] = peak_hours

        completion_rate = self._completion_rate(sessions)
        if completion_rate is not None:
            total_sessions = len(sessions)
            if total_sessions >= 10 and completion_rate < 0.5:
                updates["focus_completion_rate"] = round(completion_rate, 3)
                await self._create_low_completion_fragment(user_id, completion_rate, total_sessions, now)

        if updates:
            await self.profile_write_service.update_inferred_preference(
                user_id=user_id,
                updates=updates,
                source="ai_inferred",
            )

    @staticmethod
    def _compute_peak_focus_hours(sessions: list[FocusSession]) -> list[int]:
        hour_stats: dict[int, dict[str, int]] = {}
        for session in sessions:
            if not session.start_time:
                continue
            hour = session.start_time.hour
            if hour not in hour_stats:
                hour_stats[hour] = {"completed": 0, "total": 0}
            hour_stats[hour]["total"] += 1
            if session.status == FocusStatus.COMPLETED:
                hour_stats[hour]["completed"] += 1

        scored: list[tuple[float, int, int]] = []
        for hour, stats in hour_stats.items():
            total = stats["total"]
            completed = stats["completed"]
            if total <= 0:
                continue
            rate = completed / total
            scored.append((rate, completed, hour))

        scored.sort(reverse=True)
        return [hour for _, _, hour in scored[:3]]

    @staticmethod
    def _completion_rate(sessions: list[FocusSession]) -> float | None:
        if not sessions:
            return None
        completed = sum(1 for s in sessions if s.status == FocusStatus.COMPLETED)
        return completed / len(sessions)

    async def _create_low_completion_fragment(
        self,
        user_id: UUID,
        completion_rate: float,
        total_sessions: int,
        now: datetime,
    ) -> None:
        try:
            service = CognitiveService(self.db)
            await service.create_fragment(
                user_id=user_id,
                content=(
                    "Focus completion rate has been low over the last two weeks. "
                    "Consider shortening sessions or adjusting pacing. "
                    f"Completion rate {completion_rate:.2f} across {total_sessions} sessions."
                ),
                source_type="behavior",
                error_tags=["focus.low_completion"],
                context_tags={
                    "focus_completion_rate": completion_rate,
                    "focus_session_count": total_sessions,
                },
                source_event_id=f"focus.low_completion:{user_id}:{now.date().isoformat()}",
            )
        except Exception as exc:
            logger.warning("Failed to create focus completion fragment: %s", exc)
