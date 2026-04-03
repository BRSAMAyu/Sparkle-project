"""User-adaptive routing thresholds for the dual-core router."""

from __future__ import annotations

from uuid import UUID

from app.services.personalization.preference_service import PreferenceService


class RoutingProfileService:
    DEFAULT_PROFILE = {
        "procrastination_threshold": 0.6,
        "emotional_sensitivity": 0.5,
        "directness_preference": 0.5,
    }
    MIN_VALUE = 0.2
    MAX_VALUE = 0.85

    def __init__(self, db, redis=None):
        self.preference_service = PreferenceService(db, redis)

    async def get_profile(self, user_id: UUID) -> dict[str, float]:
        prefs = await self.preference_service.get_preferences(user_id)
        inferred = dict(prefs.inferred or {})
        return self._normalize_profile(inferred.get("routing_profile"))

    async def update_profile(self, user_id: UUID, profile: dict[str, float]) -> dict[str, float]:
        normalized = self._normalize_profile(profile)
        await self.preference_service.update_inferred(
            user_id,
            {"routing_profile": normalized},
        )
        return normalized

    async def record_session_outcome(
        self,
        user_id: UUID,
        *,
        route_mode: str,
        execution_suggestion_ignored: bool = False,
        frustration_after_cognitive: bool = False,
    ) -> dict[str, float]:
        profile = await self.get_profile(user_id)

        if route_mode == "execution_first" and execution_suggestion_ignored:
            profile["procrastination_threshold"] = self._blend(
                profile["procrastination_threshold"],
                0.25,
            )
            profile["directness_preference"] = self._blend(
                profile["directness_preference"],
                0.45,
            )

        if route_mode == "cognitive_first" and frustration_after_cognitive:
            profile["directness_preference"] = self._blend(
                profile["directness_preference"],
                0.7,
            )
            profile["emotional_sensitivity"] = self._blend(
                profile["emotional_sensitivity"],
                0.45,
            )

        await self.preference_service.update_inferred(
            user_id,
            {"routing_profile": profile},
        )
        return profile

    @classmethod
    def _normalize_profile(cls, raw: dict | None) -> dict[str, float]:
        normalized = dict(cls.DEFAULT_PROFILE)
        if isinstance(raw, dict):
            for key in cls.DEFAULT_PROFILE:
                value = raw.get(key)
                if isinstance(value, (int, float)):
                    normalized[key] = cls._clamp(float(value))
        return normalized

    @classmethod
    def _blend(cls, current: float, target: float) -> float:
        return cls._clamp(current * 0.9 + target * 0.1)

    @classmethod
    def _clamp(cls, value: float) -> float:
        return round(min(cls.MAX_VALUE, max(cls.MIN_VALUE, float(value))), 3)
