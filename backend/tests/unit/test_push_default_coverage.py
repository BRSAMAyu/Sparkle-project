"""Regression tests for daily-flow DF-9: structurally silent push channel.

Two defects kept the notification pipeline empty for real users (daily-flow
eval: 3 days of zero notifications despite streak, plan and error feedback):

1. PushService.process_all_users INNER-JOINed PushPreference, so users who
   never touched push settings (138/149 active users in the dev DB) were
   invisible to the smart push cycle.
2. UserPushOptIn DEFAULTS["enabled"] = False — the product-level master switch
   was off for everyone who never explicitly opted in, so even evaluated users
   were skipped at _send_push.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.user import User
from app.services.push_service import PushService
from app.services.user_push_opt_in_service import DEFAULTS, UserPushOptInService


@pytest.fixture
async def bare_user(db_session):
    """Active user with NO PushPreference / UserPushOptIn rows."""
    user = User(
        username=f"push_bare_{uuid4().hex[:8]}",
        email=f"push_bare_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_opt_in_defaults_enable_push(db_session, bare_user):
    record = await UserPushOptInService(db_session).get_or_create(bare_user.id)
    assert record.enabled is True, (
        "the push master switch must default to on (opt-out product), "
        "otherwise the whole channel is structurally silent"
    )
    assert DEFAULTS["quiet_hours_start"] == "22:00"
    assert DEFAULTS["quiet_hours_end"] == "08:00"


@pytest.mark.asyncio
async def test_process_all_users_evaluates_users_without_push_preference(
    bare_user, db_session, monkeypatch
):
    """A user without a PushPreference row must still be evaluated by the smart
    push cycle and receive the in-app notification when a strategy triggers."""

    async def _true(self, *args, **kwargs):
        return True

    async def _false(self, *args, **kwargs):
        return False

    async def _content(self, user, explicit_prefs, trigger_type, trigger_data):
        return {"title": "Sparkle 提醒", "body": "该复习今天的冲刺任务了"}

    monkeypatch.setattr(PushService, "_is_active_time", _true)
    monkeypatch.setattr(PushService, "_check_frequency_cap", _false)
    monkeypatch.setattr(PushService, "_check_schedule_and_quiet_hours", _false)
    monkeypatch.setattr(PushService, "_generate_push_content", _content)
    monkeypatch.setattr(PushService, "_aurora_push_opt_in_enabled", _true)

    from app.services.push_strategies import (
        CuriosityStrategy,
        EmptyCapsuleStrategy,
        InactivityStrategy,
        MemoryStrategy,
        SprintStrategy,
    )

    async def _should_trigger(self, user, policy):
        return user.id == bare_user.id

    async def _no_trigger(self, user, policy):
        return False

    monkeypatch.setattr(InactivityStrategy, "should_trigger", _should_trigger)
    monkeypatch.setattr(SprintStrategy, "should_trigger", _no_trigger)
    monkeypatch.setattr(MemoryStrategy, "should_trigger", _no_trigger)
    monkeypatch.setattr(EmptyCapsuleStrategy, "should_trigger", _no_trigger)
    monkeypatch.setattr(CuriosityStrategy, "should_trigger", _no_trigger)

    service = PushService(db_session)
    summary = await service.process_all_users()

    assert summary["evaluated_users"] >= 1, "users without PushPreference must be evaluated"
    assert summary["triggered"] >= 1

    from sqlalchemy import select

    from app.models.notification import Notification

    notifications = (
        (await db_session.execute(select(Notification).where(Notification.user_id == bare_user.id)))
        .scalars()
        .all()
    )
    assert notifications, "triggered push must create the in-app notification"
