from __future__ import annotations

from typing import Any

from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    is_enabled_mode,
    is_live_mode,
    read_mode,
    write_mode,
)


class AuroraStage19KillSwitchService:
    PREFIX = "aurora:stage19:killswitch:"
    BINDINGS = {
        "working_memory_enabled": KillSwitchBinding(
            stage="19",
            feature="working_memory",
            redis_key="working_memory_mode",
            settings_attr="AURORA_STAGE19_WORKING_MEMORY_MODE",
            legacy_bool_attr="SPARKLE_WORKING_MEMORY_ENABLED",
        ),
        "llm_extractor_enabled": KillSwitchBinding(
            stage="19",
            feature="llm_extractor",
            redis_key="llm_extractor_mode",
            settings_attr="AURORA_STAGE19_LLM_EXTRACTOR_MODE",
            legacy_bool_attr="SPARKLE_LLM_EXTRACTOR_ENABLED",
        ),
        "consolidation_enabled": KillSwitchBinding(
            stage="19",
            feature="consolidation",
            redis_key="consolidation_mode",
            settings_attr="AURORA_STAGE19_CONSOLIDATION_MODE",
            legacy_bool_attr="SPARKLE_CONSOLIDATION_ENABLED",
        ),
        # Memory V3 (M-02): episodic 写路径 storage gate（off=bypass 全写、
        # shadow=只观测不拦截、live=执行五分类）。语义层另有独立 settings 开关。
        "storage_gate_enabled": KillSwitchBinding(
            stage="19",
            feature="storage_gate",
            redis_key="storage_gate_mode",
            settings_attr="AURORA_STAGE19_STORAGE_GATE_MODE",
            legacy_bool_attr=None,
        ),
    }

    async def get_feature_mode(self, key: str) -> str:
        return await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.BINDINGS[key],
        )

    async def is_enabled(self, key: str) -> bool:
        return is_enabled_mode(await self.get_feature_mode(key))

    async def is_live(self, key: str) -> bool:
        return is_live_mode(await self.get_feature_mode(key))

    async def get_all(self) -> dict[str, str]:
        return {key: await self.get_feature_mode(key) for key in self.BINDINGS}

    async def set_flags(self, updates: dict[str, Any]) -> dict[str, str]:
        for key, value in updates.items():
            if key in self.BINDINGS and value is not None:
                await write_mode(
                    redis_client=cache_service.redis,
                    prefix=self.PREFIX,
                    binding=self.BINDINGS[key],
                    mode=value,
                )
        return await self.get_all()
