from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.services.aurora_stage18_kill_switch_service import AuroraStage18KillSwitchService


@pytest.mark.asyncio
async def test_stage18_kill_switch_defaults_follow_settings(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SPARKLE_AGGREGATOR_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_PUSH_POLICY_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_PUSH_DELIVERY_ENABLED", False, raising=False)

    service = AuroraStage18KillSwitchService()
    flags = await service.get_all()

    assert flags == {
        "aggregator_enabled": False,
        "push_policy_enabled": True,
        "push_delivery_enabled": False,
    }


@pytest.mark.asyncio
async def test_stage18_kill_switch_can_flip_flags_without_cross_pollution(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SPARKLE_AGGREGATOR_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_PUSH_POLICY_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_PUSH_DELIVERY_ENABLED", False, raising=False)

    service = AuroraStage18KillSwitchService()
    updated = await service.set_flags(
        {
            "aggregator_enabled": True,
            "push_policy_enabled": False,
            "push_delivery_enabled": True,
        }
    )

    assert updated["aggregator_enabled"] is True
    assert updated["push_policy_enabled"] is False
    assert updated["push_delivery_enabled"] is True


@pytest.mark.asyncio
async def test_stage18_kill_switch_reads_redis_override(monkeypatch) -> None:
    fake_redis = AsyncMock()
    fake_redis.get.side_effect = ["false", "true", None]
    monkeypatch.setattr(settings, "SPARKLE_PUSH_DELIVERY_ENABLED", True, raising=False)
    monkeypatch.setattr("app.services.aurora_stage18_kill_switch_service.cache_service.redis", fake_redis)

    service = AuroraStage18KillSwitchService()
    flags = await service.get_all()

    assert flags == {
        "aggregator_enabled": False,
        "push_policy_enabled": True,
        "push_delivery_enabled": True,
    }
