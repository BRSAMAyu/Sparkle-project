from __future__ import annotations


from app.config import settings
from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    read_mode,
    record_mode_gauge,
    write_mode,
)


class AuroraStage28TraitsKillSwitchService:
    PREFIX = "aurora:stage28:traits:"
    BIAS_STREAK_KEY = "bias_above_threshold_streak"
    MASTER_BINDING = KillSwitchBinding(
        stage="28",
        feature="mode",
        redis_key="mode",
        settings_attr="AURORA_TRAITS_MODE",
    )
    NLP_BINDING = KillSwitchBinding(
        stage="28",
        feature="nlp",
        redis_key="nlp_mode",
        settings_attr="AURORA_TRAITS_NLP_MODE",
    )
    COLDSTART_BINDING = KillSwitchBinding(
        stage="28",
        feature="coldstart",
        redis_key="coldstart_mode",
        settings_attr="AURORA_TRAITS_COLDSTART_MODE",
    )

    async def get_mode(self) -> str:
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.MASTER_BINDING,
        )

    async def get_nlp_mode(self) -> str:
        if await self.get_mode() == "off":
            record_mode_gauge("28", "nlp", "off")
            return "off"
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.NLP_BINDING,
        )

    async def get_coldstart_mode(self) -> str:
        if await self.get_mode() == "off":
            record_mode_gauge("28", "coldstart", "off")
            return "off"
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.COLDSTART_BINDING,
        )

    async def set_mode(self, mode: str) -> str:
        return await write_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.MASTER_BINDING,
            mode=mode,
        )

    async def set_nlp_mode(self, mode: str) -> str:
        normalized = await write_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.NLP_BINDING,
            mode=mode,
        )
        if normalized != "off":
            await self.reset_bias_streak()
        return normalized

    async def set_coldstart_mode(self, mode: str) -> str:
        return await write_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.COLDSTART_BINDING,
            mode=mode,
        )

    async def record_bias_rate(self, bias_rate: float) -> str:
        normalized = max(0.0, min(1.0, float(bias_rate)))
        threshold = float(settings.AURORA_TRAITS_NLP_BIAS_THRESHOLD)
        redis_client = cache_service.redis
        if normalized <= threshold:
            await self.reset_bias_streak()
            return await self.get_nlp_mode()

        if redis_client is None:
            streak = int(getattr(settings, "_aurora_traits_bias_streak", 0)) + 1
            settings._aurora_traits_bias_streak = streak
            if streak >= 3 and await self.get_nlp_mode() != "off":
                await self.set_nlp_mode("off")
            return await self.get_nlp_mode()

        streak = await redis_client.incr(f"{self.PREFIX}{self.BIAS_STREAK_KEY}")
        await redis_client.expire(f"{self.PREFIX}{self.BIAS_STREAK_KEY}", 86400 * 7)
        if int(streak) >= 3 and await self.get_nlp_mode() != "off":
            return await self.set_nlp_mode("off")
        return await self.get_nlp_mode()

    async def reset_bias_streak(self) -> None:
        redis_client = cache_service.redis
        if redis_client is not None:
            await redis_client.delete(f"{self.PREFIX}{self.BIAS_STREAK_KEY}")
            return
        settings._aurora_traits_bias_streak = 0
