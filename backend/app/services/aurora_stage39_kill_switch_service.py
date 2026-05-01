from __future__ import annotations


from app.core.cache import cache_service
from app.core.kill_switch import (
    KillSwitchBinding,
    read_mode,
    record_mode_gauge,
    write_mode,
)

_BINDING_MASTER = KillSwitchBinding(
    stage="39",
    feature="mode",
    redis_key="aurora:stage39:mode",
    settings_attr="AURORA_STAGE39_MODE",
    fallback_mode="live",
)

_FEATURE_BINDINGS: dict[str, KillSwitchBinding] = {
    "scaffolding_prompt": KillSwitchBinding(
        stage="39",
        feature="scaffolding_prompt_mode",
        redis_key="aurora:stage39:scaffolding_prompt_mode",
        settings_attr="AURORA_STAGE39_SCAFFOLDING_PROMPT_MODE",
        fallback_mode="live",
    ),
    "cogload_route": KillSwitchBinding(
        stage="39",
        feature="cogload_route_mode",
        redis_key="aurora:stage39:cogload_route_mode",
        settings_attr="AURORA_STAGE39_COGLOAD_ROUTE_MODE",
        fallback_mode="live",
    ),
    "galaxy_inject": KillSwitchBinding(
        stage="39",
        feature="galaxy_inject_mode",
        redis_key="aurora:stage39:galaxy_inject_mode",
        settings_attr="AURORA_STAGE39_GALAXY_INJECT_MODE",
        fallback_mode="live",
    ),
}


def _normalize_feature(feature: str) -> str:
    normalized = str(feature or "").strip().lower()
    if normalized not in _FEATURE_BINDINGS:
        raise ValueError(f"Unknown Stage39 feature: {feature}")
    return normalized


class AuroraStage39KillSwitchService:

    async def get_mode(self) -> str:
        redis_client = cache_service.redis
        return await read_mode(
            redis_client=redis_client, prefix="sparkle:", binding=_BINDING_MASTER,
        )

    async def set_mode(self, mode: str) -> str:
        redis_client = cache_service.redis
        return await write_mode(
            redis_client=redis_client, prefix="sparkle:", binding=_BINDING_MASTER, mode=mode,
        )

    async def get_feature_mode(self, feature: str) -> str:
        feature_key = _normalize_feature(feature)
        master_mode = await self.get_mode()
        if master_mode == "off":
            record_mode_gauge(_FEATURE_BINDINGS[feature_key].stage, _FEATURE_BINDINGS[feature_key].feature, "off")
            return "off"

        redis_client = cache_service.redis
        return await read_mode(
            redis_client=redis_client, prefix="sparkle:", binding=_FEATURE_BINDINGS[feature_key],
        )

    async def set_feature_mode(self, feature: str, mode: str) -> str:
        feature_key = _normalize_feature(feature)
        redis_client = cache_service.redis
        return await write_mode(
            redis_client=redis_client, prefix="sparkle:", binding=_FEATURE_BINDINGS[feature_key], mode=mode,
        )

    async def summary(self) -> dict[str, str]:
        return {
            "mode": await self.get_mode(),
            "scaffolding_prompt_mode": await self.get_feature_mode("scaffolding_prompt"),
            "cogload_route_mode": await self.get_feature_mode("cogload_route"),
            "galaxy_inject_mode": await self.get_feature_mode("galaxy_inject"),
        }
