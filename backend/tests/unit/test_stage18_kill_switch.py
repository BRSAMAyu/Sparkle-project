from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.services.aurora_stage18_kill_switch_service import AuroraStage18KillSwitchService


@pytest.mark.asyncio
async def test_stage18_kill_switch_defaults_follow_settings(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_STAGE18_AGGREGATOR_MODE", "shadow", raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE18_PUSH_POLICY_MODE", "live", raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE18_PUSH_DELIVERY_MODE", "off", raising=False)
    # Legacy bools override an explicit fallback-mode setting; pin them off so
    # the mode attrs are authoritative here.
    monkeypatch.setattr(settings, "SPARKLE_AGGREGATOR_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_PUSH_POLICY_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_PUSH_DELIVERY_ENABLED", False, raising=False)

    service = AuroraStage18KillSwitchService()
    flags = await service.get_all()

    assert flags == {
        "aggregator_enabled": "shadow",
        "push_policy_enabled": "live",
        "push_delivery_enabled": "off",
    }


@pytest.mark.asyncio
async def test_stage18_kill_switch_can_flip_flags_without_cross_pollution(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_STAGE18_AGGREGATOR_MODE", "off", raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE18_PUSH_POLICY_MODE", "off", raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE18_PUSH_DELIVERY_MODE", "off", raising=False)
    monkeypatch.setattr(
        "app.services.aurora_stage18_kill_switch_service.cache_service.redis",
        _InMemoryKillSwitchRedis(),
    )

    service = AuroraStage18KillSwitchService()
    updated = await service.set_flags(
        {
            "aggregator_enabled": "shadow",
            "push_policy_enabled": "off",
            "push_delivery_enabled": "live",
        }
    )

    assert updated["aggregator_enabled"] == "shadow"
    assert updated["push_policy_enabled"] == "off"
    assert updated["push_delivery_enabled"] == "live"


@pytest.mark.asyncio
async def test_stage18_kill_switch_reads_redis_override(monkeypatch) -> None:
    fake_redis = AsyncMock()
    fake_redis.get.side_effect = ["shadow", "live", None]
    monkeypatch.setattr(settings, "AURORA_STAGE18_PUSH_DELIVERY_MODE", "live", raising=False)
    monkeypatch.setattr("app.services.aurora_stage18_kill_switch_service.cache_service.redis", fake_redis)

    service = AuroraStage18KillSwitchService()
    flags = await service.get_all()

    assert flags == {
        "aggregator_enabled": "shadow",
        "push_policy_enabled": "live",
        "push_delivery_enabled": "live",
    }


class _InMemoryKillSwitchRedis:
    """Kill switch round-trips only need get/set; writes to real Redis would be
    pointless here and None would make flips unobservable."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value

