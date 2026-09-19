from __future__ import annotations

import pytest

class _InMemoryKillSwitchRedis:
    """Hermetic stand-in: kill switches use get/set/delete/incr/expire only."""

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


from app.core.cache import cache_service
from app.services.aurora_stage26_scene_kill_switch_service import AuroraStage26SceneKillSwitchService

class _InMemoryKillSwitchRedis:
    """Hermetic stand-in: kill switches use get/set/delete/incr/expire only."""

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
async def test_scene_auto_downgrade_switches_live_to_shadow_after_three_low_scores(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", _InMemoryKillSwitchRedis())
    service = AuroraStage26SceneKillSwitchService()
    await service.reset_quality_streak()
    await service.set_mode("live")
    await service.record_quality_average(0.4)
    await service.record_quality_average(0.5)
    mode = await service.record_quality_average(0.59)

    assert mode == "shadow"


@pytest.mark.asyncio
async def test_scene_auto_downgrade_resets_streak_on_healthy_quality(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", _InMemoryKillSwitchRedis())
    service = AuroraStage26SceneKillSwitchService()
    await service.reset_quality_streak()
    await service.set_mode("live")
    await service.record_quality_average(0.5)
    await service.record_quality_average(0.8)
    mode = await service.record_quality_average(0.5)

    assert mode == "live"


@pytest.mark.asyncio
async def test_scene_auto_downgrade_keeps_shadow_in_shadow(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", _InMemoryKillSwitchRedis())
    service = AuroraStage26SceneKillSwitchService()
    await service.reset_quality_streak()
    await service.set_mode("shadow")
    mode = await service.record_quality_average(0.2)

    assert mode == "shadow"
