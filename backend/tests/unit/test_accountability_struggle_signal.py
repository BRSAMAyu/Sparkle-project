from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.api.v1.accountability import StruggleEncouragementRequest, encourage_from_struggle_alert
from app.core.event_types import ACCOUNTABILITY_STRUGGLE_DETECTED
from app.models.accountability import AccountabilityPartnership, AccountabilityStatus
from app.models.notification import Notification
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.accountability_notification_service import AccountabilityNotificationType
from app.services.social_signal_bridge import SocialSignalBridge
from app.services.struggle_signal_aggregator import StruggleSignalAggregator


async def _create_user(db_session, *, name: str) -> User:
    user = User(
        id=uuid4(),
        username=name,
        email=f"{name}@example.com",
        hashed_password="test",
        nickname=name,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _create_plan(db_session, user: User) -> Plan:
    plan = Plan(
        id=uuid4(),
        user_id=user.id,
        name=f"{user.username} plan",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.flush()
    return plan


async def _create_active_partnership(db_session, user: User, partner: User) -> AccountabilityPartnership:
    partnership = AccountabilityPartnership(
        id=uuid4(),
        initiator_id=user.id,
        partner_id=partner.id,
        initiator_goal="每天完成学习任务",
        partner_goal="轻量监督",
        status=AccountabilityStatus.ACTIVE,
        started_at=datetime.utcnow() - timedelta(days=3),
    )
    db_session.add(partnership)
    await db_session.flush()
    return partnership


@pytest.mark.asyncio
async def test_two_days_without_completed_plan_task_crosses_struggle_threshold(db_session) -> None:
    user = await _create_user(db_session, name="xiaoming")
    plan = await _create_plan(db_session, user)
    db_session.add(
        Task(
            id=uuid4(),
            user_id=user.id,
            plan_id=plan.id,
            title="pending for two days",
            type=TaskType.LEARNING,
            status=TaskStatus.PENDING,
            estimated_minutes=20,
            difficulty=2,
            energy_cost=2,
            created_at=datetime.utcnow() - timedelta(days=2, hours=1),
            updated_at=datetime.utcnow() - timedelta(days=2, hours=1),
        )
    )
    await db_session.commit()

    context = await StruggleSignalAggregator().get_struggle_context(
        db_session,
        user_id=str(user.id),
        plan_id=str(plan.id),
    )

    assert context["no_completion_days"] >= 2
    assert context["primary_signal"] == "completion_gap"
    assert context["struggle_score"] >= 0.6


@pytest.mark.asyncio
async def test_social_bridge_publishes_struggle_event_for_active_partner(db_session, monkeypatch) -> None:
    user = await _create_user(db_session, name="xiaoming_signal")
    partner = await _create_user(db_session, name="study_partner")
    plan = await _create_plan(db_session, user)
    partnership = await _create_active_partnership(db_session, user, partner)
    await db_session.commit()

    publish = AsyncMock(return_value="1-0")
    monkeypatch.setattr("app.services.social_signal_bridge.event_bus.publish", publish)

    result = await SocialSignalBridge(db_session).maybe_publish_accountability_struggle_signal(
        user_id=user.id,
        plan_id=plan.id,
        struggle_context={
            "struggle_score": 0.62,
            "primary_signal": "completion_gap",
            "no_completion_days": 2,
            "recent_completion_count": 0,
        },
    )

    assert result["published"] is True
    publish.assert_awaited_once()
    event_type, payload = publish.await_args.args
    assert event_type == ACCOUNTABILITY_STRUGGLE_DETECTED
    assert payload["user_id"] == str(user.id)
    assert payload["partnerships"] == [{"partnership_id": str(partnership.id), "partner_id": str(partner.id)}]


@pytest.mark.asyncio
async def test_one_tap_encouragement_creates_non_push_in_app_hint(db_session, monkeypatch) -> None:
    user = await _create_user(db_session, name="xiaoming_encouraged")
    partner = await _create_user(db_session, name="lena_partner")
    plan = await _create_plan(db_session, user)
    partnership = await _create_active_partnership(db_session, user, partner)
    await db_session.commit()

    await SocialSignalBridge(db_session).handle_accountability_struggle_detected(
        {
            "event_type": ACCOUNTABILITY_STRUGGLE_DETECTED,
            "user_id": str(user.id),
            "plan_id": str(plan.id),
            "target_name": "小明",
            "struggle_score": 0.64,
            "no_completion_days": 2,
            "dedupe_key": "test-dedupe-key",
        }
    )

    alert = (
        await db_session.execute(
            select(Notification).where(
                Notification.user_id == partner.id,
                Notification.type == AccountabilityNotificationType.STRUGGLE_ALERT.value,
            )
        )
    ).scalar_one()

    monkeypatch.setattr("app.api.v1.accountability.event_bus.publish", AsyncMock(return_value="1-0"))
    response = await encourage_from_struggle_alert(
        notification_id=alert.id,
        body=StruggleEncouragementRequest(preset_id="spark_small_step"),
        db=db_session,
        current_user=partner,
    )

    assert response["message"] == "他收到了你的鼓励"
    hint = (
        await db_session.execute(
            select(Notification).where(
                Notification.user_id == user.id,
                Notification.type == AccountabilityNotificationType.ENCOURAGEMENT_RECEIVED.value,
            )
        )
    ).scalar_one()
    assert hint.content == "lena_partner 正在看着你，加油"
    assert hint.is_read is False
    assert hint.data["display_mode"] == "weak_in_app_hint"

    await db_session.refresh(alert)
    assert alert.data["encouragement_status"] == "sent"
    assert alert.is_read is True
