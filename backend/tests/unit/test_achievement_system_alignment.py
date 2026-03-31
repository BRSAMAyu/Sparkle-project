from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.data.achievement_seeds import INITIAL_ACHIEVEMENTS, INITIAL_GALAXY_SKINS
from app.data.populate_achievements import (
    SUPPORTED_REWARD_TYPES,
    sync_achievement_definitions,
    validate_achievement_seed_data,
)
from app.models.achievement import Achievement, AchievementType, GalaxySkin, UserAchievement
from app.models.achievement import VisualEffectType
from app.models.file_storage import StoredFile  # noqa: F401
from app.models.focus import FocusSession, FocusStatus, FocusType
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.subject import Subject
from app.models.task import Task, TaskStatus, TaskType
from app.services.achievement_engine import AchievementEngine, AchievementEvent


def _seed_by_id(achievement_id: str) -> dict:
    return next(seed for seed in INITIAL_ACHIEVEMENTS if seed["id"] == achievement_id)


async def _sync_definitions(db_session) -> None:
    await sync_achievement_definitions(db_session)


async def _create_subject(db_session, sector_code: str, suffix: str) -> Subject:
    subject = Subject(
        name=f"{sector_code}-{suffix}",
        sector_code=sector_code,
        category="test",
    )
    db_session.add(subject)
    await db_session.flush()
    return subject


async def _create_node_status(db_session, user_id, subject: Subject, **status_overrides) -> UserNodeStatus:
    node = KnowledgeNode(
        name=f"node-{uuid4()}",
        subject_id=subject.id,
    )
    db_session.add(node)
    await db_session.flush()

    status = UserNodeStatus(
        user_id=user_id,
        node_id=node.id,
        **status_overrides,
    )
    db_session.add(status)
    await db_session.flush()
    return status


@pytest.mark.asyncio
async def test_seed_trigger_codes_are_supported():
    trigger_codes = {seed["trigger_code"] for seed in INITIAL_ACHIEVEMENTS}
    assert trigger_codes <= AchievementEngine.SUPPORTED_TRIGGER_CODES


@pytest.mark.asyncio
async def test_seed_reward_types_are_supported_and_skin_refs_valid():
    reward_types = {
        reward["type"]
        for seed in INITIAL_ACHIEVEMENTS
        for reward in seed.get("reward_config", [])
    }
    assert reward_types <= SUPPORTED_REWARD_TYPES
    validate_achievement_seed_data()

    skin_ids = {skin["id"] for skin in INITIAL_GALAXY_SKINS}
    referenced_skin_ids = {
        reward["skin_id"]
        for seed in INITIAL_ACHIEVEMENTS
        for reward in seed.get("reward_config", [])
        if reward.get("type") == "galaxy_skin"
    }
    assert referenced_skin_ids <= skin_ids


@pytest.mark.asyncio
async def test_seed_ids_and_prerequisites_are_consistent():
    achievement_ids = [seed["id"] for seed in INITIAL_ACHIEVEMENTS]
    assert len(achievement_ids) == len(set(achievement_ids))

    skin_ids = [skin["id"] for skin in INITIAL_GALAXY_SKINS]
    assert len(skin_ids) == len(set(skin_ids))

    id_set = set(achievement_ids)
    missing_prereqs = [
        (seed["id"], prereq)
        for seed in INITIAL_ACHIEVEMENTS
        for prereq in (seed.get("prerequisites") or [])
        if prereq not in id_set
    ]
    assert missing_prereqs == []


@pytest.mark.asyncio
async def test_sync_achievement_definitions_inserts_and_updates_existing_records(db_session, test_user):
    existing_achievement = Achievement(
        id="nodes_10",
        name="stale",
        type=AchievementType.NODE_EXPLORE,
        trigger_code="OLD_CODE",
        total_unlocked=7,
        first_unlocker_id=test_user.id,
    )
    existing_skin = GalaxySkin(
        id="default",
        name="stale",
        unlock_type="default",
        skin_config={},
        sort_order=999,
    )
    db_session.add(existing_achievement)
    db_session.add(existing_skin)
    await db_session.commit()

    synced_achievements, synced_skins = await sync_achievement_definitions(db_session)

    assert synced_achievements == len(INITIAL_ACHIEVEMENTS)
    assert synced_skins == len(INITIAL_GALAXY_SKINS)

    refreshed_achievement = await db_session.get(Achievement, "nodes_10")
    refreshed_skin = await db_session.get(GalaxySkin, "default")
    seed = _seed_by_id("nodes_10")

    assert refreshed_achievement.name == seed["name"]
    assert refreshed_achievement.trigger_code == seed["trigger_code"]
    assert refreshed_achievement.total_unlocked == 7
    assert refreshed_achievement.first_unlocker_id == test_user.id
    assert refreshed_skin.name == "经典星系"
    assert refreshed_skin.sort_order == 0


@pytest.mark.asyncio
async def test_sync_achievement_definitions_applies_model_defaults_for_optional_fields(db_session):
    await sync_achievement_definitions(db_session)

    first_light = await db_session.get(Achievement, "first_light")
    math_master = await db_session.get(Achievement, "math_master")

    assert first_light is not None
    assert math_master is not None
    assert first_light.is_hidden is False
    assert first_light.visual_effect_type == VisualEffectType.NONE
    assert math_master.is_hidden is False
    assert math_master.visual_effect_type == VisualEffectType.NONE


