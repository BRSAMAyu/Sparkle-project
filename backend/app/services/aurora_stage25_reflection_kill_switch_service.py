from __future__ import annotations

from typing import Any

from app.config import settings
from app.core.cache import cache_service
from app.core.kill_switch import KillSwitchBinding, read_mode, write_mode


class AuroraStage25ReflectionKillSwitchService:
    PREFIX = "aurora:stage25:killswitch:"
    RULE_Y_STREAK_KEY = "rule_y_breach_streak"
    BINDING = KillSwitchBinding(
        stage="25",
        feature="reflection_wire",
        redis_key="reflection_wire_mode",
        settings_attr="AURORA_REFLECTION_WIRE_MODE",
    )

    async def get_mode(self) -> str:
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.BINDING,
        )

    async def set_mode(self, mode: str) -> str:
        return await write_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.BINDING,
            mode=mode,
        )

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
            if await self.get_mode() == "live":
                await self.set_mode("shadow")
            return await self.get_mode()

        streak = await redis_client.incr(f"{self.PREFIX}{self.RULE_Y_STREAK_KEY}")
        await redis_client.expire(f"{self.PREFIX}{self.RULE_Y_STREAK_KEY}", 86400)
        if int(streak) >= 3:
            return await self.set_mode("shadow")
        return await self.get_mode()

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
