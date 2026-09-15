from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.schemas.scene import SceneRecord
from app.services.scene_consolidation_service import SceneConsolidationService, build_scene_id
from tests.unit.scene_test_helpers import make_memory, make_scene


def test_build_scene_id_is_stable_for_same_member_set() -> None:
    user_id = uuid4()
    left = build_scene_id(
        user_id=user_id,
        member_memory_ids=["b", "a", "a"],
        version="scene.v1",
    )
    right = build_scene_id(
        user_id=user_id,
        member_memory_ids=["a", "b"],
        version="scene.v1",
    )

    assert left == right


def test_build_scene_id_changes_when_algorithm_version_changes() -> None:
    user_id = uuid4()

    assert build_scene_id(user_id=user_id, member_memory_ids=["a"], version="scene.v1") != build_scene_id(
        user_id=user_id,
        member_memory_ids=["a"],
        version="scene.v2",
    )


def test_scene_record_schema_round_trips_scene_model() -> None:
    user_id = uuid4()
    scene = make_scene(user_id=user_id, member_memory_ids=[str(uuid4()), str(uuid4())])

    payload = SceneRecord.model_validate(scene)

    assert payload.user_id == user_id
    assert payload.member_memory_ids == scene.member_memory_ids
    assert payload.quality_score == scene.quality_score


@pytest.mark.asyncio
async def test_scene_user_isolation_rejects_cross_user_member(db_session) -> None:
    owner_id = uuid4()
    intruder_id = uuid4()
    owner_memory = make_memory(
        user_id=owner_id,
        summary="周末早晨学习数学",
        occurred_at=datetime(2026, 4, 19, 9, 0, 0),
        embedding=[0.9, 0.1, 0.0],
    )
    intruder_memory = make_memory(
        user_id=intruder_id,
        summary="另一个用户的数学记忆",
        occurred_at=datetime(2026, 4, 19, 10, 0, 0),
        embedding=[0.9, 0.1, 0.0],
    )
    db_session.add_all([owner_memory, intruder_memory])
    await db_session.commit()

    scene = make_scene(
        user_id=owner_id,
        member_memory_ids=[str(owner_memory.id), str(intruder_memory.id)],
    )
    db_session.add(scene)
    await db_session.commit()

    with pytest.raises(ValueError, match="cross user"):
        await SceneConsolidationService(db_session).assert_scene_user_isolation(
            scene=scene,
            expected_user_id=owner_id,
        )
