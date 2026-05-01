from __future__ import annotations


from app.core.cache import cache_service
from app.core.kill_switch import KillSwitchBinding, read_mode, write_mode


class AuroraStage26SceneKillSwitchService:
    PREFIX = "aurora:stage26:scene:"
    QUALITY_STREAK_KEY = "quality_below_threshold_streak"
    BINDING = KillSwitchBinding(
        stage="26",
        feature="scene",
        redis_key="mode",
        settings_attr="AURORA_SCENE_MODE",
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

    async def record_quality_average(self, average_quality: float) -> str:
        from app.config import settings

        normalized_quality = max(0.0, min(1.0, float(average_quality)))
        threshold = float(settings.AURORA_SCENE_QUALITY_THRESHOLD)
        redis_client = cache_service.redis
        if normalized_quality >= threshold:
            if redis_client is not None:
                await redis_client.delete(f"{self.PREFIX}{self.QUALITY_STREAK_KEY}")
            else:
                settings._aurora_scene_quality_streak = 0
            return await self.get_mode()

        if redis_client is None:
            if await self.get_mode() == "live":
                streak = int(getattr(settings, "_aurora_scene_quality_streak", 0)) + 1
                settings._aurora_scene_quality_streak = streak
                if streak >= 3:
                    await self.set_mode("shadow")
            return await self.get_mode()

        streak = await redis_client.incr(f"{self.PREFIX}{self.QUALITY_STREAK_KEY}")
        await redis_client.expire(f"{self.PREFIX}{self.QUALITY_STREAK_KEY}", 86400)
        if int(streak) >= 3 and await self.get_mode() == "live":
            return await self.set_mode("shadow")
        return await self.get_mode()

    async def reset_quality_streak(self) -> None:
        from app.config import settings

        redis_client = cache_service.redis
        if redis_client is not None:
            await redis_client.delete(f"{self.PREFIX}{self.QUALITY_STREAK_KEY}")
        elif hasattr(settings, "_aurora_scene_quality_streak"):
            settings._aurora_scene_quality_streak = 0
