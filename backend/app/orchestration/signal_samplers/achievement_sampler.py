from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.aurora.growth_signal_contract import GrowthSignalContract


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AchievementSignalSampler:
    """Read-only sampler that converts achievement service reads into Aurora growth signals."""

    async def sample(
        self,
        achievement_service: Any | None,
        user_id: UUID,
        *,
        sampled_at: datetime | None = None,
        context: dict[str, Any] | None = None,
    ) -> GrowthSignalContract:
        sampled_at = sampled_at or _utcnow()
        _ = context or {}
        if achievement_service is None:
            return GrowthSignalContract.build_cold_start(
                user_id=user_id,
                sampled_at=sampled_at,
                fallback_reason="no_achievement_service",
            )

        streak_stats: Any | None = None
        user_achievements: Any | None = None
        fallback_reasons: list[str] = []

        if hasattr(achievement_service, "get_streak_stats"):
            try:
                streak_stats = await achievement_service.get_streak_stats(str(user_id))
            except Exception:
                fallback_reasons.append("streak_stats_unavailable")
        else:
            fallback_reasons.append("missing_get_streak_stats")

        if hasattr(achievement_service, "get_user_achievements"):
            try:
                user_achievements = await achievement_service.get_user_achievements(str(user_id))
            except Exception:
                fallback_reasons.append("user_achievements_unavailable")
        else:
            fallback_reasons.append("missing_get_user_achievements")

        fallback_reason = ";".join(fallback_reasons) if fallback_reasons else None
        contract = GrowthSignalContract.from_service_data(
            user_id=user_id,
            streak_stats=streak_stats,
            user_achievements=user_achievements,
            sampled_at=sampled_at,
            fallback_reason=fallback_reason,
        )
        if contract.cold_start and contract.fallback_reason is None:
            return GrowthSignalContract.build_cold_start(
                user_id=user_id,
                sampled_at=sampled_at,
                fallback_reason=fallback_reason or "empty_achievement_sample",
            )
        return contract


async def sample_achievement_growth_signal(
    achievement_service: Any | None,
    user_id: UUID,
    *,
    sampled_at: datetime | None = None,
    context: dict[str, Any] | None = None,
) -> GrowthSignalContract:
    sampler = AchievementSignalSampler()
    return await sampler.sample(
        achievement_service,
        user_id,
        sampled_at=sampled_at,
        context=context,
    )
