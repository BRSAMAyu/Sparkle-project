from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.persdyn_attractor_service import PersDynAttractorService
from tests.unit.foresight_test_helpers import make_study_record, seed_foresight_history


@pytest.mark.asyncio
async def test_sqam_persdyn_id1_clamps_study_pace_to_unit_interval(db_session) -> None:
    user_id = uuid4()
    node_id = uuid4()
    now = datetime(2026, 4, 21, 9, 0, 0)
    for offset in range(3):
        db_session.add(
            make_study_record(
                user_id=user_id,
                node_id=node_id,
                created_at=now - timedelta(days=offset),
                study_minutes=180,
            )
        )
    await db_session.commit()

    service = PersDynAttractorService(db_session)
    rows = await service._load_signal_rows(user_id, now)
    observation = service._build_observation_for_day(
        rows=rows, reference_day=now.date()
    )

    assert observation["study_pace"] == 1.0


def test_sqam_persdyn_st1_ema_ignores_non_finite_values(db_session) -> None:
    service = PersDynAttractorService(db_session)

    result = service._ema([0.2, float("inf"), 0.4])

    assert 0.0 <= result <= 1.0


@pytest.mark.asyncio
async def test_sqam_persdyn_dp1_event_payload_omits_state_internals(
    db_session, monkeypatch
) -> None:
    user_id = uuid4()
    await seed_foresight_history(
        db_session,
        user_id=user_id,
        days=28,
        start_day=datetime(2026, 3, 25, 8, 0, 0),
    )
    publish_mock = AsyncMock()
    monkeypatch.setattr(
        "app.services.persdyn_attractor_service.event_bus.publish", publish_mock
    )

    await PersDynAttractorService(db_session).recompute_user_attractors(
        user_id=user_id,
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    payload = publish_mock.await_args.args[1]
    assert {"baseline", "variability", "recovery_rate", "confidence"}.isdisjoint(
        payload
    )
