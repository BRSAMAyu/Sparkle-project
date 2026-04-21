from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.core.cache import cache_service
from app.schemas.foresight import Deviation
from app.services.jitai_trigger_service import JITAITrigger


def _deviation(*, dim: str = "study_pace") -> Deviation:
    return Deviation(
        dim=dim,
        current_value=0.4,
        baseline=1.0,
        z_score=-3.0,
        direction="below",
        projected_3d=0.7,
        confidence=0.8,
    )


async def _clear_local_state() -> None:
    from app.config import settings

    if hasattr(settings, JITAITrigger.LOCAL_STATE_ATTR):
        delattr(settings, JITAITrigger.LOCAL_STATE_ATTR)


@pytest.fixture(autouse=True)
def _use_local_jitai_state(monkeypatch):
    monkeypatch.setattr(cache_service, "redis", None)


async def test_jitai_cooldown_blocks_same_dim_second_trigger() -> None:
    await _clear_local_state()
    service = JITAITrigger()
    user_id = uuid4()
    now = datetime(2026, 4, 21, 9, 0, 0)

    first = await service.generate_hints(user_id=user_id, deviations=(_deviation(),), now=now)
    second = await service.generate_hints(user_id=user_id, deviations=(_deviation(),), now=now + timedelta(hours=1))

    assert len(first) == 1
    assert second == ()


async def test_jitai_cooldown_is_per_dimension() -> None:
    await _clear_local_state()
    service = JITAITrigger()
    user_id = uuid4()
    now = datetime(2026, 4, 21, 9, 0, 0)

    await service.generate_hints(user_id=user_id, deviations=(_deviation(dim="study_pace"),), now=now)
    second = await service.generate_hints(user_id=user_id, deviations=(_deviation(dim="completion_rate"),), now=now)

    assert len(second) == 1


async def test_jitai_daily_budget_caps_at_three() -> None:
    await _clear_local_state()
    service = JITAITrigger()
    user_id = uuid4()
    now = datetime(2026, 4, 21, 9, 0, 0)

    first = await service.generate_hints(
        user_id=user_id,
        deviations=(
            _deviation(dim="study_pace"),
            _deviation(dim="completion_rate"),
            _deviation(dim="engagement_level"),
            _deviation(dim="mood_valence"),
        ),
        now=now,
    )
    second = await service.generate_hints(user_id=user_id, deviations=(_deviation(dim="plan_adherence"),), now=now)

    assert len(first) == 3
    assert second == ()


async def test_jitai_budget_resets_next_day() -> None:
    await _clear_local_state()
    service = JITAITrigger()
    user_id = uuid4()
    now = datetime(2026, 4, 21, 9, 0, 0)

    await service.generate_hints(
        user_id=user_id,
        deviations=(
            _deviation(dim="study_pace"),
            _deviation(dim="completion_rate"),
            _deviation(dim="engagement_level"),
        ),
        now=now,
    )
    next_day = await service.generate_hints(
        user_id=user_id,
        deviations=(_deviation(dim="plan_adherence"),),
        now=now + timedelta(days=1),
    )

    assert len(next_day) == 1
