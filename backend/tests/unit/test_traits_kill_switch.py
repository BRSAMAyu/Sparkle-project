from __future__ import annotations

import pytest

from app.config import settings
from app.services.aurora_stage28_traits_kill_switch_service import AuroraStage28TraitsKillSwitchService


@pytest.mark.asyncio
async def test_main_kill_switch_defaults_to_settings_when_no_redis() -> None:
    settings.AURORA_TRAITS_MODE = "shadow"
    service = AuroraStage28TraitsKillSwitchService()
    assert await service.get_mode() == "shadow"


@pytest.mark.asyncio
async def test_main_kill_switch_can_be_set_without_redis() -> None:
    service = AuroraStage28TraitsKillSwitchService()
    assert await service.set_mode("live") == "live"
    assert await service.get_mode() == "live"


@pytest.mark.asyncio
async def test_child_modes_turn_off_when_main_mode_off() -> None:
    service = AuroraStage28TraitsKillSwitchService()
    await service.set_mode("off")
    await service.set_nlp_mode("live")
    await service.set_coldstart_mode("live")
    assert await service.get_nlp_mode() == "off"
    assert await service.get_coldstart_mode() == "off"


@pytest.mark.asyncio
async def test_child_modes_can_be_managed_independently() -> None:
    service = AuroraStage28TraitsKillSwitchService()
    await service.set_mode("live")
    assert await service.set_nlp_mode("shadow") == "shadow"
    assert await service.set_coldstart_mode("live") == "live"
