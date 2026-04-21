from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.memory import Scene
from app.services.aurora_stage26_scene_kill_switch_service import AuroraStage26SceneKillSwitchService
from app.services.scene_consolidation_service import SceneConsolidationService
from tests.unit.scene_test_helpers import make_memory


@pytest.mark.asyncio
async def test_scene_cluster_creates_new_scene_for_first_memory(db_session) -> None:
    user_id = uuid4()
    memory = make_memory(
        user_id=user_id,
        summary="周末早晨学习数学",
        occurred_at=datetime(2026, 4, 19, 9, 0, 0),
        embedding=[0.9, 0.1, 0.0],
    )
    db_session.add(memory)
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")

    result = await SceneConsolidationService(db_session).consolidate_memory(memory)

    assert result.action == "created"
    assert result.scene is not None
    assert result.scene.member_memory_ids == [str(memory.id)]


@pytest.mark.asyncio
async def test_scene_cluster_merges_similar_memory_within_window(db_session) -> None:
    user_id = uuid4()
    first = make_memory(
        user_id=user_id,
        summary="周末早晨刷数学题",
        occurred_at=datetime(2026, 4, 19, 9, 0, 0),
        embedding=[0.95, 0.05, 0.0],
        tags=["topic:数学"],
    )
    second = make_memory(
        user_id=user_id,
        summary="周末早晨继续复盘数学错题",
        occurred_at=datetime(2026, 4, 19, 11, 0, 0),
        embedding=[0.92, 0.08, 0.0],
        tags=["topic:数学"],
    )
    db_session.add_all([first, second])
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")
    service = SceneConsolidationService(db_session)

    await service.consolidate_memory(first)
    result = await service.consolidate_memory(second)

    assert result.action == "merged"
    assert len(result.scene.member_memory_ids) == 2


@pytest.mark.asyncio
async def test_scene_cluster_splits_when_similarity_is_below_threshold(db_session) -> None:
    user_id = uuid4()
    first = make_memory(
        user_id=user_id,
        summary="周末早晨学数学",
        occurred_at=datetime(2026, 4, 19, 9, 0, 0),
        embedding=[1.0, 0.0, 0.0],
    )
    second = make_memory(
        user_id=user_id,
        summary="周末早晨整理英语作文",
        occurred_at=datetime(2026, 4, 19, 10, 0, 0),
        embedding=[0.0, 1.0, 0.0],
    )
    db_session.add_all([first, second])
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")
    service = SceneConsolidationService(db_session)

    await service.consolidate_memory(first)
    await service.consolidate_memory(second)

    rows = (await db_session.execute(select(Scene))).scalars().all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_scene_cluster_splits_when_outside_time_window(db_session) -> None:
    user_id = uuid4()
    first = make_memory(
        user_id=user_id,
        summary="第一次学习数学",
        occurred_at=datetime(2026, 4, 19, 9, 0, 0),
        embedding=[0.95, 0.05, 0.0],
    )
    second = make_memory(
        user_id=user_id,
        summary="四天后的学习数学",
        occurred_at=datetime(2026, 4, 23, 9, 0, 0),
        embedding=[0.95, 0.05, 0.0],
    )
    db_session.add_all([first, second])
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")
    service = SceneConsolidationService(db_session)

    await service.consolidate_memory(first)
    await service.consolidate_memory(second)

    rows = (await db_session.execute(select(Scene))).scalars().all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_scene_cluster_is_idempotent_for_repeated_single_memory_runs(db_session) -> None:
    user_id = uuid4()
    memory = make_memory(
        user_id=user_id,
        summary="重复跑不该创建第二个 scene",
        occurred_at=datetime(2026, 4, 19, 9, 0, 0),
        embedding=[0.8, 0.2, 0.0],
    )
    db_session.add(memory)
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")
    service = SceneConsolidationService(db_session)

    first = await service.consolidate_memory(memory)
    second = await service.consolidate_memory(memory)

    rows = (await db_session.execute(select(Scene))).scalars().all()
    assert first.scene.scene_id == second.scene.scene_id
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_scene_backfill_groups_history_deterministically(db_session) -> None:
    user_id = uuid4()
    base = datetime(2026, 4, 19, 9, 0, 0)
    db_session.add_all(
        [
            make_memory(user_id=user_id, summary="数学 1", occurred_at=base, embedding=[0.9, 0.1, 0.0]),
            make_memory(user_id=user_id, summary="数学 2", occurred_at=base + timedelta(hours=1), embedding=[0.91, 0.09, 0.0]),
            make_memory(user_id=user_id, summary="英语 1", occurred_at=base + timedelta(hours=2), embedding=[0.0, 0.9, 0.1]),
            make_memory(user_id=user_id, summary="英语 2", occurred_at=base + timedelta(hours=3), embedding=[0.0, 0.92, 0.08]),
        ]
    )
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")

    first = await SceneConsolidationService(db_session).backfill_user_scenes(user_id=user_id)
    second = await SceneConsolidationService(db_session).backfill_user_scenes(user_id=user_id)

    assert sorted(scene.scene_id for scene in first) == sorted(scene.scene_id for scene in second)
    assert len(first) == 2


@pytest.mark.asyncio
async def test_scene_cluster_skips_non_inferred_lane(db_session) -> None:
    user_id = uuid4()
    memory = make_memory(
        user_id=user_id,
        summary="direct_capture 不进 scene",
        occurred_at=datetime(2026, 4, 19, 9, 0, 0),
        embedding=[0.8, 0.2, 0.0],
        source_lane="direct_capture",
    )
    db_session.add(memory)
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")

    result = await SceneConsolidationService(db_session).consolidate_memory(memory)

    assert result.action == "skipped"


@pytest.mark.asyncio
async def test_scene_cluster_skips_reflection_source_type(db_session) -> None:
    user_id = uuid4()
    memory = make_memory(
        user_id=user_id,
        summary="reflection 不进 scene",
        occurred_at=datetime(2026, 4, 19, 9, 0, 0),
        embedding=[0.8, 0.2, 0.0],
        source_type="reflection",
    )
    db_session.add(memory)
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")

    result = await SceneConsolidationService(db_session).consolidate_memory(memory)

    assert result.action == "skipped"
