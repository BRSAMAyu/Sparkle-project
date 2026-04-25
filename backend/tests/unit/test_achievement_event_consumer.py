from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.achievement import UserStreakStats
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.notification import Notification
from app.models.plan import Plan, PlanType
from app.models.subject import Subject
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
    assert notification.data["destination_route"].startswith("/achievements/milestone/30_day_learner")
    assert notification.data["deep_link"].startswith("sparkle://milestone/30_day_learner")

    stored = await db_session.execute(select(Notification).where(Notification.id == notification.id))
    assert stored.scalar_one().title == "你已经坚持学习 30 天了"
