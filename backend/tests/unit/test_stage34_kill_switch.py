from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.services.aurora_stage34_kill_switch_service import AuroraStage34KillSwitchService


@pytest.mark.asyncio
async def test_stage34_kill_switch_defaults_follow_settings(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE34_MODE = "shadow"
    settings.AURORA_STAGE34_ERROR_BRIDGE_MODE = "live"
    settings.AURORA_STAGE34_CAPSULE_MODE = "shadow"
    settings.AURORA_STAGE34_JOURNEY_SUBSCRIBERS_MODE = "live"

    summary = await AuroraStage34KillSwitchService().summary()

    assert summary == {
        "mode": "shadow",
        "error_bridge_mode": "live",
        "capsule_mode": "shadow",
        "journey_subscribers_enabled": "live",
    }


@pytest.mark.asyncio
async def test_stage34_kill_switch_reads_redis_override(monkeypatch) -> None:
    fake_redis = AsyncMock()

    async def _fake_get(key: str) -> str | None:
        mapping = {
            "aurora_stage34:mode": "live",
            "aurora_stage34:error_bridge_mode": "shadow",
            "aurora_stage34:capsule_mode": "live",
            "aurora_stage34:journey_subscribers_enabled": "shadow",
        }
        return mapping.get(key)

    fake_redis.get.side_effect = _fake_get
    monkeypatch.setattr(cache_service, "redis", fake_redis)

    summary = await AuroraStage34KillSwitchService().summary()

    assert summary == {
        "mode": "live",
        "error_bridge_mode": "shadow",
        "capsule_mode": "live",
        "journey_subscribers_enabled": "shadow",
    }
