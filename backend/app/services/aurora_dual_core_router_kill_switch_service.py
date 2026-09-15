from __future__ import annotations

from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    read_mode,
    record_mode_gauge,
    write_mode,
)


class AuroraDualCoreRouterKillSwitchService:
    PREFIX = "aurora:dual_core_router:"
    MASTER_BINDING = KillSwitchBinding(
        stage="dual_core_router",
        feature="mode",
        redis_key="mode",
        settings_attr="AURORA_DUAL_CORE_ROUTER_MODE",
        fallback_mode="live",
    )

    async def get_mode(self) -> str:
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.MASTER_BINDING,
        )

    async def set_mode(self, mode: str) -> str:
        return await write_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.MASTER_BINDING,
            mode=mode,
        )

    async def summary(self) -> dict[str, str]:
        mode = await self.get_mode()
        record_mode_gauge("dual_core_router", "mode", mode)
        return {"mode": mode}
