from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.state_aggregator.service import StateAggregatorService
from app.services.aurora_stage26_scene_kill_switch_service import AuroraStage26SceneKillSwitchService
from tests.unit.scene_test_helpers import make_scene


@pytest.mark.asyncio
async def test_aggregator_schema_v1_7_reports_recent_scenes(db_session) -> None:
    user_id = uuid4()
    db_session.add(make_scene(user_id=user_id, member_memory_ids=[str(uuid4()), str(uuid4()), str(uuid4())]))
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")

    state = await StateAggregatorService(db_session).get_user_state(
        user_id,
        required_fields=("recent_scenes",),
    )

    assert state.schema_version == "user_state.v1.12"
    assert state.recent_scenes is not None
    assert len(state.recent_scenes.value.items) == 1


@pytest.mark.asyncio
async def test_aggregator_recent_scenes_field_keeps_30_second_ttl(db_session) -> None:
    await AuroraStage26SceneKillSwitchService().set_mode("live")

    state = await StateAggregatorService(db_session).get_user_state(
        uuid4(),
        required_fields=("recent_scenes",),
    )

    assert state.recent_scenes is not None
    assert StateAggregatorService.FIELD_TTLS_SECONDS["recent_scenes"] == 30


@pytest.mark.asyncio
async def test_aggregator_hides_recent_scenes_outside_live_mode(db_session) -> None:
    user_id = uuid4()
    db_session.add(
        make_scene(
            user_id=user_id,
            member_memory_ids=[str(uuid4())],
            time_start=datetime(2026, 4, 19, 9, 0, 0),
            time_end=datetime(2026, 4, 19, 10, 0, 0),
        )
    )
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("shadow")

    state = await StateAggregatorService(db_session).get_user_state(
        user_id,
        required_fields=("recent_scenes",),
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert state.recent_scenes is not None
    assert state.recent_scenes.value.items == ()
