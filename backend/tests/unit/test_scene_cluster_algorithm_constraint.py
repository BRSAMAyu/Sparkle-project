from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.memory import Scene
from app.services.aurora_stage26_scene_kill_switch_service import AuroraStage26SceneKillSwitchService
from app.services.scene_consolidation_service import SceneConsolidationService, assert_rule_ak_algorithm_constraint
from tests.unit.scene_test_helpers import make_memory


def test_rule_ak_requires_positive_similarity_threshold() -> None:
    with pytest.raises(ValueError, match="similarity threshold"):
        assert_rule_ak_algorithm_constraint(similarity_threshold=0.0, time_window_hours=72)


def test_rule_ak_requires_positive_time_window() -> None:
    with pytest.raises(ValueError, match="time window"):
        assert_rule_ak_algorithm_constraint(similarity_threshold=0.75, time_window_hours=0)


@pytest.mark.asyncio
async def test_rule_ak_enforces_similarity_and_time_window_together(db_session) -> None:
    user_id = uuid4()
    base = datetime(2026, 4, 19, 9, 0, 0)
    high_similarity_far = make_memory(
        user_id=user_id,
        summary="高相似但超时窗",
        occurred_at=base + timedelta(hours=80),
        embedding=[0.95, 0.05, 0.0],
    )
    low_similarity_near = make_memory(
        user_id=user_id,
        summary="近时间但低相似",
        occurred_at=base + timedelta(hours=1),
        embedding=[0.0, 1.0, 0.0],
    )
    seed = make_memory(
        user_id=user_id,
        summary="种子记忆",
        occurred_at=base,
        embedding=[0.95, 0.05, 0.0],
    )
    db_session.add_all([seed, high_similarity_far, low_similarity_near])
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")
    service = SceneConsolidationService(db_session, similarity_threshold=0.75, time_window_hours=72)

    await service.consolidate_memory(seed)
    await service.consolidate_memory(high_similarity_far)
    await service.consolidate_memory(low_similarity_near)

    rows = (await db_session.execute(select(Scene))).scalars().all()
    assert len(rows) == 3
