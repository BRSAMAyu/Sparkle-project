from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.services.aurora_stage27_foresight_kill_switch_service import AuroraStage27ForesightKillSwitchService
from app.schemas.foresight import Deviation
from app.services.jitai_trigger_service import JITAITrigger, TEMPLATE_REGISTRY


def _deviation(
    *,
    dim: str = "study_pace",
    z_score: float = -3.0,
    confidence: float = 0.8,
    direction: str = "below",
) -> Deviation:
    return Deviation(
        dim=dim,
        current_value=0.4,
        baseline=1.0,
        z_score=z_score,
        direction=direction,
        projected_3d=0.7,
        confidence=confidence,
    )


def _clear_local_state() -> None:
    if hasattr(settings, JITAITrigger.LOCAL_STATE_ATTR):
        delattr(settings, JITAITrigger.LOCAL_STATE_ATTR)


@pytest.fixture(autouse=True)
def _use_local_jitai_state(monkeypatch):
    monkeypatch.setattr(cache_service, "redis", None)
    _clear_local_state()


@pytest.mark.asyncio
async def test_jitai_generates_hint_for_eligible_deviation() -> None:
    _clear_local_state()
    hints = await JITAITrigger().generate_hints(
        user_id=uuid4(),
        deviations=(_deviation(),),
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert len(hints) == 1
    assert "学习节奏" in hints[0].message


@pytest.mark.asyncio
async def test_jitai_selects_above_template() -> None:
    _clear_local_state()
    hints = await JITAITrigger().generate_hints(
        user_id=uuid4(),
        deviations=(_deviation(direction="above", z_score=3.0),),
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert len(hints) == 1
    assert hints[0].template_id == "study_pace_above"


@pytest.mark.asyncio
async def test_jitai_skips_low_confidence_deviation() -> None:
    _clear_local_state()
    hints = await JITAITrigger().generate_hints(
        user_id=uuid4(),
        deviations=(_deviation(confidence=0.4),),
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert hints == ()


@pytest.mark.asyncio
async def test_jitai_skips_under_threshold_z_score() -> None:
    _clear_local_state()
    hints = await JITAITrigger().generate_hints(
        user_id=uuid4(),
        deviations=(_deviation(z_score=-1.2),),
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert hints == ()


@pytest.mark.asyncio
async def test_jitai_hint_contains_template_id_and_message() -> None:
    _clear_local_state()
    hints = await JITAITrigger().generate_hints(
        user_id=uuid4(),
        deviations=(_deviation(dim="completion_rate"),),
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert hints[0].template_id == "completion_rate_below"
    assert hints[0].message == TEMPLATE_REGISTRY["completion_rate:below"]["message"]


@pytest.mark.asyncio
async def test_jitai_budget_usage_increments_after_live_trigger() -> None:
    _clear_local_state()
    service = JITAITrigger()
    user_id = uuid4()
    now = datetime(2026, 4, 21, 9, 0, 0)

    await service.generate_hints(user_id=user_id, deviations=(_deviation(),), now=now)

    assert await service.get_daily_budget_usage(user_id=user_id, now=now) == 1


@pytest.mark.asyncio
async def test_jitai_shadow_mode_can_be_reached_by_misfire_auto_downgrade() -> None:
    _clear_local_state()
    kill_switch = AuroraStage27ForesightKillSwitchService()
    await kill_switch.set_mode("live")
    await kill_switch.set_feature_mode("deviation", "live")
    await kill_switch.set_feature_mode("jitai", "live")
    service = JITAITrigger()
    base = datetime(2026, 4, 21, 9, 0, 0)
    for offset in range(2, -1, -1):
        day = base - timedelta(days=offset)
        for _ in range(10):
            await service.generate_hints(user_id=uuid4(), deviations=(_deviation(),), now=day)
        for _ in range(2):
            await service.record_misfire(now=day)

    assert await kill_switch.get_feature_mode("deviation") == "shadow"
    assert await kill_switch.get_feature_mode("jitai") == "shadow"


def test_jitai_template_registry_is_complete() -> None:
    expected = {
        "study_pace:below",
        "study_pace:above",
        "completion_rate:below",
        "completion_rate:above",
        "engagement_level:below",
        "engagement_level:above",
        "mood_valence:below",
        "mood_valence:above",
        "plan_adherence:below",
        "plan_adherence:above",
    }

    assert expected.issubset(TEMPLATE_REGISTRY)
