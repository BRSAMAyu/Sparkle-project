from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.services.persdyn_attractor_service import PersDynAttractorService
from tests.unit.foresight_test_helpers import seed_foresight_history


@pytest.mark.asyncio
async def test_attractor_cold_start_rows_have_confidence_below_point_three(db_session) -> None:
    user_id = uuid4()
    await seed_foresight_history(
        db_session,
        user_id=user_id,
        days=8,
        start_day=datetime(2026, 4, 13, 8, 0, 0),
    )

    states = await PersDynAttractorService(db_session).recompute_user_attractors(
        user_id=user_id,
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert all(state.confidence < 0.3 for state in states.values())


@pytest.mark.asyncio
async def test_attractor_snapshot_hides_cold_start_rows(db_session) -> None:
    user_id = uuid4()
    await seed_foresight_history(
        db_session,
        user_id=user_id,
        days=12,
        start_day=datetime(2026, 4, 10, 8, 0, 0),
    )

    states = await PersDynAttractorService(db_session).get_snapshot_attractors(
        user_id=user_id,
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert states == {}


@pytest.mark.asyncio
async def test_attractor_snapshot_returns_rows_at_fourteen_days(db_session) -> None:
    user_id = uuid4()
    await seed_foresight_history(
        db_session,
        user_id=user_id,
        days=14,
        start_day=datetime(2026, 4, 8, 8, 0, 0),
    )

    states = await PersDynAttractorService(db_session).get_snapshot_attractors(
        user_id=user_id,
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert states
    assert all(state.confidence >= 0.3 for state in states.values())
