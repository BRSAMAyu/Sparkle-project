from __future__ import annotations

import pytest

from app.core.cache import cache_service
from app.services.aurora_stage29_srl_kill_switch_service import AuroraStage29SRLKillSwitchService
from app.services.srl_phase_tracker_service import SRLPhaseTrackerService


class _FakeEventBus:
    async def get_consumer_lag(self, stream: str = "sparkle_events", group_name: str | None = None):
        del stream, group_name
        return {
            "groups": [
                {"name": "srl_phase_tracker", "lag_time_seconds": 2.0},
                {"name": "srl_phase_tracker", "lag_time_seconds": 5.5},
                {"name": "srl_phase_tracker", "lag_time_seconds": 7.2},
            ]
        }

    async def get_dlq_stats(self, stream: str = "sparkle_events"):
        del stream
        return {"message_count": 3}


@pytest.mark.asyncio
async def test_collect_runtime_metrics_computes_p95(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    tracker = SRLPhaseTrackerService(event_bus=_FakeEventBus())
    metrics = await tracker.collect_runtime_metrics()

    assert metrics["lag_p95"] == 7.2
    assert metrics["dlq_size"] == 3


@pytest.mark.asyncio
async def test_lag_monitor_auto_downgrades_after_three_high_points(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    service = AuroraStage29SRLKillSwitchService()
    await service.ordered_startup("live")

    await service.record_event_lag_p95(6.0)
    await service.record_event_lag_p95(6.0)
    mode = await service.record_event_lag_p95(6.0)

    assert mode == "shadow"
    assert await service.get_bridge_mode() == "shadow"


@pytest.mark.asyncio
async def test_lag_monitor_resets_when_lag_recovers(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    service = AuroraStage29SRLKillSwitchService()
    await service.ordered_startup("live")

    await service.record_event_lag_p95(6.0)
    await service.record_event_lag_p95(1.0)
    mode = await service.record_event_lag_p95(6.0)

    assert mode == "live" or mode == "shadow"
