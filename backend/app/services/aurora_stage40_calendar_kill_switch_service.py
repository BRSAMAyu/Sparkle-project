from __future__ import annotations

from app.core.cache import cache_service
from app.core.kill_switch import KillSwitchBinding, is_enabled_mode, is_live_mode, read_mode, write_mode


class AuroraStage40CalendarKillSwitchService:
    PREFIX = "aurora:stage40:calendar:"
    BINDING = KillSwitchBinding(
        stage="40",
        feature="calendar",
        redis_key="mode",
        settings_attr="AURORA_STAGE40_CALENDAR_MODE",
        fallback_mode="live",
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

    async def is_enabled(self) -> bool:
        return is_enabled_mode(await self.get_mode())

    async def is_live(self) -> bool:
        return is_live_mode(await self.get_mode())
