from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.services.aurora_stage21_kill_switch_service import AuroraStage21KillSwitchService


@pytest.mark.asyncio
async def test_stage21_kill_switch_defaults_follow_settings(monkeypatch) -> None:
    monkeypatch.setattr("app.services.aurora_stage21_kill_switch_service.cache_service.redis", None)
    monkeypatch.setattr(settings, "SPARKLE_SKILL_STORE_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_SKILL_SELECTION_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_SKILL_SHARE_ENABLED", False, raising=False)

    flags = await AuroraStage21KillSwitchService().get_all()

    assert flags == {
        "skill_store_enabled": True,
        "skill_selection_enabled": False,
        "skill_share_enabled": False,
    }


@pytest.mark.asyncio
async def test_stage21_kill_switch_can_flip_flags_without_cross_pollution(monkeypatch) -> None:
    monkeypatch.setattr("app.services.aurora_stage21_kill_switch_service.cache_service.redis", None)
    monkeypatch.setattr(settings, "SPARKLE_SKILL_STORE_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_SKILL_SELECTION_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_SKILL_SHARE_ENABLED", False, raising=False)

    service = AuroraStage21KillSwitchService()
    updated = await service.set_flags(
        {
            "skill_store_enabled": False,
            "skill_selection_enabled": True,
            "skill_share_enabled": True,
        }
    )

    assert updated == {
        "skill_store_enabled": False,
        "skill_selection_enabled": True,
        "skill_share_enabled": True,
    }


@pytest.mark.asyncio
async def test_stage21_kill_switch_reads_redis_override(monkeypatch) -> None:
    fake_redis = AsyncMock()
    fake_redis.get.side_effect = ["false", "true", None]
    monkeypatch.setattr(settings, "SPARKLE_SKILL_SHARE_ENABLED", True, raising=False)
    monkeypatch.setattr("app.services.aurora_stage21_kill_switch_service.cache_service.redis", fake_redis)

    flags = await AuroraStage21KillSwitchService().get_all()

    assert flags == {
        "skill_store_enabled": False,
        "skill_selection_enabled": True,
        "skill_share_enabled": True,
    }
