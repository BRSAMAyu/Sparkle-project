from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from app.models.notification_interaction import NotificationPreferences
from app.models.user import PushPreference, User
from app.models.user_preferences import UserPreferencesCenter
from app.services import preference_consumption_service as consumption_module
from app.services.preference_consumption_service import PreferenceConsumptionService


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 4, 21, 9, 15, tzinfo=ZoneInfo("Asia/Shanghai"))
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_schedule_context_uses_frontend_weekly_grid_index(db_session, monkeypatch):
    monkeypatch.setattr(consumption_module, "datetime", FrozenDateTime)
    user_id = uuid4()
    grid = ["relax"] * 168
    grid[9 * 7 + 1] = "busy"  # Tuesday 09:00 in the Flutter grid format.

    db_session.add_all(
        [
            User(
                id=user_id,
                username=f"user_{user_id.hex[:8]}",
                email=f"{user_id.hex[:8]}@example.com",
                hashed_password="hashed",
            ),
            PushPreference(user_id=user_id, timezone="Asia/Shanghai"),
            UserPreferencesCenter(
                user_id=user_id,
                explicit={
                    "timezone": "Asia/Shanghai",
                    "schedule_preferences": {"grid": grid},
                },
                inferred={},
            ),
        ]
    )
    await db_session.commit()

    context = await PreferenceConsumptionService(db_session).get_schedule_context(user_id)

    assert context["schedule_available"] is True
    assert context["slot_index"] == 64
    assert context["current_slot_type"] == "busy"
    assert context["is_busy"] is True


@pytest.mark.asyncio
async def test_push_suppression_uses_local_quiet_hours(db_session, monkeypatch):
    monkeypatch.setattr(consumption_module, "datetime", FrozenDateTime)
    user_id = uuid4()

    db_session.add_all(
        [
            User(
                id=user_id,
                username=f"user_{user_id.hex[:8]}",
                email=f"{user_id.hex[:8]}@example.com",
                hashed_password="hashed",
            ),
            PushPreference(user_id=user_id, timezone="Asia/Shanghai"),
            UserPreferencesCenter(
                user_id=user_id,
                explicit={"timezone": "Asia/Shanghai"},
                inferred={},
            ),
            NotificationPreferences(
                user_id=user_id,
                enable_system=True,
                enable_interventions=True,
                notification_level="standard",
                quiet_hours_enabled=True,
                quiet_hours_start="09:00",
                quiet_hours_end="10:00",
            ),
        ]
    )
    await db_session.commit()

    suppressed = await PreferenceConsumptionService(db_session).should_suppress_push(user_id)

    assert suppressed is True
