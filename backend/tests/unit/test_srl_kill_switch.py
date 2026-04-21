from __future__ import annotations

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.services.aurora_stage29_srl_kill_switch_service import AuroraStage29SRLKillSwitchService


@pytest.mark.asyncio
async def test_main_kill_switch_defaults_to_settings_without_redis(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_SRL_MODE = "shadow"
    service = AuroraStage29SRLKillSwitchService()
    assert await service.get_mode() == "shadow"


@pytest.mark.asyncio
async def test_child_modes_resolve_to_off_when_main_mode_off(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    service = AuroraStage29SRLKillSwitchService()
    await service.set_mode("off")
    await service.set_tracker_mode("live")
    assert await service.get_tracker_mode() == "off"
    assert await service.get_bridge_mode() == "off"


@pytest.mark.asyncio
async def test_ordered_shutdown_turns_children_off_in_sequence(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    service = AuroraStage29SRLKillSwitchService()
    await service.ordered_startup("live")
    summary = await service.ordered_shutdown()
    assert summary["tracker_mode"] == "off"
    assert summary["bridge_mode"] == "off"
    assert summary["scaffolding_consume_mode"] == "off"


@pytest.mark.asyncio
async def test_ordered_startup_sets_all_modes_live(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    service = AuroraStage29SRLKillSwitchService()
    summary = await service.ordered_startup("live")
    assert summary["mode"] == "live"
    assert summary["tracker_mode"] == "live"
    assert summary["bridge_mode"] == "live"
    assert summary["scaffolding_consume_mode"] == "live"
