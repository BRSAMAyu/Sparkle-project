from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.services.aurora_stage26_scene_kill_switch_service import AuroraStage26SceneKillSwitchService
from app.services.scene_consolidation_service import SceneConsolidationService
from tests.unit.scene_test_helpers import make_memory, make_scene


@pytest.mark.asyncio
async def test_recent_scenes_are_scoped_per_user(db_session) -> None:
    owner_id = uuid4()
    other_id = uuid4()
    db_session.add_all(
        [
            make_scene(user_id=owner_id, member_memory_ids=[str(uuid4())]),
            make_scene(user_id=other_id, member_memory_ids=[str(uuid4())]),
        ]
    )
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")

    items = await SceneConsolidationService(db_session).list_recent_scenes_for_aggregator(
        user_id=owner_id,
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert len(items) == 1


@pytest.mark.asyncio
async def test_scene_user_isolation_blocks_cross_user_candidate_merge(db_session) -> None:
    owner_id = uuid4()
    other_id = uuid4()
    db_session.add(
        make_scene(
            user_id=other_id,
            member_memory_ids=[str(uuid4())],
            centroid_embedding=[0.95, 0.05],
        )
    )
    memory = make_memory(
        user_id=owner_id,
        summary="不该合并到别人的 scene",
        occurred_at=datetime(2026, 4, 19, 9, 0, 0),
        embedding=[0.95, 0.05],
    )
    db_session.add(memory)
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")

    result = await SceneConsolidationService(db_session).consolidate_memory(memory)

    assert result.action == "created"
    assert result.scene.user_id == owner_id


@pytest.mark.asyncio
async def test_assert_scene_user_isolation_blocks_cross_user_attack(db_session) -> None:
    owner_id = uuid4()
    owner_memory = make_memory(
        user_id=owner_id,
        summary="owner",
        occurred_at=datetime(2026, 4, 19, 9, 0, 0),
        embedding=[0.8, 0.2],
    )
    db_session.add(owner_memory)
    await db_session.commit()
    scene = make_scene(user_id=owner_id, member_memory_ids=[str(owner_memory.id)])
    await SceneConsolidationService(db_session).assert_scene_user_isolation(scene=scene, expected_user_id=owner_id)


@pytest.mark.asyncio
async def test_scene_list_rejects_foreign_access_by_expected_user_mismatch(db_session) -> None:
    scene = make_scene(user_id=uuid4(), member_memory_ids=[str(uuid4())])

    with pytest.raises(ValueError, match="cross-user"):
        await SceneConsolidationService(db_session).assert_scene_user_isolation(
            scene=scene,
            expected_user_id=uuid4(),
        )
