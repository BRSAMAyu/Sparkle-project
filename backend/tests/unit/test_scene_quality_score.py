from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.services.aurora_stage26_scene_kill_switch_service import AuroraStage26SceneKillSwitchService
from app.services.scene_consolidation_service import SceneConsolidationService
from tests.unit.scene_test_helpers import make_scene


def test_quality_score_rewards_cohesive_three_member_scene(db_session) -> None:
    service = SceneConsolidationService(db_session)

    score = service._score_scene(
        embeddings=[[0.9, 0.1], [0.88, 0.12], [0.91, 0.09]],
        centroid=[0.896, 0.104],
        time_start=datetime(2026, 4, 19, 9, 0, 0),
        time_end=datetime(2026, 4, 19, 12, 0, 0),
    )

    assert score >= 0.65


def test_quality_score_penalizes_small_member_count(db_session) -> None:
    service = SceneConsolidationService(db_session)

    one_member = service._score_scene(
        embeddings=[[0.9, 0.1]],
        centroid=[0.9, 0.1],
        time_start=datetime(2026, 4, 19, 9, 0, 0),
        time_end=datetime(2026, 4, 19, 10, 0, 0),
    )
    three_member = service._score_scene(
        embeddings=[[0.9, 0.1], [0.88, 0.12], [0.91, 0.09]],
        centroid=[0.896, 0.104],
        time_start=datetime(2026, 4, 19, 9, 0, 0),
        time_end=datetime(2026, 4, 19, 10, 0, 0),
    )

    assert one_member < three_member


def test_quality_score_penalizes_low_cohesion(db_session) -> None:
    service = SceneConsolidationService(db_session)

    low = service._score_scene(
        embeddings=[[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]],
        centroid=[0.5, 0.5],
        time_start=datetime(2026, 4, 19, 9, 0, 0),
        time_end=datetime(2026, 4, 19, 12, 0, 0),
    )
    high = service._score_scene(
        embeddings=[[0.9, 0.1], [0.88, 0.12], [0.91, 0.09]],
        centroid=[0.896, 0.104],
        time_start=datetime(2026, 4, 19, 9, 0, 0),
        time_end=datetime(2026, 4, 19, 12, 0, 0),
    )

    assert low < high


def test_quality_score_penalizes_too_short_span(db_session) -> None:
    service = SceneConsolidationService(db_session)

    short = service._score_scene(
        embeddings=[[0.9, 0.1], [0.88, 0.12], [0.91, 0.09]],
        centroid=[0.896, 0.104],
        time_start=datetime(2026, 4, 19, 9, 0, 0),
        time_end=datetime(2026, 4, 19, 9, 5, 0),
    )
    reasonable = service._score_scene(
        embeddings=[[0.9, 0.1], [0.88, 0.12], [0.91, 0.09]],
        centroid=[0.896, 0.104],
        time_start=datetime(2026, 4, 19, 9, 0, 0),
        time_end=datetime(2026, 4, 19, 11, 0, 0),
    )

    assert short < reasonable


def test_quality_score_penalizes_too_long_span(db_session) -> None:
    service = SceneConsolidationService(db_session)

    long = service._score_scene(
        embeddings=[[0.9, 0.1], [0.88, 0.12], [0.91, 0.09]],
        centroid=[0.896, 0.104],
        time_start=datetime(2026, 4, 19, 9, 0, 0),
        time_end=datetime(2026, 4, 23, 12, 0, 0),
    )
    reasonable = service._score_scene(
        embeddings=[[0.9, 0.1], [0.88, 0.12], [0.91, 0.09]],
        centroid=[0.896, 0.104],
        time_start=datetime(2026, 4, 19, 9, 0, 0),
        time_end=datetime(2026, 4, 20, 12, 0, 0),
    )

    assert long < reasonable


@pytest.mark.asyncio
async def test_recent_scene_filter_uses_quality_threshold(db_session) -> None:
    user_id = uuid4()
    high = make_scene(user_id=user_id, member_memory_ids=[str(uuid4())], quality_score=0.8)
    low = make_scene(
        user_id=user_id,
        member_memory_ids=[str(uuid4())],
        quality_score=0.4,
        time_start=datetime(2026, 4, 19, 9, 0, 0) + timedelta(hours=2),
        time_end=datetime(2026, 4, 19, 10, 0, 0) + timedelta(hours=2),
    )
    db_session.add_all([high, low])
    await db_session.commit()
    await AuroraStage26SceneKillSwitchService().set_mode("live")

    items = await SceneConsolidationService(db_session).list_recent_scenes_for_aggregator(
        user_id=user_id,
        now=datetime(2026, 4, 21, 9, 0, 0),
    )

    assert [item.scene_id for item in items] == [high.scene_id]
