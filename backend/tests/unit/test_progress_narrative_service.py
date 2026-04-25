from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.achievement import Achievement, AchievementRarity, AchievementType, UserAchievement, UserStreakStats
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, StudyRecord
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_feedback import TaskFeedback
from app.models.user import User
from app.services.progress_narrative_service import ProgressNarrativeService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_progress_snapshot_includes_task_and_streak_highlights(db_session):
    user_id = uuid4()
    now = _utcnow()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    task = Task(
        id=uuid4(),
        user_id=user_id,
        title="高数复习",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=30,
        actual_minutes=35,
        difficulty=3,
        energy_cost=2,
        tags=[],
        completed_at=now - timedelta(days=1),
    )
    study = StudyRecord(
        id=uuid4(),
        user_id=user_id,
        node_id=uuid4(),
        task_id=task.id,
        study_minutes=35,
        mastery_delta=12.0,
        record_type="task_complete",
    )
    streak = UserStreakStats(
        user_id=user_id,
        current_streak=12,
        max_streak=12,
        total_checkin_days=30,
    )
    db_session.add_all([user, task, study, streak])
    await db_session.commit()

    service = ProgressNarrativeService(db_session, redis=None)
    snapshot = await service.build_snapshot(str(user_id))

    assert snapshot.highlights
    assert snapshot.comparisons["tasks_completed"]["current"] == 1
    assert snapshot.streak_info["current_streak"] == 12


@pytest.mark.asyncio
async def test_progress_snapshot_uses_achievement_context_story(db_session):
    user_id = uuid4()
    now = _utcnow()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    achievement = Achievement(
        id="streak_7",
        name="连续7天学习",
        description="连续学习7天",
        type=AchievementType.STREAK,
        rarity=AchievementRarity.RARE,
        trigger_code="STREAK_DAYS",
        trigger_config={"days": 7},
        total_unlocked=1,
    )
    user_achievement = UserAchievement(
        user_id=user_id,
        achievement_id=achievement.id,
        progress=1.0,
        progress_value=7,
        progress_target=7,
        unlocked_at=now - timedelta(days=1),
        is_first_unlocker=True,
        context_snapshot={
            "story": "2026年3月10日，在「考前冲刺」目标日前 5 天，完成了 7 天连续学习，解锁了「连续7天学习」。",
            "is_first_unlocker": True,
            "current_plan": {"name": "考前冲刺", "days_to_target": 5},
            "task": {"title": "导数专项练习"},
        },
    )
    db_session.add_all([user, achievement, user_achievement])
    await db_session.commit()

    service = ProgressNarrativeService(db_session, redis=None)
    snapshot = await service.build_snapshot(str(user_id))

    assert any("这周你解锁了「连续7天学习」" in item for item in snapshot.highlights)
    assert any("这是你第一次做到" in item for item in snapshot.highlights)


@pytest.mark.asyncio
async def test_weekly_growth_narrative_uses_tasks_errors_reflections_and_mastery(db_session):
    user_id = uuid4()
    now = _utcnow()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    node = KnowledgeNode(
        id=uuid4(),
        name="热力学第一定律",
        importance_level=3,
    )
    task = Task(
        id=uuid4(),
        user_id=user_id,
        title="热力学费曼复述",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=35,
        actual_minutes=42,
        difficulty=3,
        energy_cost=2,
        tags=["热力学"],
        completed_at=now - timedelta(days=1),
        created_at=now - timedelta(days=1),
    )
    study = StudyRecord(
        id=uuid4(),
        user_id=user_id,
        node_id=node.id,
        task_id=task.id,
        study_minutes=42,
        mastery_delta=18.5,
        initial_mastery=40,
        record_type="task_complete",
        created_at=now - timedelta(days=1),
    )
    error = ErrorRecord(
        id=uuid4(),
        user_id=user_id,
        subject_code="physics",
        chapter="热力学",
        question_text="内能变化题",
        latest_analysis={"root_cause": "概念混淆"},
        mastery_level=0.2,
        created_at=now - timedelta(days=1),
        is_deleted=False,
    )
    feedback = TaskFeedback(
        id=uuid4(),
        user_id=user_id,
        task_id=task.id,
        completion_quality=4,
        category="too_difficult",
        feedback_text="最后讲给自己听才顺了",
        reflection_payload={
            "selected_option": "换一种解释方式",
            "free_text": "费曼法把概念讲清楚了",
            "submitted_at": now.isoformat(),
            "status": "completed",
        },
        created_at=now - timedelta(days=1),
    )
    db_session.add_all([user, node, task, study, error, feedback])
    await db_session.commit()

    service = ProgressNarrativeService(db_session, redis=None)
    narrative = await service.build_weekly_narrative(str(user_id), generated_at=now)

    assert narrative.is_placeholder is False
    assert narrative.data_points["tasks_completed"] == 1
    assert narrative.data_points["error_records"] == 1
    assert narrative.data_points["reflection_records"] == 1
    assert narrative.data_points["mastery_delta"] == 18.5
    assert "热力学" in narrative.body
    assert "概念混淆" in narrative.body
    assert "费曼法" in narrative.body


@pytest.mark.asyncio
async def test_weekly_growth_narrative_returns_first_week_placeholder(db_session):
    user_id = uuid4()
    now = _utcnow()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    await db_session.commit()

    service = ProgressNarrativeService(db_session, redis=None)
    narrative = await service.build_weekly_narrative(user_id, generated_at=now)

    assert narrative.is_placeholder is True
    assert "这是你的第一周，先开始吧" in narrative.body
    assert narrative.source_counts == {
        "task_completions": 0,
        "error_records": 0,
        "reflection_records": 0,
        "mastery_changes": 0,
        "achievement_unlocks": 0,
    }
