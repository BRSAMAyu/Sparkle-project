from __future__ import annotations

import pytest

from app.config import settings
from app.services.aurora_stage28_traits_kill_switch_service import AuroraStage28TraitsKillSwitchService


@pytest.mark.asyncio
async def test_bias_auto_downgrade_turns_off_nlp_after_three_failures() -> None:
    settings.AURORA_TRAITS_NLP_BIAS_THRESHOLD = 0.10
    service = AuroraStage28TraitsKillSwitchService()
    await service.set_mode("live")
    await service.set_nlp_mode("live")

    await service.record_bias_rate(0.2)
    await service.record_bias_rate(0.2)
    mode = await service.record_bias_rate(0.2)

    assert mode == "off"


@pytest.mark.asyncio
async def test_bias_auto_downgrade_resets_streak_when_bias_recovers() -> None:
    settings.AURORA_TRAITS_NLP_BIAS_THRESHOLD = 0.10
    service = AuroraStage28TraitsKillSwitchService()
    await service.set_mode("live")
    await service.set_nlp_mode("live")

    await service.record_bias_rate(0.2)
    await service.record_bias_rate(0.01)
    mode = await service.record_bias_rate(0.2)

    assert mode == "live"


@pytest.mark.asyncio
async def test_bias_auto_downgrade_keeps_off_mode_stable() -> None:
    settings.AURORA_TRAITS_NLP_BIAS_THRESHOLD = 0.10
    service = AuroraStage28TraitsKillSwitchService()
    await service.set_mode("live")
    await service.set_nlp_mode("off")

    mode = await service.record_bias_rate(0.2)

    assert mode == "off"
