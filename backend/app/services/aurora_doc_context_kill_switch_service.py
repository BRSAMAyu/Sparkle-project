from __future__ import annotations

from app.config import settings
from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    is_enabled_mode,
    is_live_mode,
    read_mode,
    record_mode_gauge,
    resolve_settings_mode,
    write_mode,
)


class AuroraDocContextKillSwitchService:
    PREFIX = "aurora:doc_context:"
    BINDING = KillSwitchBinding(
        stage="doc_context",
        feature="document_context_injection",
        redis_key="document_context_injection_mode",
        settings_attr="AURORA_DOC_CONTEXT_DOCUMENT_CONTEXT_INJECTION_MODE",
        fallback_mode="shadow",
    )

    async def get_mode(self) -> str:
        mode = await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.BINDING,
            record_gauge=False,
        )
        if not settings.ENABLE_DOCUMENT_CONTEXT_INJECTION:
            mode = "off"
        record_mode_gauge(self.BINDING.stage, self.BINDING.feature, mode)
        return mode

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

    async def summary(self) -> dict[str, str | int | float | bool]:
        return {
            "mode": await self.get_mode(),
            "enabled": settings.ENABLE_DOCUMENT_CONTEXT_INJECTION,
            "context_ratio": settings.DOCUMENT_CONTEXT_RATIO,
            "max_chunks": settings.DOCUMENT_CONTEXT_MAX_CHUNKS,
            "similarity_threshold": settings.DOCUMENT_CONTEXT_SIMILARITY_THRESHOLD,
            "recency_boost_days": settings.DOCUMENT_CONTEXT_RECENCY_BOOST_DAYS,
        }


record_mode_gauge(
    AuroraDocContextKillSwitchService.BINDING.stage,
    AuroraDocContextKillSwitchService.BINDING.feature,
    "off"
    if not settings.ENABLE_DOCUMENT_CONTEXT_INJECTION
    else resolve_settings_mode(AuroraDocContextKillSwitchService.BINDING),
)
