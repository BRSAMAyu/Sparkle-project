"""P-06: 24h 测试时钟下的通知负担不变量。

验收口径（headless）：
- 24 小时逐 tick 推进的可控时钟下，任意时刻已发通知数**不超过 cap（0 超 cap）**；
- 当日达到 cap 后所有后续尝试被 ``daily_cap`` 抑制，次日本地日重置后恢复；
- P-03 mute 落库后，剩余 tick 全部被抑制（mute 生效，复用 P-03 真源）。

发送模拟以真实 ``Notification`` 行落库（通知账本即计数真源），resolver 的
cap 判定与账本同源——不是 mock 计数。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.aurora.proactive import config as proactive_config
from app.aurora.runtime_v1.notification_settings import NotificationSettingsResolver
from app.models.notification import Notification
from app.models.user_preferences import UserPreferencesCenter
from app.services.proactive_suggestion_service import ProactiveSuggestionFeedbackService


@pytest.fixture(autouse=True)
def _deterministic_burden_knobs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", False)
    monkeypatch.setattr(proactive_config, "PROACTIVE_DAILY_CAP", 3)


async def _sent_count(db_session, user_id) -> int:
    result = await db_session.execute(
        select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
    )
    return int(result.scalar_one())


async def test_24h_clock_never_exceeds_daily_cap(db_session, test_user) -> None:
    db_session.add(UserPreferencesCenter(user_id=test_user.id, explicit={"daily_cap": 3}))
    await db_session.commit()

    resolver = NotificationSettingsResolver(db_session)
    # 24 个 tick 全部落在同一用户本地日（上海 9/26 00:00–23:00 = UTC 9/25 16:00 起）。
    start = datetime(2026, 9, 25, 16, 0, tzinfo=UTC).replace(tzinfo=None)
    sent_events: list[datetime] = []

    for tick in range(24):
        now = start + timedelta(hours=tick)
        decision = await resolver.evaluate_burden(test_user.id, now=now)
        if decision.allowed:
            # 模拟真实发送：通知账本落一行（与生产 NotificationService 同表）。
            db_session.add(
                Notification(
                    user_id=test_user.id,
                    title="t",
                    content="c",
                    type="comeback_nudge",
                    created_at=now,
                )
            )
            await db_session.commit()
            sent_events.append(now)

        # 不变量：任意时刻，当日已发 ≤ cap（0 超 cap）。
        assert await _sent_count(db_session, test_user.id) <= 3

    total = await _sent_count(db_session, test_user.id)
    assert total == 3, f"24 次 tick（远超 cap 的尝试）应恰发 cap=3 条，实发 {total}"
    # 第 4 次起的尝试必须带 daily_cap 原因。
    assert len(sent_events) == 3
    fourth = await resolver.evaluate_burden(test_user.id, now=start + timedelta(hours=6))
    assert fourth.allowed is False and fourth.reason == "daily_cap"


async def test_cap_resets_on_next_local_day(db_session, test_user) -> None:
    db_session.add(UserPreferencesCenter(user_id=test_user.id, explicit={"daily_cap": 2}))
    await db_session.commit()

    resolver = NotificationSettingsResolver(db_session)
    # 上海本地 9/25 的 08:00–20:00（UTC 00:00–12:00）发满 2 条。
    for hour in (0, 1):
        now = datetime(2026, 9, 25, hour, tzinfo=UTC).replace(tzinfo=None)
        assert (await resolver.evaluate_burden(test_user.id, now=now)).allowed is True
        db_session.add(Notification(user_id=test_user.id, title="t", content="c", type="x", created_at=now))
    await db_session.commit()

    blocked = await resolver.evaluate_burden(
        test_user.id, now=datetime(2026, 9, 25, 2, tzinfo=UTC).replace(tzinfo=None)
    )
    assert blocked.allowed is False and blocked.reason == "daily_cap"

    # 本地日滚动（上海 9/26 00:00 = UTC 9/25 16:00）后恢复放行。
    next_day = await resolver.evaluate_burden(
        test_user.id, now=datetime(2026, 9, 25, 16, 1, tzinfo=UTC).replace(tzinfo=None)
    )
    assert next_day.allowed is True


async def test_mute_from_p03_truth_stops_remaining_day(db_session, test_user) -> None:
    db_session.add(UserPreferencesCenter(user_id=test_user.id, explicit={"daily_cap": 3}))
    await db_session.commit()

    resolver = NotificationSettingsResolver(db_session)
    feedback = ProactiveSuggestionFeedbackService(db_session)
    start = datetime(2026, 9, 25, 0, 0, tzinfo=UTC).replace(tzinfo=None)

    for tick in range(6):
        now = start + timedelta(hours=tick)
        # 与 comeback_nudge_task 同序：先 P-03 mute/cooldown，再负担闸门。
        if await resolver.suggestion_suppressed(test_user.id, "comeback_nudge", now=now) is not None:
            continue
        decision = await resolver.evaluate_burden(test_user.id, now=now)
        if not decision.allowed:
            continue
        if tick == 2:
            # 用户在第 3 个 tick 点了「不再提醒此类」。
            await feedback.record_mute(test_user.id, "comeback_nudge", now=now)
            continue
        db_session.add(
            Notification(user_id=test_user.id, title="t", content="c", type="comeback_nudge", created_at=now)
        )
        await db_session.commit()

    total = await _sent_count(db_session, test_user.id)
    # tick0/1 发送、tick2 mute（不发送）、tick3-5 全被 mute 抑制（非 cap 原因）。
    assert total == 2
    assert await resolver.suggestion_suppressed(test_user.id, "comeback_nudge") is not None
    suppressed = await resolver.suggestion_suppressed(test_user.id, "comeback_nudge")
    assert suppressed is not None and suppressed["reason"] == "muted"


async def test_zero_cap_means_user_off(db_session, test_user) -> None:
    """daily_cap=0 = 用户关停：任何时刻都抑制（关停要真生效）。"""
    db_session.add(UserPreferencesCenter(user_id=test_user.id, explicit={"daily_cap": 0}))
    await db_session.commit()

    resolver = NotificationSettingsResolver(db_session)
    for hour in (1, 9, 17):
        decision = await resolver.evaluate_burden(
            test_user.id, now=datetime(2026, 9, 25, hour, tzinfo=UTC).replace(tzinfo=None)
        )
        assert decision.allowed is False
        assert decision.reason == "daily_cap"
        assert decision.details["cap"] == 0


async def test_other_users_ledger_is_isolated(db_session, test_user) -> None:
    resolver = NotificationSettingsResolver(db_session)
    now = datetime(2026, 9, 25, 6, tzinfo=UTC).replace(tzinfo=None)
    other = uuid4()
    db_session.add(Notification(user_id=other, title="t", content="c", type="x", created_at=now))
    await db_session.commit()

    assert await resolver.daily_count(test_user.id, now=now) == 0
