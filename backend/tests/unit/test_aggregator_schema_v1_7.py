from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.core.cache import cache_service
from app.state_aggregator.service import StateAggregatorService
from app.services.aurora_stage26_scene_kill_switch_service import AuroraStage26SceneKillSwitchService
from tests.unit.scene_test_helpers import make_scene


class _InMemoryKillSwitchRedis:
    """Minimal Redis stub: kill switch read/write only touch get/set on mode keys."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value


@pytest.fixture(name="scene_kill_switch_redis")
async def scene_kill_switch_redis_fixture(monkeypatch):
    """Make the stage26 scene kill switch hermetic (no live Redis required).

    Without Redis, kill_switch.write_mode drops the write and read_mode falls
    back to settings.AURORA_SCENE_MODE ("live"), so set_mode("shadow") silently
    no-ops and the hides-outside-live-mode assertion can never pass. Same
    stubbing pattern as tests/unit/test_stage19_kill_switch.py.
    """
    fake = _InMemoryKillSwitchRedis()
    monkeypatch.setattr(cache_service, "redis", fake)
    return fake


@pytest.mark.asyncio
async def test_aggregator_schema_v1_7_reports_recent_scenes(db_session, scene_kill_switch_redis) -> None:
    user_id = uuid4()
    db_session.add(make_scene(user_id=user_id, member_memory_ids=[str(uuid4()), str(uuid4()), str(uuid4())]))
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")

    state = await StateAggregatorService(db_session).get_user_state(
        user_id,
        required_fields=("recent_scenes",),
    )

    assert state.schema_version == "user_state.v1.13"
    assert state.recent_scenes is not None
    assert len(state.recent_scenes.value.items) == 1


@pytest.mark.asyncio
async def test_aggregator_recent_scenes_field_keeps_30_second_ttl(db_session, scene_kill_switch_redis) -> None:
    await AuroraStage26SceneKillSwitchService().set_mode("live")

    state = await StateAggregatorService(db_session).get_user_state(
        uuid4(),
        required_fields=("recent_scenes",),
    )

    assert state.recent_scenes is not None
    assert StateAggregatorService.FIELD_TTLS_SECONDS["recent_scenes"] == 30


@pytest.mark.asyncio
async def test_aggregator_hides_recent_scenes_outside_live_mode(db_session, scene_kill_switch_redis) -> None:
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
