from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.accountability import AccountabilityCheckin, AccountabilityPartnership, AccountabilityStatus
from app.models.notification import Notification
from app.models.notification_interaction import NotificationPreferences
from app.models.user import PushPreference, User
from app.services.accountability_notification_service import (
    AccountabilityNotificationType,
    accountability_notification_service,
)
from app.services.policy_scheduler_service import PolicySchedulerService
from app.tasks.accountability_tasks import _send_daily_reminders


def _make_user(*, username: str, timezone_name: str = "Asia/Shanghai") -> User:
    suffix = uuid4().hex[:8]
    user = User(
        username=f"{username}_{suffix}",
        email=f"{username}_{suffix}@example.com",
        hashed_password="hashed",
        password_login_enabled=True,
        nickname=username,
        registration_source="email",
        is_active=True,
    )
    user.push_preference = PushPreference(timezone=timezone_name)
    return user


async def _commit_all(db_session, *objects):
    db_session.add_all(list(objects))
    await db_session.commit()
    for obj in objects:
        await db_session.refresh(obj)


async def _create_active_partnership(
    db_session,
    *,
    initiator: User,
    partner: User,
    check_in_days: int,
    started_at: datetime,
) -> AccountabilityPartnership:
    partnership = AccountabilityPartnership(
        initiator_id=initiator.id,
        partner_id=partner.id,
        initiator_goal="保持复盘节奏",
        partner_goal="互相给一句反馈",
        check_in_days=check_in_days,
        status=AccountabilityStatus.ACTIVE,
        started_at=started_at,
        created_at=started_at,
    )
    await _commit_all(db_session, partnership)
    return partnership


async def _create_checkin(
    db_session,
    *,
    partnership: AccountabilityPartnership,
    user: User,
    created_at: datetime,
) -> None:
    checkin = AccountabilityCheckin(
        partnership_id=partnership.id,
        user_id=user.id,
        content="完成一次轻复盘",
        mood=4,
        minutes=25,
        created_at=created_at,
        liked_by=[],
        encouragements=[],
    )
    await _commit_all(db_session, checkin)


@pytest.fixture
def capture_accountability_reminders(monkeypatch):
    sent: list[tuple[str, str]] = []

    async def _record_send(db, user_id, partnership_id, partner_name, locale="zh"):
        sent.append((str(user_id), str(partnership_id)))
        return None

    async def _noop_policy_event(self, *args, **kwargs):
        return None

    monkeypatch.setattr(accountability_notification_service, "send_daily_reminder", _record_send)
    monkeypatch.setattr(PolicySchedulerService, "handle_event", _noop_policy_event)
    return sent


@pytest.mark.asyncio
async def test_daily_reminders_respect_partnership_checkin_cadence(
    db_session,
    capture_accountability_reminders,
) -> None:
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    recent_owner = _make_user(username="recent_owner")
    recent_partner = _make_user(username="recent_partner")
    due_owner = _make_user(username="due_owner")
    due_partner = _make_user(username="due_partner")
    await _commit_all(db_session, recent_owner, recent_partner, due_owner, due_partner)

    recent = await _create_active_partnership(
        db_session,
        initiator=recent_owner,
        partner=recent_partner,
        check_in_days=2,
        started_at=datetime(2026, 4, 25, 1, 0),
    )
    due = await _create_active_partnership(
        db_session,
        initiator=due_owner,
        partner=due_partner,
        check_in_days=2,
        started_at=datetime(2026, 4, 25, 1, 0),
    )
    await _create_checkin(
        db_session,
        partnership=recent,
        user=recent_owner,
        created_at=datetime(2026, 5, 1, 2, 0),
    )
    await _create_checkin(
        db_session,
        partnership=due,
        user=due_owner,
        created_at=datetime(2026, 4, 30, 2, 0),
    )

    result = await _send_daily_reminders(db_session, now=now)

    sent = capture_accountability_reminders
    assert (str(recent_owner.id), str(recent.id)) not in sent
    assert (str(due_owner.id), str(due.id)) in sent
    assert result["skipped_by_cadence"] >= 1


@pytest.mark.asyncio
async def test_daily_reminders_respect_user_notification_preferences(
    db_session,
    capture_accountability_reminders,
) -> None:
    now = datetime(2026, 5, 2, 9, 0, tzinfo=UTC)
    owner = _make_user(username="owner")
    partner = _make_user(username="partner")
    await _commit_all(db_session, owner, partner)
    partnership = await _create_active_partnership(
        db_session,
        initiator=owner,
        partner=partner,
        check_in_days=1,
        started_at=datetime(2026, 4, 25, 1, 0),
    )
    db_session.add(
        NotificationPreferences(
            user_id=owner.id,
            enable_system=False,
            enable_interventions=True,
            disabled_types=[],
            notification_level="standard",
            quiet_hours_enabled=False,
        )
    )
    await db_session.commit()

    result = await _send_daily_reminders(db_session, now=now)

    sent = capture_accountability_reminders
    assert (str(owner.id), str(partnership.id)) not in sent
    assert (str(partner.id), str(partnership.id)) in sent
    assert result["skipped_by_preferences"] == 1


@pytest.mark.asyncio
async def test_daily_reminders_dedupe_same_local_day(
    db_session,
    capture_accountability_reminders,
) -> None:
    now = datetime(2026, 5, 2, 13, 0, tzinfo=UTC)
    owner = _make_user(username="owner")
    partner = _make_user(username="partner")
    await _commit_all(db_session, owner, partner)
    partnership = await _create_active_partnership(
        db_session,
        initiator=owner,
        partner=partner,
        check_in_days=1,
        started_at=datetime(2026, 4, 25, 1, 0),
    )
    db_session.add(
        Notification(
            user_id=owner.id,
            title="今日打卡提醒",
            content="轻轻提醒一下",
            type=AccountabilityNotificationType.DAILY_REMINDER.value,
            data={"partnership_id": str(partnership.id)},
            created_at=now - timedelta(hours=1),
        )
    )
    await db_session.commit()

    result = await _send_daily_reminders(db_session, now=now)

    sent = capture_accountability_reminders
    assert (str(owner.id), str(partnership.id)) not in sent
    assert (str(partner.id), str(partnership.id)) in sent
    assert result["skipped_duplicates"] == 1
