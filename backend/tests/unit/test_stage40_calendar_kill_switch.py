from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.orchestration.prompts import format_user_context
from app.services.aurora_stage40_calendar_kill_switch_service import AuroraStage40CalendarKillSwitchService


@pytest.mark.asyncio
async def test_stage40_calendar_kill_switch_defaults_follow_settings(monkeypatch) -> None:
    monkeypatch.setattr("app.services.aurora_stage40_calendar_kill_switch_service.cache_service.redis", None)
    monkeypatch.setattr(settings, "AURORA_STAGE40_CALENDAR_MODE", "shadow", raising=False)

    assert await AuroraStage40CalendarKillSwitchService().get_mode() == "shadow"


@pytest.mark.asyncio
async def test_stage40_calendar_kill_switch_reads_redis_override(monkeypatch) -> None:
    fake_redis = AsyncMock()
    fake_redis.get.return_value = "off"
    monkeypatch.setattr("app.services.aurora_stage40_calendar_kill_switch_service.cache_service.redis", fake_redis)
    monkeypatch.setattr(settings, "AURORA_STAGE40_CALENDAR_MODE", "live", raising=False)

    assert await AuroraStage40CalendarKillSwitchService().get_mode() == "off"


def test_stage40_calendar_shadow_mode_skips_prompt_render(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_STAGE40_CALENDAR_MODE", "live", raising=False)

    rendered = format_user_context(
        {
            "calendar_context": {
                "_stage40_mode": "shadow",
                "workload_density": "high",
                "upcoming_deadlines": [
                    {
                        "title": "高数作业",
                        "start_time": "2026-04-24T09:00:00",
                        "end_time": "2026-04-24T10:00:00",
                        "source": "task",
                    }
                ],
            }
        }
    )

    assert "【时间约束】" not in rendered
    assert "高数作业" not in rendered
