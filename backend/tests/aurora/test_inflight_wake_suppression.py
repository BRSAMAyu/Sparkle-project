"""P-06: 用户关停后 in-flight scheduled notifications 的取消与抑制。

两条防线（关停要真生效，不等「地狱时刻」）：
1. **取消面**：用户关停（enable_interventions=False）时，已排队的 pending
   wake 被即时取消（``AuroraWakeScheduler.cancel_pending_wakes``）；统一偏好
   PUT 是触发入口之一。
2. **抑制面**：已经派发、正在执行的投递任务（celery 已排通知）在执行时
   复核统一策略——quiet hours / daily cap / 关停 / 低刺激档都必须生效；
   未被取消面覆盖的 in-flight 任务在此被拦下（defense in depth）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.aurora.proactive import config as proactive_config
from app.aurora.runtime_v1.notification_settings import NotificationSettingsResolver
from app.aurora.runtime_v1.persistence import PersistedScheduledWake
from app.aurora.runtime_v1.state import ScheduledWake
from app.aurora.runtime_v1.wake_scheduler import AuroraWakeScheduler
from app.models.notification import Notification
from app.models.notification_interaction import NotificationPreferences
from app.models.user_preferences import UserPreferencesCenter


@pytest.fixture(autouse=True)
def _deterministic_burden_knobs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", False)
    monkeypatch.setattr(proactive_config, "PROACTIVE_DAILY_CAP", 3)


async def _notification_count(db_session, user_id) -> int:
    result = await db_session.execute(
        select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
    )
    return int(result.scalar_one())


async def _schedule_pending_wake(db_session, user_id, wake_id: str) -> None:
    scheduler = AuroraWakeScheduler(db_session, enabled=True)
    # scheduled_at 取过去时刻：模拟「已到期、in-flight 待投递」的已排通知
    # （deliver 面只在 due 时可见，与生产 scan→dispatch 时序一致）。
    wake = ScheduledWake(
        wake_id=wake_id,
        scheduled_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1),
        reason="checkpoint_debrief",
        planned_action="checkin",
    )
    persisted = await scheduler.schedule_wake(
        user_id,
        surface="aurora_modeling",
        conversation_id="conv-1",
        wake=wake,
    )
    assert persisted is not None and persisted.wake.status == "pending"


async def _load_wake(db_session, wake_id: str) -> PersistedScheduledWake | None:
    from app.aurora.runtime_v1.persistence import AuroraPersistenceStore

    record = await AuroraPersistenceStore(db_session, enabled=True).load_scheduled_wake(wake_id)
    return record


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ── 取消面：cancel_pending_wakes ─────────────────────────────────────────────


async def test_cancel_pending_wakes_cancels_all_inflight(db_session, test_user) -> None:
    wake_ids = [f"w1-{uuid4().hex[:8]}", f"w2-{uuid4().hex[:8]}"]
    for wake_id in wake_ids:
        await _schedule_pending_wake(db_session, test_user.id, wake_id)

    scheduler = AuroraWakeScheduler(db_session, enabled=True)
    cancelled = await scheduler.cancel_pending_wakes(test_user.id, reason="interventions_disabled")

    assert cancelled == 2
    due = await scheduler.list_due_wakes(user_id=test_user.id)
    assert due == []
    for wake_id in wake_ids:
        record = await _load_wake(db_session, wake_id)
        assert record is not None and record.wake.status == "cancelled"


async def test_cancel_pending_wakes_is_scoped_to_user(db_session, test_user) -> None:
    other = uuid4()
    await _schedule_pending_wake(db_session, test_user.id, f"mine-{uuid4().hex[:8]}")
    await _schedule_pending_wake(db_session, other, f"theirs-{uuid4().hex[:8]}")

    scheduler = AuroraWakeScheduler(db_session, enabled=True)
    cancelled = await scheduler.cancel_pending_wakes(test_user.id, reason="interventions_disabled")

    assert cancelled == 1
    remaining = await scheduler.list_due_wakes(user_id=other)
    assert len(remaining) == 1, "其他用户的 in-flight wake 不受牵连"


# ── 抑制面：投递任务执行时复核统一策略 ────────────────────────────────────────


async def test_deliver_suppresses_when_interventions_disabled(db_session, test_user) -> None:
    from app.core.celery_tasks import deliver_aurora_wake

    wake_id = f"w-off-{uuid4().hex[:8]}"
    await _schedule_pending_wake(db_session, test_user.id, wake_id)
    db_session.add(NotificationPreferences(user_id=test_user.id, enable_interventions=False))
    await db_session.commit()

    result = await deliver_aurora_wake(db_session, wake_id=wake_id, user_id=str(test_user.id))

    assert result["status"] == "cancelled"
    assert result["reason"] == "interventions_disabled"
    assert await _notification_count(db_session, test_user.id) == 0
    record = await _load_wake(db_session, wake_id)
    assert record is not None and record.wake.status == "cancelled"


async def test_deliver_suppresses_inside_user_quiet_hours(db_session, test_user) -> None:
    from app.core.celery_tasks import deliver_aurora_wake

    wake_id = f"w-quiet-{uuid4().hex[:8]}"
    await _schedule_pending_wake(db_session, test_user.id, wake_id)
    # 全天 quiet 窗（时钟无关的确定性窗口）。
    db_session.add(
        NotificationPreferences(
            user_id=test_user.id,
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="23:59",
        )
    )
    await db_session.commit()

    result = await deliver_aurora_wake(db_session, wake_id=wake_id, user_id=str(test_user.id))

    assert result["status"] == "cancelled"
    assert result["reason"] == "quiet_hours"
    assert await _notification_count(db_session, test_user.id) == 0


async def test_deliver_suppresses_when_daily_cap_reached(db_session, test_user) -> None:
    from app.core.celery_tasks import deliver_aurora_wake

    wake_id = f"w-cap-{uuid4().hex[:8]}"
    await _schedule_pending_wake(db_session, test_user.id, wake_id)
    db_session.add(UserPreferencesCenter(user_id=test_user.id, explicit={"daily_cap": 1}))
    db_session.add(
        Notification(
            user_id=test_user.id,
            title="早前的通知",
            content="c",
            type="system",
            created_at=_utcnow(),
        )
    )
    await db_session.commit()

    result = await deliver_aurora_wake(db_session, wake_id=wake_id, user_id=str(test_user.id))

    assert result["status"] == "cancelled"
    assert result["reason"] == "daily_cap"
    assert await _notification_count(db_session, test_user.id) == 1, "不新增通知"


async def test_deliver_low_stimulation_is_in_app_only(db_session, test_user) -> None:
    from app.core.celery_tasks import deliver_aurora_wake

    wake_id = f"w-low-{uuid4().hex[:8]}"
    await _schedule_pending_wake(db_session, test_user.id, wake_id)
    db_session.add(UserPreferencesCenter(user_id=test_user.id, explicit={"aurora_stimulation_mode": "low"}))
    await db_session.commit()

    result = await deliver_aurora_wake(
        db_session,
        wake_id=wake_id,
        user_id=str(test_user.id),
        push_via_websocket=True,
    )

    # 低刺激档：通知照常入应用内中心（负担闸门不误伤），但主动推送被 A-07 档位关闭。
    assert result["status"] == "delivered"
    assert result["push_via_websocket"] is False
    assert await _notification_count(db_session, test_user.id) == 1


async def test_deliver_normal_path_unchanged(db_session, test_user) -> None:
    from app.core.celery_tasks import deliver_aurora_wake

    wake_id = f"w-ok-{uuid4().hex[:8]}"
    await _schedule_pending_wake(db_session, test_user.id, wake_id)

    result = await deliver_aurora_wake(
        db_session,
        wake_id=wake_id,
        user_id=str(test_user.id),
        push_via_websocket=True,
    )

    assert result["status"] == "delivered"
    assert result["push_via_websocket"] is True
    assert await _notification_count(db_session, test_user.id) == 1
    record = await _load_wake(db_session, wake_id)
    assert record is not None and record.wake.status == "executed"


async def test_deliver_missing_wake_is_noop(db_session, test_user) -> None:
    from app.core.celery_tasks import deliver_aurora_wake

    result = await deliver_aurora_wake(db_session, wake_id="missing", user_id=str(test_user.id))
    assert result["status"] == "skipped"


async def test_deliver_fail_closed_when_settings_unreadable(db_session, test_user) -> None:
    """设置读不到 → 宁可少发：跳过且不取消（留下次重试），绝不带病投递。"""
    wake_id = f"w-fc-{uuid4().hex[:8]}"
    await _schedule_pending_wake(db_session, test_user.id, wake_id)

    class _Broken:
        async def execute(self, *args, **kwargs):
            raise RuntimeError("db down")

    # 直接钉 resolver 契约；投递路径对 Unavailable 的处理（跳过而非投递）由
    # resolver 的 fail-closed 契约 + 任务侧 try 语义保证。
    resolver = NotificationSettingsResolver(_Broken())  # type: ignore[arg-type]
    from app.aurora.runtime_v1.notification_settings import NotificationSettingsUnavailable

    with pytest.raises(NotificationSettingsUnavailable):
        await resolver.evaluate_burden(test_user.id)
