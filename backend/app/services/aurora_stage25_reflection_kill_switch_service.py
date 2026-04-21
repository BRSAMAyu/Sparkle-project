from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service


class AuroraStage25ReflectionKillSwitchService:
    PREFIX = "aurora:stage25:killswitch:"
    MODE_KEY = "reflection_wire_mode"
    RULE_Y_STREAK_KEY = "rule_y_breach_streak"
    DEFAULT_MODES = {"off", "shadow", "live"}

    async def get_mode(self) -> str:
        redis_client = cache_service.redis
        if redis_client is None:
            return self._normalize_mode(settings.AURORA_REFLECTION_WIRE_MODE)
        raw = await redis_client.get(f"{self.PREFIX}{self.MODE_KEY}")
        if raw is None:
            return self._normalize_mode(settings.AURORA_REFLECTION_WIRE_MODE)
        return self._normalize_mode(raw)

    async def set_mode(self, mode: str) -> str:
        normalized = self._normalize_mode(mode)
        redis_client = cache_service.redis
        if redis_client is not None:
            await redis_client.set(f"{self.PREFIX}{self.MODE_KEY}", normalized)
        else:
            settings.AURORA_REFLECTION_WIRE_MODE = normalized
        return normalized

    async def is_trigger_enabled(self, category: str) -> bool:
        normalized = str(category or "").strip().lower()
        if not normalized:
            return False
        redis_client = cache_service.redis
        redis_key = f"{self.PREFIX}trigger:{normalized}"
        if redis_client is not None:
            raw = await redis_client.get(redis_key)
            if raw is not None:
                return self._normalize_bool(raw)
        return self._default_trigger_enabled(normalized)

    async def set_trigger_enabled(self, category: str, enabled: bool) -> bool:
        normalized = str(category or "").strip().lower()
        if not normalized:
            return False
        redis_client = cache_service.redis
        if redis_client is not None:
            await redis_client.set(f"{self.PREFIX}trigger:{normalized}", "1" if enabled else "0")
        return enabled

    async def get_all(self) -> dict[str, Any]:
        return {
            "reflection_wire_mode": await self.get_mode(),
            "trigger_toggles": {
                category: await self.is_trigger_enabled(category)
                for category in (
                    "too_difficult",
                    "unclear",
                    "abandoned",
                    "intervention_ineffective",
                    "plan_stall",
                    "overload",
                )
            },
        }

    async def record_rule_y_pass_rate(self, pass_rate: float) -> str:
        normalized = max(0.0, min(1.0, float(pass_rate)))
        redis_client = cache_service.redis
        if normalized >= 0.95:
            if redis_client is not None:
                await redis_client.delete(f"{self.PREFIX}{self.RULE_Y_STREAK_KEY}")
            return await self.get_mode()

        if redis_client is None:
            if self._normalize_mode(settings.AURORA_REFLECTION_WIRE_MODE) == "live":
                settings.AURORA_REFLECTION_WIRE_MODE = "shadow"
            return self._normalize_mode(settings.AURORA_REFLECTION_WIRE_MODE)

        streak = await redis_client.incr(f"{self.PREFIX}{self.RULE_Y_STREAK_KEY}")
        await redis_client.expire(f"{self.PREFIX}{self.RULE_Y_STREAK_KEY}", 86400)
        if int(streak) >= 3:
            await redis_client.set(f"{self.PREFIX}{self.MODE_KEY}", "shadow")
            return "shadow"
        return await self.get_mode()

    @classmethod
    def _normalize_mode(cls, value: str | Any) -> str:
        normalized = str(value or "off").strip().lower()
        if normalized not in cls.DEFAULT_MODES:
            return "off"
        return normalized

    @staticmethod
    def _normalize_bool(value: Any) -> bool:
        return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _default_trigger_enabled(category: str) -> bool:
        mapping = {
            "too_difficult": settings.AURORA_REFLECTION_TRIGGER_TOO_DIFFICULT,
            "unclear": settings.AURORA_REFLECTION_TRIGGER_UNCLEAR,
            "abandoned": settings.AURORA_REFLECTION_TRIGGER_ABANDONED,
            "intervention_ineffective": settings.AURORA_REFLECTION_TRIGGER_INTERVENTION_INEFFECTIVE,
            "plan_stall": settings.AURORA_REFLECTION_TRIGGER_PLAN_STALL,
            "overload": settings.AURORA_REFLECTION_TRIGGER_OVERLOAD,
        }
        return bool(mapping.get(category, False))