@pytest.mark.asyncio
async def test_early_bird_progress_updates_from_focus_event(db_session, test_user):
    await _sync_definitions(db_session)
    engine = AchievementEngine(db_session)

    unlocked = await engine.process_event(
        user_id=test_user.id,
        event_type=AchievementEvent.EARLY_BIRD,
        session_start_time=datetime(2026, 3, 10, 6, 30, 0),
    )

    assert unlocked == []
    result = await db_session.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == test_user.id,
            UserAchievement.achievement_id == "early_bird",
        )
    )
    progress = result.scalar_one_or_none()
    assert progress is not None
    assert progress.progress_value == 1
    assert progress.progress_target == 10
    assert progress.progress == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_speed_unlock_counts_recent_first_unlocks(db_session, test_user):
    await _sync_definitions(db_session)
    subject = await _create_subject(db_session, "math", "speed")
    now = datetime.utcnow()

    for _ in range(20):
        await _create_node_status(
            db_session,
            test_user.id,
            subject,
            is_unlocked=True,
            first_unlock_at=now - timedelta(hours=1),
        )

    achievement = await db_session.get(Achievement, "speed_learner")
    engine = AchievementEngine(db_session)
    progress, current, target = await engine._evaluate_progress(test_user.id, achievement)

    assert current == 20
    assert target == 20
    assert progress == 1.0


@pytest.mark.asyncio
async def test_all_sectors_unlocked_counts_distinct_subject_sectors(db_session, test_user):
    await _sync_definitions(db_session)
    sectors = _seed_by_id("all_sectors")["trigger_config"]["sectors"]

    for index, sector in enumerate(sectors):
        subject = await _create_subject(db_session, sector, str(index))
        await _create_node_status(
            db_session,
            test_user.id,
            subject,
            is_unlocked=True,
            first_unlock_at=datetime.utcnow(),
        )

    achievement = await db_session.get(Achievement, "all_sectors")
    engine = AchievementEngine(db_session)
    progress, current, target = await engine._evaluate_progress(test_user.id, achievement)

    assert current == len(sectors)
    assert target == len(sectors)
    assert progress == 1.0


@pytest.mark.asyncio
async def test_weekend_warrior_uses_learning_history(db_session, test_user):
    await _sync_definitions(db_session)
    subject = await _create_subject(db_session, "math", "weekend")
    node = KnowledgeNode(name=f"weekend-node-{uuid4()}", subject_id=subject.id)
    db_session.add(node)
    await db_session.flush()

    db_session.add(
        FocusSession(
            user_id=test_user.id,
            start_time=datetime(2026, 2, 14, 9, 0, 0),
            end_time=datetime(2026, 2, 14, 9, 30, 0),
            duration_minutes=30,
            focus_type=FocusType.POMODORO,
            status=FocusStatus.COMPLETED,
        )
    )
    db_session.add(
        Task(
            user_id=test_user.id,
            title="weekend task",
            type=TaskType.LEARNING,
            tags=[],
            estimated_minutes=25,
            difficulty=1,
            energy_cost=1,
            status=TaskStatus.COMPLETED,
            priority=1,
            completed_at=datetime(2026, 2, 22, 11, 0, 0),
        )
    )
    db_session.add(
        StudyRecord(
            user_id=test_user.id,
            node_id=node.id,
            study_minutes=40,
            mastery_delta=5,
            created_at=datetime(2026, 2, 28, 14, 0, 0),
        )
    )
    db_session.add(
        StudyRecord(
            user_id=test_user.id,
            node_id=node.id,
            study_minutes=35,
            mastery_delta=4,
            created_at=datetime(2026, 3, 8, 10, 0, 0),
        )
    )
    await db_session.commit()

    achievement = await db_session.get(Achievement, "weekend_warrior")
    engine = AchievementEngine(db_session)
    progress, current, target = await engine._evaluate_progress(test_user.id, achievement)

    assert current == 4
    assert target == 4
    assert progress == 1.0


@pytest.mark.asyncio
async def test_close_to_unlock_returns_achievement_with_progress_shape(db_session, test_user):
    await _sync_definitions(db_session)
    subject = await _create_subject(db_session, "math", "close")
    now = datetime.utcnow()

    for _ in range(16):
        await _create_node_status(
            db_session,
            test_user.id,
            subject,
            is_unlocked=True,
            first_unlock_at=now - timedelta(hours=2),
        )

    engine = AchievementEngine(db_session)
    close_achievements = await engine.get_close_to_unlock_achievements(
        user_id=test_user.id,
        threshold=0.8,
        category="hidden",
    )

    speed_learner = next(item for item in close_achievements if item["achievement"]["id"] == "speed_learner")
    assert speed_learner["is_unlocked"] is False
    assert speed_learner["progress_percentage"] == 80
    assert speed_learner["user_progress"]["achievement_id"] == "speed_learner"
    assert speed_learner["user_progress"]["progress_value"] == 16


@pytest.mark.asyncio
async def test_close_to_unlock_excludes_db_unlocked_achievement_when_cache_is_stale(
    db_session,
    test_user,
):
    await _sync_definitions(db_session)
    subject = await _create_subject(db_session, "math", "close-unlocked")
    now = datetime.utcnow()

    for _ in range(16):
        await _create_node_status(
            db_session,
            test_user.id,
            subject,
            is_unlocked=True,
            first_unlock_at=now - timedelta(hours=2),
        )

    db_session.add(
        UserAchievement(
            user_id=test_user.id,
            achievement_id="speed_learner",
            progress=1.0,
            unlocked_at=now,
            last_progress_update=now,
        )
    )
    await db_session.commit()

    engine = AchievementEngine(db_session)
    engine._is_unlocked = AsyncMock(return_value=False)

    close_achievements = await engine.get_close_to_unlock_achievements(
        user_id=test_user.id,
        threshold=0.8,
        category="hidden",
    )

    assert all(
        item["achievement"]["id"] != "speed_learner"
        for item in close_achievements
    )
