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


class _MemoryCache:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ttl=None):
        self.values[key] = value


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
        mastery_level=0.85,
        created_at=now - timedelta(days=1),
        last_reviewed_at=now - timedelta(days=1),
        review_count=2,
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
    narrative = await service.get_weekly_narrative(
        str(user_id),
        now - timedelta(days=now.weekday()),
        now - timedelta(days=now.weekday()) + timedelta(days=7),
        force=True,
        now=now,
    )

    assert narrative.is_placeholder is False
    assert narrative.data_points["tasks_completed"] == 1
    assert narrative.data_points["error_records"] == 1
    assert narrative.data_points["errors_fixed"] == 1
    assert narrative.data_points["reflection_records"] == 1
    assert narrative.data_points["mastery_delta"] == 18.5
    assert narrative.highlights
    assert narrative.biggest_improvement is not None
    assert narrative.biggest_improvement["node_name"] == "热力学第一定律"
    assert narrative.next_week_suggestion
    assert "热力学" in narrative.body
    assert narrative.data_points["error_causes"] == ["概念混淆"]
    assert "掌握度从 40% 提升到了 58%" in narrative.body


@pytest.mark.asyncio
async def test_weekly_growth_narrative_varies_against_recent_cached_weeks(db_session):
    user_id = uuid4()
    base = datetime(2026, 4, 6, 10, 0, tzinfo=UTC).replace(tzinfo=None)
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    node = KnowledgeNode(
        id=uuid4(),
        name="网络层路由",
        importance_level=3,
    )
    db_session.add_all([user, node])
    for week_offset in (0, 7):
        completed_at = base + timedelta(days=week_offset + 1)
        task = Task(
            id=uuid4(),
            user_id=user_id,
            title="网络层错题复盘",
            type=TaskType.LEARNING,
            status=TaskStatus.COMPLETED,
            estimated_minutes=30,
            actual_minutes=30,
            difficulty=3,
            energy_cost=2,
            tags=["网络层"],
            completed_at=completed_at,
            created_at=completed_at,
        )
        study = StudyRecord(
            id=uuid4(),
            user_id=user_id,
            node_id=node.id,
            task_id=task.id,
            study_minutes=30,
            mastery_delta=10.0,
            initial_mastery=40,
            record_type="task_complete",
            created_at=completed_at,
        )
        db_session.add_all([task, study])
    await db_session.commit()

    cache = _MemoryCache()
    service = ProgressNarrativeService(db_session, redis=None, cache=cache)
    first = await service.get_weekly_narrative(
        user_id,
        base,
        base + timedelta(days=7),
        force=True,
        now=base + timedelta(days=5),
    )
    second = await service.get_weekly_narrative(
        user_id,
        base + timedelta(days=7),
        base + timedelta(days=14),
        force=True,
        now=base + timedelta(days=12),
    )

    assert second.data_points["recent_narrative_count"] == 1
    assert second.data_points["style_variant"] != first.data_points["style_variant"]
    assert second.sentences[0] != first.sentences[0]
    assert not set(first.sentences).intersection(second.sentences)


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
    assert narrative.highlights == ["开始留下第一条成长线索。"]
    assert narrative.source_counts == {
        "task_completions": 0,
        "error_records": 0,
        "error_review_records": 0,
        "reflection_records": 0,
        "mastery_changes": 0,
        "achievement_unlocks": 0,
        "study_days": 0,
    }


@pytest.mark.asyncio
async def test_weekly_growth_narrative_returns_gentle_pause_when_no_study_days(db_session):
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
        title="整理下周学习清单",
        type=TaskType.PLANNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=15,
        actual_minutes=15,
        difficulty=1,
        energy_cost=1,
        tags=["网络层"],
        completed_at=now - timedelta(days=1),
        created_at=now - timedelta(days=1),
    )
    db_session.add_all([user, task])
    await db_session.commit()

    service = ProgressNarrativeService(db_session, redis=None)
    narrative = await service.build_weekly_narrative(user_id, generated_at=now)

    assert narrative.is_placeholder is True
    assert narrative.data_points["study_days"] == 0
    assert narrative.highlights == ["本周暂停学习，下周继续。"]
    assert "本周暂停学习，下周继续" in narrative.body
