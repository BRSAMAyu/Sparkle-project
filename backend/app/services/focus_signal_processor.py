"""
Focus signal processor - translate focus sessions into inferred preferences.
"""
from __future__ import annotations

from datetime import timezone, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.focus import FocusSession, FocusStatus
from app.services.cognitive_service import CognitiveService
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_write_service import ProfileWriteService
from app.services.signal_adaptation import recency_weight, weighted_median


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

        duration_samples = [
            (
                float(s.duration_minutes),
                recency_weight(s.start_time, now=now, half_life_days=5.0, min_weight=0.35),
            )
            for s in completed_sessions
            if s.duration_minutes
        ]
        preferred_duration_value = weighted_median(duration_samples)
        if preferred_duration_value is not None:
            preferred_duration = int(round(preferred_duration_value))
            prefs = await self.pref_service.get_preferences(user_id)
            explicit_focus = (prefs.explicit or {}).get("focus_duration_preference")
            if explicit_focus:
                delta_ratio = abs(preferred_duration - explicit_focus) / max(1, explicit_focus)
                if delta_ratio > 0.3:
                    updates["preferred_focus_duration"] = preferred_duration
            else:
                updates["preferred_focus_duration"] = preferred_duration

        peak_hours = self._compute_peak_focus_hours(sessions, now=now)
        if peak_hours:
            updates["peak_focus_hours"] = peak_hours

        completion_rate = self._completion_rate(sessions, now=now)
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
    def _compute_peak_focus_hours(sessions: list[FocusSession], now: datetime | None = None) -> list[int]:
        current = now or _utcnow()
        hour_stats: dict[int, dict[str, float]] = {}
        for session in sessions:
            if not session.start_time:
                continue
            hour = session.start_time.hour
            if hour not in hour_stats:
                hour_stats[hour] = {"completed": 0.0, "total": 0.0}
            weight = recency_weight(session.start_time, now=current, half_life_days=5.0, min_weight=0.35)
            hour_stats[hour]["total"] += weight
            if session.status == FocusStatus.COMPLETED:
                hour_stats[hour]["completed"] += weight

        scored: list[tuple[float, float, int]] = []
        for hour, stats in hour_stats.items():
            total = stats["total"]
            completed = stats["completed"]
            if total <= 0:
                continue
            # Bayesian smoothing avoids a single perfect session dominating a much larger sample.
            smoothed_rate = (completed + 1.5) / (total + 3.0)
            support = min(total / 4.0, 1.0)
            score = smoothed_rate * (0.7 + support * 0.3)
            scored.append((score, total, hour))

        scored.sort(reverse=True)
        return [hour for _, _, hour in scored[:3]]

    @staticmethod
    def _completion_rate(sessions: list[FocusSession], now: datetime | None = None) -> float | None:
        if not sessions:
            return None
        current = now or _utcnow()
        weighted_total = 0.0
        weighted_completed = 0.0
        for session in sessions:
            weight = recency_weight(session.start_time, now=current, half_life_days=5.0, min_weight=0.35)
            weighted_total += weight
            if session.status == FocusStatus.COMPLETED:
                weighted_completed += weight
        if weighted_total <= 0:
            return None
        return weighted_completed / weighted_total

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
