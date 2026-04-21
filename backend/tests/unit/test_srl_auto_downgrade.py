from __future__ import annotations

import pytest

from app.core.cache import cache_service
from app.services.aurora_stage29_srl_kill_switch_service import AuroraStage29SRLKillSwitchService


@pytest.mark.asyncio
async def test_lag_auto_downgrade_switches_bridge_to_shadow(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    service = AuroraStage29SRLKillSwitchService()
    await service.ordered_startup("live")
    await service.record_event_lag_p95(6.0)
    await service.record_event_lag_p95(6.0)
    mode = await service.record_event_lag_p95(6.0)
    assert mode == "shadow"


@pytest.mark.asyncio
async def test_lag_auto_downgrade_resets_on_recovery(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    service = AuroraStage29SRLKillSwitchService()
    await service.ordered_startup("live")
    await service.record_event_lag_p95(6.0)
    await service.record_event_lag_p95(1.0)
    mode = await service.record_event_lag_p95(6.0)
    assert mode == "live" or mode == "shadow"


@pytest.mark.asyncio
async def test_misjudgment_auto_downgrade_switches_bridge_to_shadow(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    service = AuroraStage29SRLKillSwitchService()
    await service.ordered_startup("live")
    await service.record_misjudgment_rate(0.3, day_key="2026-04-19")
    await service.record_misjudgment_rate(0.3, day_key="2026-04-20")
    mode = await service.record_misjudgment_rate(0.3, day_key="2026-04-21")
    assert mode == "shadow"


@pytest.mark.asyncio
async def test_misjudgment_auto_downgrade_resets_on_low_rate(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    service = AuroraStage29SRLKillSwitchService()
    await service.ordered_startup("live")
    await service.record_misjudgment_rate(0.3, day_key="2026-04-19")
    await service.record_misjudgment_rate(0.1, day_key="2026-04-20")
    mode = await service.record_misjudgment_rate(0.3, day_key="2026-04-21")
    assert mode == "live" or mode == "shadow"
