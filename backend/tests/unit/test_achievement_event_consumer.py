from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.achievement import (
    Achievement,
    AchievementRarity,
    AchievementType,
    ContractStatus,
    SparkContract,
    UserAchievement,
    UserStreakStats,
)
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.notification import Notification
from app.models.plan import Plan, PlanType
from app.models.subject import Subject
from app.services.achievement_engine import ContractService
from app.services.achievement_event_consumer import AchievementEventConsumer


@pytest.mark.asyncio
async def test_milestone_notification_contains_personalized_numbers(db_session, test_user):
    subject = Subject(name="milestone-math", sector_code="math", category="test")
    db_session.add(subject)
    await db_session.flush()

    for index in range(67):
        node = KnowledgeNode(name=f"node-{index}", subject_id=subject.id)
        db_session.add(node)
        await db_session.flush()
        db_session.add(
            UserNodeStatus(
                user_id=test_user.id,
                node_id=node.id,
                is_unlocked=True,
                mastery_score=42.0,
            )
        )

    for index in range(2):
        plan = Plan(
            user_id=test_user.id,
            name=f"sprint-{index}",
            type=PlanType.SPRINT,
            is_active=False,
            progress=1.0,
        )
        plan.updated_at = datetime.utcnow() - timedelta(days=index)
        db_session.add(plan)

    for index in range(23):
        db_session.add(
            ErrorRecord(
                user_id=test_user.id,
                subject_code="math",
                question_text=f"错题 {index}",
                is_deleted=False,
            )
        )

    db_session.add(
        UserStreakStats(
            user_id=test_user.id,
            total_checkin_days=30,
            current_streak=9,
            max_streak=12,
        )
    )
    await db_session.commit()

    consumer = AchievementEventConsumer(event_bus=AsyncMock())

    with patch(
        "app.services.notification_service.NotificationService._push_notification_via_websocket",
        new=AsyncMock(),
    ):
        notification = await consumer._maybe_create_milestone_notification(
            db=db_session,
            user_id=test_user.id,
            event={
                "achievement_id": "30_day_learner",
                "achievement_name": "30 天学习者",
            },
        )

    assert notification is not None
    assert notification.type == "milestone_notification"
    assert "67 个知识节点" in notification.content
    assert "23 道错题" in notification.content
    assert notification.data["study_days"] == 30
    assert notification.data["mastered_nodes"] == 67
    assert notification.data["completed_sprints"] == 2
    assert notification.data["error_count"] == 23
    assert notification.data["share_hashtag"] == "#30天打卡"
    assert notification.data["celebration_value"] == 30
    assert notification.data["destination_route"].startswith("/achievements/milestone/30_day_learner")
    assert "study_days=30" in notification.data["destination_route"]
    assert "mastered_nodes=67" in notification.data["destination_route"]
    assert notification.data["deep_link"].startswith("sparkle://milestone/30_day_learner")

    stored = await db_session.execute(select(Notification).where(Notification.id == notification.id))
    assert stored.scalar_one().title == "你已经坚持学习 30 天了"


@pytest.mark.asyncio
async def test_milestone_notification_skips_duplicates_within_24h(db_session, test_user):
    db_session.add(
        Notification(
            user_id=test_user.id,
            title="你已经坚持学习 30 天了",
            content="这段时间你完成了 2 次冲刺备考。",
            type="milestone_notification",
            data={"achievement_id": "30_day_learner"},
        )
    )
    await db_session.commit()

    consumer = AchievementEventConsumer(event_bus=AsyncMock())

    notification = await consumer._maybe_create_milestone_notification(
        db=db_session,
        user_id=test_user.id,
        event={
            "achievement_id": "30_day_learner",
            "achievement_name": "30 天学习者",
        },
    )

    assert notification is None


@pytest.mark.asyncio
async def test_achievement_progress_event_creates_persistent_notification(db_session, test_user):
    consumer = AchievementEventConsumer(event_bus=AsyncMock())

    with patch(
        "app.services.notification_service.NotificationService._push_notification_via_websocket",
        new=AsyncMock(),
    ), patch(
        "app.services.notification_service.NotificationService._should_push_notification",
        new=AsyncMock(return_value=(True, None)),
    ):
        notification = await consumer._create_achievement_progress_notification(
            db=db_session,
            user_id=test_user.id,
            achievement_id="streak_7",
            achievement_name="连续学习 7 天",
            progress_percent=50,
        )

    assert notification is not None
    assert notification.type == "achievement_progress"
    assert notification.data["achievement_id"] == "streak_7"
    assert notification.data["progress_percent"] == 50

    stored = await db_session.execute(select(Notification).where(Notification.id == notification.id))
    assert stored.scalar_one().title == "连续学习 7 天 进度达到 50%"


@pytest.mark.asyncio
async def test_contract_completion_triggers_achievement_unlock(db_session, test_user):
    db_session.add(
        Achievement(
            id="contract_finish_first",
            name="契约兑现者",
            description="完成一次星火契约",
            type=AchievementType.CONTRACT,
            rarity=AchievementRarity.COMMON,
            trigger_code="CONTRACT_COMPLETED",
            trigger_config={"count": 1},
            category="contract",
        )
    )
    db_session.add(
        SparkContract(
            user_id=test_user.id,
            target_study_minutes=20,
            target_days=1,
            photon_stake=10,
            start_date=datetime.utcnow() - timedelta(days=2),
            end_date=datetime.utcnow() - timedelta(days=1),
            status=ContractStatus.ACTIVE,
            current_days=1,
            current_minutes=0,
        )
    )
    await db_session.commit()

    service = ContractService(db_session)
    with patch.object(service, "_grant_rewards", new=AsyncMock()), patch(
        "app.services.achievement_engine.AchievementEngine._notify_unlocks",
        new=AsyncMock(),
    ):
        result = await service.check_contract_status(str(test_user.id))

    assert result == {"status": "completed", "reward": 20.0}

    user_achievement_result = await db_session.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == test_user.id,
            UserAchievement.achievement_id == "contract_finish_first",
        )
    )
    user_achievement = user_achievement_result.scalar_one_or_none()
    assert user_achievement is not None
    assert user_achievement.unlocked_at is not None
