from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.schemas.foresight import Deviation
from app.services.jitai_trigger_service import JITAITrigger


@pytest.fixture(autouse=True)
def _use_local_jitai_state(monkeypatch):
    monkeypatch.setattr(cache_service, "redis", None)
    if hasattr(settings, JITAITrigger.LOCAL_STATE_ATTR):
        delattr(settings, JITAITrigger.LOCAL_STATE_ATTR)


def _deviation(*, z_score: float = -3.0, confidence: float = 0.8) -> Deviation:
    return Deviation(
        dim="study_pace",
        current_value=0.4,
        baseline=1.0,
        z_score=z_score,
        direction="below",
        projected_3d=0.7,
        confidence=confidence,
    )


@pytest.mark.asyncio
async def test_sqam_jitai_id1_skips_non_finite_deviation() -> None:
    hints = await JITAITrigger().generate_hints(
        user_id=uuid4(),
        deviations=(_deviation(z_score=float("nan")),),
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert hints == ()


@pytest.mark.asyncio
async def test_sqam_jitai_dp1_event_payload_hashes_user_id(monkeypatch) -> None:
    publish_mock = AsyncMock()
    monkeypatch.setattr(
        "app.services.jitai_trigger_service.event_bus.publish", publish_mock
    )

    await JITAITrigger().generate_hints(
        user_id=uuid4(),
        deviations=(_deviation(),),
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    payload = publish_mock.await_args.args[1]
    assert "user_id_hash" in payload
    assert "user_id" not in payload


def test_sqam_jitai_dp1_internal_budget_key_stays_plaintext() -> None:
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    key = JITAITrigger._budget_key(user_id, now=datetime(2026, 4, 21, 9, 0, 0))

    assert user_id in key
