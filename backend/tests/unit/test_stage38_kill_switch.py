from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.services.aurora_stage38_kill_switch_service import AuroraStage38KillSwitchService


@pytest.mark.asyncio
async def test_stage38_err_replan_defaults_to_settings(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE38_ERR_REPLAN_MODE = "shadow"

    service = AuroraStage38KillSwitchService()
    assert await service.get_feature_mode("err_replan") == "shadow"


@pytest.mark.asyncio
async def test_stage38_push_scheduler_defaults_to_settings(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE38_PUSH_SCHEDULER_MODE = "live"

    service = AuroraStage38KillSwitchService()
    assert await service.get_feature_mode("push_scheduler") == "live"


@pytest.mark.asyncio
async def test_stage38_redis_override_both_features(monkeypatch) -> None:
    settings.AURORA_STAGE38_ERR_REPLAN_MODE = "off"
    settings.AURORA_STAGE38_PUSH_SCHEDULER_MODE = "off"

    fake_redis = AsyncMock()

    async def _fake_get(key: str) -> str | None:
        mapping = {
            "aurora_stage38:err_replan_mode": "live",
            "aurora_stage38:push_scheduler_mode": "shadow",
        }
        return mapping.get(key)

    fake_redis.get.side_effect = _fake_get
    monkeypatch.setattr(cache_service, "redis", fake_redis)

    summary = await AuroraStage38KillSwitchService().summary()
    assert summary == {
        "err_replan_mode": "live",
        "push_scheduler_mode": "shadow",
    }


@pytest.mark.asyncio
async def test_stage38_summary_returns_both_features(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_STAGE38_ERR_REPLAN_MODE = "shadow"
    settings.AURORA_STAGE38_PUSH_SCHEDULER_MODE = "shadow"

    summary = await AuroraStage38KillSwitchService().summary()
    assert set(summary.keys()) == {"err_replan_mode", "push_scheduler_mode"}


@pytest.mark.asyncio
async def test_stage38_invalid_mode_falls_back_to_shadow(monkeypatch) -> None:
    settings.AURORA_STAGE38_ERR_REPLAN_MODE = "invalid_value"

    fake_redis = AsyncMock()
    fake_redis.get.return_value = None
    monkeypatch.setattr(cache_service, "redis", fake_redis)

    service = AuroraStage38KillSwitchService()
    assert await service.get_feature_mode("err_replan") == "shadow"
