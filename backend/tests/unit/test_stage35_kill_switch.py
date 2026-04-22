from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.services.aurora_stage35_kill_switch_service import AuroraStage35KillSwitchService


@pytest.mark.asyncio
async def test_stage35_kill_switch_defaults_follow_settings(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE35_MODE = "shadow"
    settings.AURORA_STAGE35_METACOG_ROUTER_MODE = "live"

    summary = await AuroraStage35KillSwitchService().summary()

    assert summary == {
        "mode": "shadow",
        "metacog_router_mode": "live",
    }


@pytest.mark.asyncio
async def test_stage35_kill_switch_reads_redis_override(monkeypatch) -> None:
    fake_redis = AsyncMock()

    async def _fake_get(key: str) -> str | None:
        mapping = {
            "aurora_stage35:mode": "live",
            "aurora_stage35:metacog_router_mode": "shadow",
        }
        return mapping.get(key)

    fake_redis.get.side_effect = _fake_get
    monkeypatch.setattr(cache_service, "redis", fake_redis)

    summary = await AuroraStage35KillSwitchService().summary()

    assert summary == {
        "mode": "live",
        "metacog_router_mode": "shadow",
    }
