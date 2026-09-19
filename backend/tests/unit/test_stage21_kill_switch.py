from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.services.aurora_stage21_kill_switch_service import AuroraStage21KillSwitchService


@pytest.mark.asyncio
async def test_stage21_kill_switch_defaults_follow_settings(monkeypatch) -> None:
    monkeypatch.setattr("app.services.aurora_stage21_kill_switch_service.cache_service.redis", None)
    monkeypatch.setattr(settings, "AURORA_STAGE21_SKILL_STORE_MODE", "live", raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE21_SKILL_SELECTION_MODE", "shadow", raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE21_SKILL_SHARE_MODE", "off", raising=False)
    # Legacy bools override fallback-mode attrs; pin them off so mode attrs win.
    monkeypatch.setattr(settings, "SPARKLE_SKILL_STORE_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_SKILL_SELECTION_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_SKILL_SHARE_ENABLED", False, raising=False)

    flags = await AuroraStage21KillSwitchService().get_all()

    assert flags == {
        "skill_store_enabled": "live",
        "skill_selection_enabled": "shadow",
        "skill_share_enabled": "off",
    }


@pytest.mark.asyncio
async def test_stage21_kill_switch_can_flip_flags_without_cross_pollution(monkeypatch) -> None:
    monkeypatch.setattr("app.services.aurora_stage21_kill_switch_service.cache_service.redis", None)
    monkeypatch.setattr(settings, "AURORA_STAGE21_SKILL_STORE_MODE", "live", raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE21_SKILL_SELECTION_MODE", "off", raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE21_SKILL_SHARE_MODE", "off", raising=False)

    monkeypatch.setattr(cache_service, "redis", _InMemoryKillSwitchRedis())
    service = AuroraStage21KillSwitchService()
    updated = await service.set_flags(
        {
            "skill_store_enabled": "shadow",
            "skill_selection_enabled": "live",
            "skill_share_enabled": "shadow",
        }
    )

    assert updated == {
        "skill_store_enabled": "shadow",
        "skill_selection_enabled": "live",
        "skill_share_enabled": "shadow",
    }


@pytest.mark.asyncio
async def test_stage21_kill_switch_reads_redis_override(monkeypatch) -> None:
    fake_redis = AsyncMock()
    fake_redis.get.side_effect = ["shadow", "live", None]
    monkeypatch.setattr(settings, "AURORA_STAGE21_SKILL_SHARE_MODE", "shadow", raising=False)
    monkeypatch.setattr("app.services.aurora_stage21_kill_switch_service.cache_service.redis", fake_redis)

    flags = await AuroraStage21KillSwitchService().get_all()

    assert flags == {
        "skill_store_enabled": "shadow",
        "skill_selection_enabled": "live",
        "skill_share_enabled": "shadow",
    }


class _InMemoryKillSwitchRedis:
    """Hermetic mode store: get/set is all the kill switches need here."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value


