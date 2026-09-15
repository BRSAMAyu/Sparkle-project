from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.services.aurora_stage33_kill_switch_service import AuroraStage33KillSwitchService


@pytest.mark.asyncio
async def test_stage33_master_off_short_circuits_subfeatures(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "off"
    settings.AURORA_STAGE33_SRL_MODE = "live"
    settings.AURORA_STAGE33_WM_PROMPT_MODE = "live"
    settings.AURORA_STAGE33_EVENTS_MODE = "live"

    service = AuroraStage33KillSwitchService()
    assert await service.get_mode() == "off"
    assert await service.get_feature_mode("srl") == "off"
    assert await service.get_feature_mode("wm_prompt") == "off"
    assert await service.get_feature_mode("events") == "off"


@pytest.mark.asyncio
async def test_stage33_srl_mode_follows_settings(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "live"
    settings.AURORA_STAGE33_SRL_MODE = "shadow"

    service = AuroraStage33KillSwitchService()
    assert await service.get_feature_mode("srl") == "shadow"


@pytest.mark.asyncio
async def test_stage33_wm_prompt_mode_follows_settings(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "live"
    settings.AURORA_STAGE33_WM_PROMPT_MODE = "live"

    service = AuroraStage33KillSwitchService()
    assert await service.get_feature_mode("wm_prompt") == "live"


@pytest.mark.asyncio
async def test_stage33_events_mode_follows_settings(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "live"
    settings.AURORA_STAGE33_EVENTS_MODE = "shadow"

    service = AuroraStage33KillSwitchService()
    assert await service.get_feature_mode("events") == "shadow"


@pytest.mark.asyncio
async def test_stage33_redis_override_takes_precedence(monkeypatch) -> None:
    settings.AURORA_STAGE33_MODE = "off"
    settings.AURORA_STAGE33_SRL_MODE = "off"
    settings.AURORA_STAGE33_WM_PROMPT_MODE = "off"
    settings.AURORA_STAGE33_EVENTS_MODE = "off"
    settings.AURORA_STAGE33_COMMUNITY_MODE = "live"

    fake_redis = AsyncMock()

    async def _fake_get(key: str) -> str | None:
        mapping = {
            "aurora_stage33:mode": "live",
            "aurora_stage33:srl_mode": "shadow",
            "aurora_stage33:wm_prompt_mode": "live",
            "aurora_stage33:events_mode": "shadow",
            "aurora_stage33:social_mode": "live",
        }
        return mapping.get(key)

    fake_redis.get.side_effect = _fake_get
    monkeypatch.setattr(cache_service, "redis", fake_redis)

    service = AuroraStage33KillSwitchService()
    summary = await service.summary()

    assert summary == {
        "mode": "live",
        "social": "live",
        "srl": "shadow",
        "wm_prompt": "live",
        "events": "shadow",
        "community": "live",
    }


@pytest.mark.asyncio
async def test_stage33_master_shadow_allows_independent_subfeatures(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "shadow"
    settings.AURORA_STAGE33_SRL_MODE = "live"
    settings.AURORA_STAGE33_WM_PROMPT_MODE = "shadow"
    settings.AURORA_STAGE33_EVENTS_MODE = "live"

    service = AuroraStage33KillSwitchService()
    assert await service.get_mode() == "shadow"
    assert await service.get_feature_mode("srl") == "live"
    assert await service.get_feature_mode("wm_prompt") == "shadow"
    assert await service.get_feature_mode("events") == "live"


@pytest.mark.asyncio
async def test_stage33_summary_returns_all_keys(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE33_MODE = "shadow"
    settings.AURORA_STAGE33_SOCIAL_MODE = "live"
    settings.AURORA_STAGE33_SRL_MODE = "shadow"
    settings.AURORA_STAGE33_WM_PROMPT_MODE = "shadow"
    settings.AURORA_STAGE33_EVENTS_MODE = "shadow"
    settings.AURORA_STAGE33_COMMUNITY_MODE = "live"

    summary = await AuroraStage33KillSwitchService().summary()
    assert set(summary.keys()) == {"mode", "social", "srl", "wm_prompt", "events", "community"}
