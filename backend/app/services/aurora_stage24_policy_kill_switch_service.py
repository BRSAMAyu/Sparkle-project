from __future__ import annotations

from typing import Any

from app.core.cache import cache_service
from app.core.kill_switch import KillSwitchBinding, read_mode, write_mode


class AuroraStage24PolicyKillSwitchService:
    PREFIX = "aurora:stage24:killswitch:"
    BINDING = KillSwitchBinding(
        stage="24",
        feature="policy_compiler",
        redis_key="policy_compiler_mode",
        settings_attr="AURORA_POLICY_COMPILER_MODE",
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
            "policy_compiler_mode": await self.get_mode(),
        }
