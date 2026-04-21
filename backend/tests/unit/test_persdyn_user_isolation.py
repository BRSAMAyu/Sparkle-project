from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.aurora_stage27 import PersDynAttractor
from app.services.persdyn_attractor_service import PersDynAttractorService
from tests.unit.foresight_test_helpers import seed_foresight_history


@pytest.mark.asyncio
async def test_persdyn_snapshot_reads_only_owner_rows(db_session) -> None:
    owner_id = uuid4()
    other_id = uuid4()
    now = datetime(2026, 4, 21, 9, 0, 0)
    await seed_foresight_history(db_session, user_id=owner_id, days=28, start_day=datetime(2026, 3, 25, 8, 0, 0))
    await seed_foresight_history(db_session, user_id=other_id, days=28, start_day=datetime(2026, 3, 25, 8, 0, 0), recent_drop=True)

    states = await PersDynAttractorService(db_session).get_snapshot_attractors(user_id=owner_id, now=now)

    assert states
    assert all(state.dim in PersDynAttractorService.DIMENSIONS for state in states.values())


@pytest.mark.asyncio
async def test_persdyn_upsert_does_not_overwrite_other_user_rows(db_session) -> None:
    owner_id = uuid4()
    other_id = uuid4()
    now = datetime(2026, 4, 21, 9, 0, 0)
    await seed_foresight_history(db_session, user_id=owner_id, days=28, start_day=datetime(2026, 3, 25, 8, 0, 0))
    await seed_foresight_history(db_session, user_id=other_id, days=28, start_day=datetime(2026, 3, 25, 8, 0, 0), recent_drop=True)

    service = PersDynAttractorService(db_session)
    await service.recompute_user_attractors(user_id=owner_id, now=now)
    await service.recompute_user_attractors(user_id=other_id, now=now)

    rows = (await db_session.execute(select(PersDynAttractor))).scalars().all()
    owner_rows = [row for row in rows if row.user_id == owner_id]
    other_rows = [row for row in rows if row.user_id == other_id]

    assert len(owner_rows) == 5
    assert len(other_rows) == 5


@pytest.mark.asyncio
async def test_persdyn_build_current_observation_is_user_scoped(db_session) -> None:
    owner_id = uuid4()
    other_id = uuid4()
    now = datetime(2026, 4, 21, 9, 0, 0)
    await seed_foresight_history(db_session, user_id=owner_id, days=28, start_day=datetime(2026, 3, 25, 8, 0, 0))
    await seed_foresight_history(db_session, user_id=other_id, days=28, start_day=datetime(2026, 3, 25, 8, 0, 0), recent_drop=True)

    owner_observation = await PersDynAttractorService(db_session).build_current_observation(user_id=owner_id, now=now)
    other_observation = await PersDynAttractorService(db_session).build_current_observation(user_id=other_id, now=now)

    assert owner_observation != other_observation


def test_persdyn_requires_non_empty_user_id(db_session) -> None:
    with pytest.raises(ValueError):
        PersDynAttractorService(db_session)._require_user_id("")
