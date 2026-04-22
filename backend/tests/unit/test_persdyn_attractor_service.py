from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.aurora_stage27 import PersDynAttractor
from app.services.persdyn_attractor_service import PersDynAttractorService
from tests.unit.foresight_test_helpers import (
    make_reflection,
    make_study_record,
    make_task,
    seed_foresight_history,
)


def test_persdyn_dimensions_are_frozen_whitelist() -> None:
    assert PersDynAttractorService.DIMENSIONS == (
        "study_pace",
        "completion_rate",
        "engagement_level",
        "mood_valence",
        "plan_adherence",
    )


def test_persdyn_ema_uses_alpha_point_one(db_session) -> None:
    service = PersDynAttractorService(db_session)

    result = service._ema([1.0, 2.0, 3.0])

    assert round(result, 3) == 1.29


def test_persdyn_confidence_marks_cold_start_below_threshold(db_session) -> None:
    service = PersDynAttractorService(db_session)

    assert service._confidence(10) < 0.3


def test_persdyn_confidence_scales_to_high_confidence_after_full_window(
    db_session,
) -> None:
    service = PersDynAttractorService(db_session)

    assert service._confidence(28) == 0.95


@pytest.mark.asyncio
async def test_persdyn_build_observation_maps_reflection_valence(db_session) -> None:
    user_id = uuid4()
    now = datetime(2026, 4, 21, 9, 0, 0)
    db_session.add(
        make_reflection(
            user_id=user_id, occurred_at=now - timedelta(hours=1), category="overload"
        )
    )
    await db_session.commit()

    service = PersDynAttractorService(db_session)
    rows = await service._load_signal_rows(user_id, now)
    observation = service._build_observation_for_day(
        rows=rows, reference_day=now.date()
    )

    assert observation["mood_valence"] == 0.1


@pytest.mark.asyncio
async def test_persdyn_build_observation_penalizes_overdue_plan_tasks(
    db_session,
) -> None:
    user_id = uuid4()
    plan_id = uuid4()
    now = datetime(2026, 4, 21, 9, 0, 0)
    db_session.add(
        make_task(
            user_id=user_id,
            created_at=now - timedelta(days=2),
            due_date=(now - timedelta(days=1)).date(),
            completed_at=None,
            plan_id=plan_id,
        )
    )
    await db_session.commit()

    service = PersDynAttractorService(db_session)
    rows = await service._load_signal_rows(user_id, now)
    observation = service._build_observation_for_day(
        rows=rows, reference_day=now.date()
    )

    assert observation["plan_adherence"] == 0.0


@pytest.mark.asyncio
async def test_persdyn_build_observation_averages_study_pace_over_three_days(
    db_session,
) -> None:
    user_id = uuid4()
    node_id = uuid4()
    now = datetime(2026, 4, 21, 9, 0, 0)
    for offset in range(3):
        db_session.add(
            make_study_record(
                user_id=user_id,
                node_id=node_id,
                created_at=now - timedelta(days=offset),
                study_minutes=90,
            )
        )
    await db_session.commit()

    service = PersDynAttractorService(db_session)
    rows = await service._load_signal_rows(user_id, now)
    observation = service._build_observation_for_day(
        rows=rows, reference_day=now.date()
    )

    assert observation["study_pace"] == 1.0


@pytest.mark.asyncio
async def test_persdyn_recompute_persists_rows_per_dimension(db_session) -> None:
    user_id = uuid4()
    await seed_foresight_history(
        db_session,
        user_id=user_id,
        days=28,
        start_day=datetime(2026, 3, 25, 8, 0, 0),
    )

    states = await PersDynAttractorService(db_session).recompute_user_attractors(
        user_id=user_id,
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    rows = (
        (
            await db_session.execute(
                select(PersDynAttractor).where(PersDynAttractor.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    assert len(states) == 5
    assert len(rows) == 5


@pytest.mark.asyncio
async def test_persdyn_snapshot_filters_low_confidence_rows(db_session) -> None:
    user_id = uuid4()
    await seed_foresight_history(
        db_session,
        user_id=user_id,
        days=10,
        start_day=datetime(2026, 4, 11, 8, 0, 0),
        include_scenes=False,
    )

    states = await PersDynAttractorService(db_session).get_snapshot_attractors(
        user_id=user_id,
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert states == {}
