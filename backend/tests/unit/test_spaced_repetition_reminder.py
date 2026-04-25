from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.celery_tasks import _run_spaced_repetition_reminders_for_user
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.notification import Notification
from app.services.notification_center_service import SPACED_REPETITION_NOTIFICATION_TYPE
from app.services.notification_service import NotificationService

pytestmark = pytest.mark.asyncio


async def _seed_node_status(
    db_session,
    user_id,
    *,
    mastery: float,
    days_ago: int,
    now: datetime,
    node_name: str = "子网划分",
) -> KnowledgeNode:
    last_updated_at = now - timedelta(days=days_ago)
    node = KnowledgeNode(name=node_name, description="networking basics")
    db_session.add(node)
    await db_session.flush()

    db_session.add(
        UserNodeStatus(
            user_id=user_id,
            node_id=node.id,
            mastery_score=mastery,
            bkt_mastery_prob=0.0,
            is_unlocked=True,
            last_interacted_at=last_updated_at,
            updated_at=last_updated_at,
        )
    )
    await db_session.commit()
    return node


async def _notifications_for(db_session, user_id) -> list[Notification]:
    result = await db_session.execute(
        select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at)
    )
    return list(result.scalars().all())


async def test_seven_day_mid_mastery_triggers_spaced_repetition_push(db_session, test_user, monkeypatch):
    monkeypatch.setattr(NotificationService, "_push_notification_via_websocket", AsyncMock())
    now = datetime.utcnow().replace(microsecond=0)
    node = await _seed_node_status(db_session, test_user.id, mastery=0.55, days_ago=7, now=now)

    result = await _run_spaced_repetition_reminders_for_user(db_session, str(test_user.id), now=now)

    assert result["sent"] == 1
    assert result["sent_node_ids"] == [str(node.id)]
    notifications = await _notifications_for(db_session, test_user.id)
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.type == SPACED_REPETITION_NOTIFICATION_TYPE
    assert "子网划分" in notification.content
    assert "7 天" in notification.content
    assert "10 分钟" in notification.content
    assert notification.data["node_id"] == str(node.id)
    assert notification.data["deep_link"] == f"/galaxy?nodeId={node.id}"
    assert notification.data["primary_action"]["label"] == "开始复习"


@pytest.mark.parametrize(
    ("mastery", "days_ago", "skipped_reason"),
    [
        (0.55, 2, "skipped_window"),
        (0.86, 7, "skipped_mastery"),
        (0.19, 7, "skipped_mastery"),
    ],
)
async def test_spaced_repetition_skips_non_due_or_out_of_band_mastery(
    db_session,
    test_user,
    monkeypatch,
    mastery,
    days_ago,
    skipped_reason,
):
    monkeypatch.setattr(NotificationService, "_push_notification_via_websocket", AsyncMock())
    now = datetime.utcnow().replace(microsecond=0)
    await _seed_node_status(db_session, test_user.id, mastery=mastery, days_ago=days_ago, now=now)

    result = await _run_spaced_repetition_reminders_for_user(db_session, str(test_user.id), now=now)

    assert result["sent"] == 0
    assert result[skipped_reason] == 1
    assert await _notifications_for(db_session, test_user.id) == []


async def test_spaced_repetition_enforces_per_node_minimum_push_interval(db_session, test_user, monkeypatch):
    monkeypatch.setattr(NotificationService, "_push_notification_via_websocket", AsyncMock())
    now = datetime.utcnow().replace(microsecond=0)
    await _seed_node_status(db_session, test_user.id, mastery=0.55, days_ago=7, now=now)

    first = await _run_spaced_repetition_reminders_for_user(db_session, str(test_user.id), now=now)
    second = await _run_spaced_repetition_reminders_for_user(db_session, str(test_user.id), now=now)

    assert first["sent"] == 1
    assert second["sent"] == 0
    assert second["skipped_duplicate"] == 1
    assert len(await _notifications_for(db_session, test_user.id)) == 1
