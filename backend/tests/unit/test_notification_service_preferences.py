from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.models.notification import Notification
from app.models.notification_interaction import NotificationPreferences
from app.models.user import PushPreference, User
from app.schemas.notification import NotificationCreate
from app.services.notification_service import NotificationService


def _format_clock(value: datetime) -> str:
    return value.strftime("%H:%M")


@pytest.mark.asyncio
async def test_notification_service_suppresses_websocket_during_quiet_hours(db_session, monkeypatch):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="hashed",
    )
    push_pref = PushPreference(user_id=user_id, timezone="Asia/Shanghai")
    now_local = datetime.now(ZoneInfo("Asia/Shanghai"))
    prefs = NotificationPreferences(
        user_id=user_id,
        enable_system=True,
        enable_interventions=True,
        notification_level="standard",
        quiet_hours_enabled=True,
        quiet_hours_start=_format_clock(now_local - timedelta(hours=1)),
        quiet_hours_end=_format_clock(now_local + timedelta(hours=1)),
    )
    db_session.add_all([user, push_pref, prefs])
    await db_session.commit()

    ws_manager = SimpleNamespace(send_personal_message=AsyncMock())
    monkeypatch.setattr("app.core.websocket.get_ws_manager", lambda: ws_manager)

    await NotificationService.create(
        db_session,
        user_id,
        NotificationCreate(title="Quiet", content="Should persist only", type="system"),
        push_via_websocket=True,
    )

    result = await db_session.execute(select(Notification).where(Notification.user_id == user_id))
    notifications = result.scalars().all()

    assert len(notifications) == 1
    ws_manager.send_personal_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_notification_service_respects_enable_system_for_realtime_delivery(db_session, monkeypatch):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="hashed",
    )
    push_pref = PushPreference(user_id=user_id, timezone="Asia/Shanghai")
    prefs = NotificationPreferences(
        user_id=user_id,
        enable_system=False,
        enable_interventions=True,
        notification_level="standard",
        quiet_hours_enabled=False,
    )
    db_session.add_all([user, push_pref, prefs])
    await db_session.commit()

    ws_manager = SimpleNamespace(send_personal_message=AsyncMock())
    monkeypatch.setattr("app.core.websocket.get_ws_manager", lambda: ws_manager)

    await NotificationService.create(
        db_session,
        user_id,
        {"title": "Muted", "content": "No realtime push", "type": "system"},
        push_via_websocket=True,
    )

    result = await db_session.execute(select(Notification).where(Notification.user_id == user_id))
    notifications = result.scalars().all()

    assert len(notifications) == 1
    ws_manager.send_personal_message.assert_not_awaited()
