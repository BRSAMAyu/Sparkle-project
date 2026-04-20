from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.notification import Notification
from app.models.push_delivery_record import PushDeliveryRecord
from app.models.user import User
from app.models.user_push_opt_in import UserPushOptIn
from app.services.push_delivery_service import PushDeliveryService
from app.services.push_policy_compiler import PushDecision


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_push_delivery_service_counts_only_recent_unretracted_records(db_session) -> None:
    user = User(
        id=uuid4(),
        username="push_count_user",
        email="push-count@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    db_session.add_all(
        [
            PushDeliveryRecord(
                user_id=user.id,
                policy_id="CommitmentFollowUp",
                category="commitment_follow_up",
                message_template_id="commitment_follow_up_gentle",
                title="title",
                body="body",
                evidence_token="commitment:1",
                scheduled_send_at=_utcnow() - timedelta(hours=1),
                sent_at=_utcnow() - timedelta(hours=1),
            ),
            PushDeliveryRecord(
                user_id=user.id,
                policy_id="CommitmentFollowUp",
                category="commitment_follow_up",
                message_template_id="commitment_follow_up_gentle",
                title="title",
                body="body",
                evidence_token="commitment:2",
                scheduled_send_at=_utcnow() - timedelta(hours=2),
                sent_at=_utcnow() - timedelta(hours=2),
                retracted_at=_utcnow() - timedelta(minutes=30),
            ),
            PushDeliveryRecord(
                user_id=user.id,
                policy_id="EngagementRecovery",
                category="engagement_recovery",
                message_template_id="engagement_recovery_soft",
                title="title",
                body="body",
                evidence_token="engagement:1",
                scheduled_send_at=_utcnow() - timedelta(days=2),
                sent_at=_utcnow() - timedelta(days=2),
            ),
        ]
    )
    await db_session.commit()

    service = PushDeliveryService(db_session)
    count = await service.recent_delivery_count_24h(user.id, now=_utcnow())

    assert count == 1


@pytest.mark.asyncio
async def test_push_delivery_service_disable_category_updates_record_and_opt_in(db_session, monkeypatch) -> None:
    del monkeypatch
    user = User(
        id=uuid4(),
        username="push_disable_user",
        email="push-disable@example.com",
        hashed_password="test",
    )
    notification = Notification(
        user_id=user.id,
        title="主动提醒",
        content="你之前答应过的事情还没收尾",
        type="aurora_push",
        data={},
    )
    opt_in = UserPushOptIn(
        user_id=user.id,
        enabled=True,
        allow_commitment_follow_up=True,
        allow_engagement_recovery=True,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
        timezone="Asia/Shanghai",
    )
    record = PushDeliveryRecord(
        user_id=user.id,
        notification=notification,
        policy_id="CommitmentFollowUp",
        category="commitment_follow_up",
        message_template_id="commitment_follow_up_gentle",
        title="主动提醒",
        body="你之前答应过的事情还没收尾",
        evidence_token="commitment:abc",
        scheduled_send_at=_utcnow(),
        sent_at=_utcnow(),
    )
    db_session.add_all([user, notification, opt_in, record])
    await db_session.commit()

    service = PushDeliveryService(db_session)
    updated = await service.apply_action(
        user_id=user.id,
        notification_id=notification.id,
        action="disable_category",
    )

    await db_session.refresh(opt_in)
    await db_session.refresh(notification)

    assert updated is not None
    assert updated.category_disabled is True
    assert updated.deleted_at is not None
    assert opt_in.allow_commitment_follow_up is False
    assert notification.deleted_at is not None


@pytest.mark.asyncio
async def test_push_delivery_service_respects_delivery_guards(db_session, monkeypatch) -> None:
    user = User(
        id=uuid4(),
        username="push_guard_user",
        email="push-guard@example.com",
        hashed_password="test",
    )
    opt_in = UserPushOptIn(
        user_id=user.id,
        enabled=True,
        allow_commitment_follow_up=True,
        allow_engagement_recovery=False,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
        timezone="Asia/Shanghai",
    )
    db_session.add_all([user, opt_in])
    await db_session.commit()

    service = PushDeliveryService(db_session)
    monkeypatch.setattr(service.kill_switches, "is_enabled", AsyncMock(return_value=True))

    decision = PushDecision(
        policy_id="CommitmentFollowUp",
        category="commitment_follow_up",
        evidence_token="commitment:guard",
        message_template_id="commitment_follow_up_gentle",
        scheduled_send_at=_utcnow() + timedelta(hours=1),
        title="主动提醒",
        body="body",
        metadata={},
    )

    delivered = await service.deliver_decision(user_id=user.id, decision=decision)
    assert delivered is None
