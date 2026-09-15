from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.services.aurora_stage19_kill_switch_service import AuroraStage19KillSwitchService


@pytest.mark.asyncio
async def test_stage19_kill_switch_defaults_follow_settings(monkeypatch) -> None:
    monkeypatch.setattr("app.services.aurora_stage19_kill_switch_service.cache_service.redis", None)
    monkeypatch.setattr(settings, "AURORA_STAGE19_WORKING_MEMORY_MODE", "shadow", raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE19_LLM_EXTRACTOR_MODE", "live", raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE19_CONSOLIDATION_MODE", "off", raising=False)

    flags = await AuroraStage19KillSwitchService().get_all()

    assert flags == {
        "working_memory_enabled": "shadow",
        "llm_extractor_enabled": "live",
        "consolidation_enabled": "off",
    }


@pytest.mark.asyncio
async def test_stage19_kill_switch_can_flip_flags_without_cross_pollution(monkeypatch) -> None:
    monkeypatch.setattr("app.services.aurora_stage19_kill_switch_service.cache_service.redis", None)
    monkeypatch.setattr(settings, "AURORA_STAGE19_WORKING_MEMORY_MODE", "off", raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE19_LLM_EXTRACTOR_MODE", "off", raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE19_CONSOLIDATION_MODE", "off", raising=False)

    service = AuroraStage19KillSwitchService()
    updated = await service.set_flags(
        {
            "working_memory_enabled": "shadow",
            "llm_extractor_enabled": "off",
            "consolidation_enabled": "live",
        }
    )

    assert updated["working_memory_enabled"] == "shadow"
    assert updated["llm_extractor_enabled"] == "off"
    assert updated["consolidation_enabled"] == "live"


@pytest.mark.asyncio
async def test_stage19_kill_switch_reads_redis_override(monkeypatch) -> None:
    fake_redis = AsyncMock()
    fake_redis.get.side_effect = ["shadow", "live", None]
    monkeypatch.setattr(settings, "AURORA_STAGE19_CONSOLIDATION_MODE", "live", raising=False)
    monkeypatch.setattr("app.services.aurora_stage19_kill_switch_service.cache_service.redis", fake_redis)

    service = AuroraStage19KillSwitchService()
    flags = await service.get_all()

    assert flags == {
        "working_memory_enabled": "shadow",
        "llm_extractor_enabled": "live",
        "consolidation_enabled": "live",
    }
