from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.services.aurora_stage26_scene_kill_switch_service import AuroraStage26SceneKillSwitchService
from app.services.scene_consolidation_service import SceneConsolidationService, build_scene_id
from tests.unit.scene_test_helpers import make_memory


def test_scene_id_hash_is_order_independent() -> None:
    user_id = uuid4()

    assert build_scene_id(user_id=user_id, member_memory_ids=["1", "2"], version="scene.v1") == build_scene_id(
        user_id=user_id,
        member_memory_ids=["2", "1"],
        version="scene.v1",
    )


@pytest.mark.asyncio
async def test_repeated_stream_processing_produces_same_scene_id(db_session) -> None:
    user_id = uuid4()
    base = datetime(2026, 4, 19, 9, 0, 0)
    first = make_memory(user_id=user_id, summary="数学", occurred_at=base, embedding=[0.9, 0.1])
    second = make_memory(user_id=user_id, summary="数学续集", occurred_at=base + timedelta(hours=1), embedding=[0.91, 0.09])
    db_session.add_all([first, second])
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")
    service = SceneConsolidationService(db_session)

    a = await service.consolidate_memory(first)
    created_scene_id = a.scene.scene_id
    b = await service.consolidate_memory(second)
    c = await service.consolidate_memory(first)
    d = await service.consolidate_memory(second)

    assert b.scene.scene_id == d.scene.scene_id
    assert created_scene_id != b.scene.scene_id
    assert c.scene.scene_id == b.scene.scene_id


@pytest.mark.asyncio
async def test_backfill_three_replays_produce_same_scene_set(db_session) -> None:
    user_id = uuid4()
    base = datetime(2026, 4, 19, 9, 0, 0)
    db_session.add_all(
        [
            make_memory(user_id=user_id, summary="数学1", occurred_at=base, embedding=[0.9, 0.1]),
            make_memory(user_id=user_id, summary="数学2", occurred_at=base + timedelta(hours=1), embedding=[0.91, 0.09]),
            make_memory(user_id=user_id, summary="英语1", occurred_at=base + timedelta(days=1), embedding=[0.1, 0.9]),
        ]
    )
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")
    service = SceneConsolidationService(db_session)

    first = sorted(scene.scene_id for scene in await service.backfill_user_scenes(user_id=user_id))
    second = sorted(scene.scene_id for scene in await service.backfill_user_scenes(user_id=user_id))
    third = sorted(scene.scene_id for scene in await service.backfill_user_scenes(user_id=user_id))

    assert first == second == third


def test_scene_id_hash_changes_when_algorithm_version_changes() -> None:
    user_id = uuid4()

    assert build_scene_id(user_id=user_id, member_memory_ids=["1", "2"], version="scene.v1") != build_scene_id(
        user_id=user_id,
        member_memory_ids=["1", "2"],
        version="scene.v2",
    )
