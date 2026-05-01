from __future__ import annotations


from app.core.cache import cache_service
from app.core.kill_switch import KillSwitchBinding, read_mode, write_mode


class AuroraStage31IdiographicKillSwitchService:
    PREFIX = "aurora:stage31:idiographic:"
    BINDING = KillSwitchBinding(
        stage="31",
        feature="idiographic",
        redis_key="mode",
        settings_attr="AURORA_IDIOGRAPHIC_MODE",
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

    async def disable(self) -> str:
        return await self.set_mode("off")

    async def auto_downgrade_on_disconfirm_rate(self, ratio: float) -> str | None:
        if float(ratio or 0.0) <= 0.30:
            return None
        if await self.get_mode() != "live":
            return None
        return await self.set_mode("shadow")
