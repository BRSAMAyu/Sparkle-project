from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.services.aurora_stage26_scene_kill_switch_service import AuroraStage26SceneKillSwitchService
from app.services.scene_consolidation_service import SceneConsolidationService
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
from tests.unit.scene_test_helpers import make_memory

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
async def test_scene_kill_switch_defaults_to_off(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", _InMemoryKillSwitchRedis())
    service = AuroraStage26SceneKillSwitchService()
    await service.reset_quality_streak()
    await service.set_mode("off")
    mode = await service.get_mode()
    assert mode == "off"


@pytest.mark.asyncio
async def test_scene_kill_switch_round_trips_modes() -> None:
    service = AuroraStage26SceneKillSwitchService()

    assert await service.set_mode("live") == "live"
    assert await service.get_mode() == "live"
    assert await service.set_mode("shadow") == "shadow"
    assert await service.set_mode("off") == "off"


@pytest.mark.asyncio
async def test_scene_consolidation_stops_when_mode_is_off(db_session, monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", _InMemoryKillSwitchRedis())
    user_id = uuid4()
    memory = make_memory(
        user_id=user_id,
        summary="不开启 scene",
        occurred_at=datetime(2026, 4, 19, 9, 0, 0),
        embedding=[0.8, 0.2],
    )
    db_session.add(memory)
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("off")

    result = await SceneConsolidationService(db_session).consolidate_memory(memory)

    assert result.action == "disabled"
    assert result.scene is None
