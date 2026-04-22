from __future__ import annotations

import pytest

from app.services.aurora_stage23_kill_switch_service import AuroraStage23KillSwitchService


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def get(self, key: str):
        return self.data.get(key)

    async def set(self, key: str, value: str):
        self.data[key] = value
        return True


@pytest.mark.asyncio
async def test_bayesian_kill_switch_defaults_to_env(monkeypatch) -> None:
    monkeypatch.setattr("app.services.aurora_stage23_kill_switch_service.cache_service.redis", None)
    monkeypatch.setattr("app.core.kill_switch.settings.AURORA_BAYESIAN_MODE", "shadow")

    service = AuroraStage23KillSwitchService()
    assert await service.get_mode() == "shadow"


@pytest.mark.asyncio
async def test_bayesian_kill_switch_persists_mode_in_redis(monkeypatch) -> None:
    redis = FakeRedis()
    monkeypatch.setattr("app.services.aurora_stage23_kill_switch_service.cache_service.redis", redis)

    service = AuroraStage23KillSwitchService()
    await service.set_mode("live")

    assert await service.get_mode() == "live"


@pytest.mark.asyncio
async def test_bayesian_kill_switch_clamps_invalid_mode(monkeypatch) -> None:
    monkeypatch.setattr("app.services.aurora_stage23_kill_switch_service.cache_service.redis", None)
    monkeypatch.setattr("app.core.kill_switch.settings.AURORA_BAYESIAN_MODE", "not-real")

    service = AuroraStage23KillSwitchService()
    assert await service.get_mode() == "off"
