from __future__ import annotations

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.services.aurora_stage39_kill_switch_service import AuroraStage39KillSwitchService


@pytest.mark.asyncio
async def test_stage39_kill_switch_defaults_to_settings_without_redis(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    monkeypatch.setattr(settings, "AURORA_STAGE39_MODE", "live")
    monkeypatch.setattr(settings, "AURORA_STAGE39_SCAFFOLDING_PROMPT_MODE", "live")
    monkeypatch.setattr(settings, "AURORA_STAGE39_COGLOAD_ROUTE_MODE", "shadow")
    monkeypatch.setattr(settings, "AURORA_STAGE39_GALAXY_INJECT_MODE", "shadow")

    service = AuroraStage39KillSwitchService()
    assert await service.summary() == {
        "mode": "live",
        "scaffolding_prompt_mode": "live",
        "cogload_route_mode": "shadow",
        "galaxy_inject_mode": "shadow",
    }


@pytest.mark.asyncio
async def test_stage39_child_modes_resolve_to_off_when_master_mode_off(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    service = AuroraStage39KillSwitchService()
    await service.set_mode("off")
    await service.set_feature_mode("scaffolding_prompt", "live")
    assert await service.get_feature_mode("scaffolding_prompt") == "off"
