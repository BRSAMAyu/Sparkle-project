from __future__ import annotations

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.services.aurora_stage28_traits_kill_switch_service import AuroraStage28TraitsKillSwitchService

class _InMemoryKillSwitchRedis:
    """Hermetic mode store: get/set is all the kill switches need here."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def incr(self, key: str) -> int:
        self._store[key] = str(int(self._store.get(key, "0")) + 1)
        return int(self._store[key])

    async def expire(self, key: str, ttl: int) -> None:
        pass




@pytest.mark.asyncio
async def test_bias_auto_downgrade_turns_off_nlp_after_three_failures(monkeypatch) -> None:
    settings.AURORA_TRAITS_NLP_BIAS_THRESHOLD = 0.10
    monkeypatch.setattr(cache_service, "redis", _InMemoryKillSwitchRedis())
    service = AuroraStage28TraitsKillSwitchService()
    await service.set_mode("live")
    await service.set_nlp_mode("live")

    await service.record_bias_rate(0.2)
    await service.record_bias_rate(0.2)
    mode = await service.record_bias_rate(0.2)

    assert mode == "off"


@pytest.mark.asyncio
async def test_bias_auto_downgrade_resets_streak_when_bias_recovers() -> None:
    settings.AURORA_TRAITS_NLP_BIAS_THRESHOLD = 0.10
    service = AuroraStage28TraitsKillSwitchService()
    await service.set_mode("live")
    await service.set_nlp_mode("live")

    await service.record_bias_rate(0.2)
    await service.record_bias_rate(0.01)
    mode = await service.record_bias_rate(0.2)

    assert mode == "live"


@pytest.mark.asyncio
async def test_bias_auto_downgrade_keeps_off_mode_stable(monkeypatch) -> None:
    settings.AURORA_TRAITS_NLP_BIAS_THRESHOLD = 0.10
    monkeypatch.setattr(cache_service, "redis", _InMemoryKillSwitchRedis())
    service = AuroraStage28TraitsKillSwitchService()
    await service.set_mode("live")
    await service.set_nlp_mode("off")

    mode = await service.record_bias_rate(0.2)

    assert mode == "off"
