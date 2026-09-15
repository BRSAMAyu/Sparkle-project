from __future__ import annotations

from typing import Any

from app.core.cache import cache_service
from app.core.kill_switch import KillSwitchBinding, read_mode, write_mode


class AuroraStage23KillSwitchService:
    PREFIX = "aurora:stage23:killswitch:"
    BINDING = KillSwitchBinding(
        stage="23",
        feature="mode",
        redis_key="bayesian_mode",
        settings_attr="AURORA_BAYESIAN_MODE",
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

    async def get_all(self) -> dict[str, Any]:
        return {
            "bayesian_mode": await self.get_mode(),
            "live_canary_percent": self.live_canary_percent(),
        }

    @staticmethod
    def live_canary_percent() -> int:
        from app.config import settings

        try:
            return max(0, min(100, int(settings.AURORA_BAYESIAN_LIVE_CANARY_PERCENT)))
        except (TypeError, ValueError):
            return 0
