from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.cache import cache_service
from app.services.aurora_stage31_idiographic_kill_switch_service import (
    AuroraStage31IdiographicKillSwitchService,
)
from app.services.idiographic_association_service import IdiographicAssociationService


@pytest.mark.asyncio
async def test_kill_switch_auto_downgrades_live_mode_on_high_disconfirm_rate() -> None:
    service = AuroraStage31IdiographicKillSwitchService()
    original_mode = await service.get_mode()

    try:
        await service.set_mode("live")
        downgraded = await service.auto_downgrade_on_disconfirm_rate(0.31)

        assert downgraded == "shadow"
        assert await service.get_mode() == "shadow"
    finally:
        await service.set_mode(original_mode)


@pytest.mark.asyncio
async def test_idiographic_shadow_computes_without_db_writes_or_events(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    kill_switch = AuroraStage31IdiographicKillSwitchService()
    original_mode = await kill_switch.get_mode()
    await kill_switch.set_mode("shadow")

    user_id = uuid4()
    event_bus = AsyncMock()
    service = IdiographicAssociationService(event_bus=event_bus)
    daily_vectors = {
        date(2026, 4, 20): {
            "dims": {
                "study_pace": 0.4,
                "completion_rate": 0.6,
                "engagement_level": 0.7,
            },
            "active_event_count": 2,
            "stage30_dim_count": 0,
            "silent_window_cut": False,
        }
    }
    upsert_daily = AsyncMock()
    upsert_changepoints = AsyncMock()
    upsert_associations = AsyncMock()
    write_cache = AsyncMock()

    monkeypatch.setattr(service, "_build_daily_vectors", AsyncMock(return_value=daily_vectors))
    monkeypatch.setattr(service, "_upsert_daily_vectors", upsert_daily)
    monkeypatch.setattr(service, "_upsert_changepoints", upsert_changepoints)
    monkeypatch.setattr(service, "_upsert_associations", upsert_associations)
    monkeypatch.setattr(service, "_load_disconfirmed_pairs", AsyncMock(return_value={}))
    monkeypatch.setattr(service, "_write_summary_cache", write_cache)

    try:
        result = await service.recompute_user(user_id, publish_event=True)
    finally:
        await kill_switch.set_mode(original_mode)

    assert result["mode"] == "shadow"
    assert result["active_days"] == 1
    upsert_daily.assert_not_awaited()
    upsert_changepoints.assert_not_awaited()
    upsert_associations.assert_not_awaited()
    write_cache.assert_not_awaited()
    event_bus.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_idiographic_shadow_does_not_expose_aggregator_summary(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    kill_switch = AuroraStage31IdiographicKillSwitchService()
    original_mode = await kill_switch.get_mode()
    await kill_switch.set_mode("shadow")
    service = IdiographicAssociationService()
    read_cache = AsyncMock()
    monkeypatch.setattr(service, "_read_summary_cache", read_cache)

    try:
        summary = await service.build_aggregator_summary(uuid4())
    finally:
        await kill_switch.set_mode(original_mode)

    assert summary is None
    read_cache.assert_not_awaited()
