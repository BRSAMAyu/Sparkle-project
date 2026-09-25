"""P-06: /notification-center/preferences 成为统一设置面（服务端权威）。

一处真源：quiet hours（NotificationPreferences 表）+ daily cap
（explicit["daily_cap"]，P-04 同款偏好中心载体）+ stimulation mode
（A-07 aurora_stimulation_mode，同一真源键）——GET/PUT 统一投影与写路径，
多设备读同一服务端状态；PUT 关停（enable_interventions=False）即时取消
in-flight scheduled notifications。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.api.v1.notification_center import (
    get_notification_preferences,
    update_notification_preferences,
)
from app.aurora.proactive import config as proactive_config
from app.aurora.runtime_v1.persistence import AuroraPersistenceStore
from app.aurora.runtime_v1.state import ScheduledWake
from app.aurora.runtime_v1.wake_scheduler import AuroraWakeScheduler
from app.models.notification_interaction import NotificationPreferences
from app.models.user_preferences import UserPreferencesCenter
from app.schemas.unified_notification import NotificationPreferencesUpdate


@pytest.fixture(autouse=True)
def _deterministic_burden_knobs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", False)
    monkeypatch.setattr(proactive_config, "PROACTIVE_DAILY_CAP", 3)


async def _get_prefs(db_session, test_user):
    return await get_notification_preferences(current_user=test_user, db=db_session)


async def _put_prefs(db_session, test_user, **fields):
    return await update_notification_preferences(
        NotificationPreferencesUpdate(**fields), current_user=test_user, db=db_session
    )


async def test_get_preferences_projects_unified_state(db_session, test_user) -> None:
    db_session.add(
        UserPreferencesCenter(user_id=test_user.id, explicit={"daily_cap": 5, "aurora_stimulation_mode": "low"})
    )
    await db_session.commit()

    prefs = await _get_prefs(db_session, test_user)

    assert prefs.daily_cap == 5
    assert prefs.stimulation_mode == "low"
    assert prefs.quiet_hours_enabled is False


async def test_get_preferences_defaults_match_enforcement(db_session, test_user) -> None:
    prefs = await _get_prefs(db_session, test_user)

    assert prefs.daily_cap == 3, "未设置时投影 enforcement 基线（env cap）"
    assert prefs.stimulation_mode == "auto"
    assert prefs.enable_interventions is True


async def test_put_preferences_writes_one_truth_and_roundtrips(db_session, test_user) -> None:
    updated = await _put_prefs(
        db_session,
        test_user,
        quiet_hours_enabled=True,
        quiet_hours_start="23:00",
        quiet_hours_end="07:00",
        daily_cap=4,
        stimulation_mode="low",
    )

    assert updated.daily_cap == 4
    assert updated.stimulation_mode == "low"
    assert updated.quiet_hours_enabled is True

    # 多设备一致：另一台设备 GET 同一服务端状态。
    again = await _get_prefs(db_session, test_user)
    assert again.daily_cap == 4
    assert again.stimulation_mode == "low"
    assert again.quiet_hours_start == "23:00"

    # 真源落位：aurora_stimulation_mode 走 A-07 同一键；daily_cap 走 explicit。
    row = (
        await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == test_user.id))
    ).scalar_one()
    assert row.explicit["aurora_stimulation_mode"] == "low"
    assert row.explicit["daily_cap"] == 4
    assert row.explicit["notification_preferences"]["quiet_hours_enabled"] is True


async def test_put_preferences_rejects_invalid_values(db_session, test_user) -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        NotificationPreferencesUpdate(daily_cap=-1)
    with pytest.raises(pydantic.ValidationError):
        NotificationPreferencesUpdate(stimulation_mode="diagnose_me")


async def test_put_disable_interventions_cancels_inflight_wakes(db_session, test_user) -> None:
    wake_id = f"api-w-{uuid4().hex[:8]}"
    scheduler = AuroraWakeScheduler(db_session, enabled=True)
    await scheduler.schedule_wake(
        test_user.id,
        surface="aurora_modeling",
        conversation_id="conv-1",
        wake=ScheduledWake(
            wake_id=wake_id,
            scheduled_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1),
            reason="checkpoint_debrief",
            planned_action="checkin",
        ),
    )
    assert len(await scheduler.list_due_wakes(user_id=test_user.id)) == 1

    await _put_prefs(db_session, test_user, enable_interventions=False)

    record = await AuroraPersistenceStore(db_session, enabled=True).load_scheduled_wake(wake_id)
    assert record is not None and record.wake.status == "cancelled"
    assert len(await scheduler.list_due_wakes(user_id=test_user.id)) == 0


async def test_put_other_changes_do_not_cancel_inflight(db_session, test_user) -> None:
    wake_id = f"api-keep-{uuid4().hex[:8]}"
    scheduler = AuroraWakeScheduler(db_session, enabled=True)
    await scheduler.schedule_wake(
        test_user.id,
        surface="aurora_modeling",
        conversation_id="conv-1",
        wake=ScheduledWake(
            wake_id=wake_id,
            scheduled_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1),
            reason="checkpoint_debrief",
            planned_action="checkin",
        ),
    )

    await _put_prefs(db_session, test_user, notification_level="minimal")

    record = await AuroraPersistenceStore(db_session, enabled=True).load_scheduled_wake(wake_id)
    assert record is not None and record.wake.status == "pending", "未关停不误取消"


async def test_persisted_row_model_roundtrip(db_session, test_user) -> None:
    """quiet 窗写在既有 NotificationPreferences 表（零迁移）。"""
    await _put_prefs(
        db_session, test_user, quiet_hours_enabled=True, quiet_hours_start="21:30", quiet_hours_end="06:30"
    )
    row = (
        await db_session.execute(select(NotificationPreferences).where(NotificationPreferences.user_id == test_user.id))
    ).scalar_one()
    assert row.quiet_hours_enabled is True
    assert row.quiet_hours_start == "21:30"
    assert row.quiet_hours_end == "06:30"
