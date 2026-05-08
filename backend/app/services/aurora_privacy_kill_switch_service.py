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


class AuroraPrivacyKillSwitchService:
    PREFIX = "aurora:privacy:"
    BINDING = KillSwitchBinding(
        stage="privacy",
        feature="pii_redaction",
        redis_key="pii_redaction_mode",
        settings_attr="AURORA_PRIVACY_PII_REDACTION_MODE",
        fallback_mode="live",
    )

    async def get_mode(self) -> str:
        mode = await read_mode(
            redis_client=cache_service.redis,
            prefix=self.PREFIX,
            binding=self.BINDING,
            record_gauge=False,
        )
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


record_mode_gauge(
    AuroraPrivacyKillSwitchService.BINDING.stage,
    AuroraPrivacyKillSwitchService.BINDING.feature,
    resolve_settings_mode(AuroraPrivacyKillSwitchService.BINDING),
)
