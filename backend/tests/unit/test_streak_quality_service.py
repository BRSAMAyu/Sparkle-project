from datetime import date, datetime, timedelta

import pytest

from app.models.achievement import StreakDayStatus, UserStreakDay, UserStreakStats
from app.models.galaxy import KnowledgeNode, StudyRecord
from app.models.task import Task, TaskStatus, TaskType
from app.services.streak_quality import StreakQualityService


@pytest.mark.asyncio
async def test_compute_quality_counts_real_learning_signals(db_session, test_user):
    target_day = date(2026, 5, 2)
    node = KnowledgeNode(name="Derivatives")
    db_session.add(node)
    await db_session.flush()

    db_session.add_all(
        [
            UserStreakStats(
                user_id=test_user.id,
                current_streak=5,
                max_streak=5,
                longest_streak=5,
                total_checkin_days=8,
            ),
            StudyRecord(
                user_id=test_user.id,
                node_id=node.id,
                study_minutes=70,
                mastery_delta=0.2,
                created_at=datetime(2026, 5, 2, 9, 0),
            ),
            Task(
                user_id=test_user.id,
                title="Core calculus drill",
                type=TaskType.TRAINING,
                estimated_minutes=45,
                difficulty=4,
                priority=3,
                due_date=target_day,
                status=TaskStatus.COMPLETED,
                completed_at=datetime(2026, 5, 2, 10, 0),
            ),
            Task(
                user_id=test_user.id,
                title="Light reading",
                type=TaskType.LEARNING,
                estimated_minutes=15,
                difficulty=1,
                priority=0,
                due_date=target_day,
                status=TaskStatus.PENDING,
            ),
            UserStreakDay(
                user_id=test_user.id,
                day=target_day - timedelta(days=1),
                status=StreakDayStatus.MISSED,
            ),
            UserStreakDay(
                user_id=test_user.id,
                day=target_day,
                status=StreakDayStatus.ACTIVE,
            ),
        ]
    )
    await db_session.commit()

    quality = await StreakQualityService(db_session).compute_quality(test_user.id, target_day)

    assert quality.effective_minutes == 70
    assert quality.core_tasks_completed == 1
    assert quality.difficult_breakthroughs == 2
    assert quality.plan_consistency == 0.5
    assert quality.recovery_score == 0.5
    assert quality.is_quality_day is True


@pytest.mark.asyncio
async def test_build_payload_includes_quality_trend_and_evidence(db_session, test_user):
    today = datetime.utcnow().date()
    node = KnowledgeNode(name="Vectors")
    db_session.add(node)
    await db_session.flush()
    db_session.add_all(
        [
            UserStreakStats(user_id=test_user.id, current_streak=1, max_streak=1),
            StudyRecord(
                user_id=test_user.id,
                node_id=node.id,
                study_minutes=95,
                mastery_delta=0.2,
                created_at=datetime.combine(today, datetime.min.time()),
            ),
            UserStreakDay(user_id=test_user.id, day=today, status=StreakDayStatus.ACTIVE),
        ]
    )
    await db_session.commit()

    payload = await StreakQualityService(db_session).build_payload(test_user.id)

    assert payload["current_streak"] == 1
    assert payload["quality_streak"] == 1
    assert len(payload["weekly_quality_trend"]) == 7
    assert payload["today_quality"]["is_quality_day"] is True
    assert payload["celebration_trigger"]["evidence"]
