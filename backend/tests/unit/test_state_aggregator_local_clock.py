"""V3-FIX-297（state_aggregator 跨钟表 max + UTC 日历日界）红绿测。

定界（wt576 F6 双构建器复现 + V3-FIX-37 列钟表家族）：
- ``FocusSession.end_time`` 存客户端本地墙上时间 naive（mobile 发本地 ISO 串、
  无时区后缀——focus_repository.dart:79 / V3-FIX-37 定界）；
- ``UserStreakStats.last_activity_date`` 存 UTC 日界（achievement_engine
  写 ``_utcnow().date()``）→ ``_build_engagement_state`` 修前把两列直接
  ``max()``：UTC+8 用户墙上 01:00（绝对 09-24T17:00Z）会压过 streak 的
  09-25T00:00Z（绝对更新 7 小时）——选出绝对时刻更旧的值；
- ``CalendarEvent.start_time/end_time`` 存客户端本地墙上时间 naive
  （mobile calendar_event_model.dart:102 toIso8601String 本地 ISO 无后缀）
  → ``_build_calendar_context`` 修前用 naive-UTC ``now.replace(hour=0)``
  切「今日」：UTC+8 02:30 时把用户昨日午后事件切进「今日」空闲格、
  本地今日上午忙碌整段缺席。

修法（沿 V3-FIX-37/208/211 家族先例）：
- 比较前把墙上钟列经用户时区换算成绝对 UTC naive（time_utils.
  wall_clock_to_utc_naive），与 streak 值同钟 max；返回值同为绝对 UTC
  naive——wake_policy.hours_since_last_active（``_utcnow()`` 差值）与
  push_policy_compiler（``>= now-72h``）消费面均按绝对时刻直比；
- 「今日」窗口按用户本地日界的墙上零点切（time_utils.local_date +
  local_midnight_wall），勿用 local_midnight_as_utc_naive（墙上钟列）。

冻结钟（沿 test_growth_streak_local_clock 双冻结钟族）：
- NOW = 2026-09-25 18:30 naive-UTC = 上海 2026-09-26 02:30（用户昨日/今日
  双侧都落在界上，正中缺陷面）；UTC 用户同钟控制组钉住「边界确由用户
  时区驱动、非硬编码平移」。
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import UserStreakStats
from app.models.calendar_event import CalendarEvent
from app.models.focus import FocusSession, FocusStatus
from app.models.user import PushPreference, User
from app.state_aggregator.service import StateAggregatorService

NOW = dt.datetime(2026, 9, 25, 18, 30)  # naive UTC；上海本地 = 2026-09-26 02:30


async def _seed_user(db: AsyncSession, *, timezone: str) -> User:
    user = User(
        username=f"wt582-{uuid4().hex[:8]}",
        email=f"wt582-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.flush()
    db.add(PushPreference(user_id=user.id, timezone=timezone))
    await db.commit()
    return user


async def _seed_focus(db: AsyncSession, user_id, *, end: dt.datetime) -> None:
    db.add(
        FocusSession(
            user_id=user_id,
            # start_time/end_time 是客户端本地墙上钟列（无时区后缀 naive）
            start_time=end - dt.timedelta(hours=1),
            end_time=end,
            duration_minutes=60,
            status=FocusStatus.COMPLETED,
        )
    )
    await db.commit()


def _block_pairs(value) -> list[tuple[str, str]]:
    return [(block.start, block.end) for block in value.time_blocks_today]


# ---------------------------------------------------------------------------
# F6-1：engagement_state 跨钟表 max
# ---------------------------------------------------------------------------


async def test_engagement_max_picks_newest_absolute_moment_shanghai(
    db_session: AsyncSession,
):
    """上海用户：墙上钟 01:00（=09-24T17:00Z）不得压过 streak 09-25T00:00Z。

    修前 max() 直比 naive 值选了墙上钟 01:00——绝对时刻比 streak 值旧 7 小时。
    """
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_focus(db_session, user.id, end=dt.datetime(2026, 9, 25, 1, 0))
    db_session.add(
        UserStreakStats(user_id=user.id, current_streak=1, last_activity_date=dt.datetime(2026, 9, 25, 0, 0))
    )
    await db_session.commit()

    envelope = await StateAggregatorService(db_session)._build_engagement_state(user.id, NOW)

    assert envelope.value.last_active_at == dt.datetime(2026, 9, 25, 0, 0), (
        f"应选绝对时刻更新的 streak 值 09-25T00:00Z（墙上钟 01:00 绝对只到 09-24T17:00Z）；"
        f"修前 max() 直比 naive 选了墙上钟 01:00：{envelope.value.last_active_at}"
    )


async def test_engagement_returns_converted_absolute_when_wall_newer(
    db_session: AsyncSession,
):
    """墙上钟更新的那次：返回值应为换算后的绝对 UTC 瞬间，而非墙上钟原样。

    墙上钟 09-25 20:00（上海）= 09-25T12:00Z > streak 09-25T00:00Z；修前返回
    墙上钟 20:00 原样，wake_policy._extract_hours_since_last_active 以
    ``_utcnow()`` 差值消费该值会被 8 小时时差污染。
    """
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_focus(db_session, user.id, end=dt.datetime(2026, 9, 25, 20, 0))
    db_session.add(
        UserStreakStats(user_id=user.id, current_streak=1, last_activity_date=dt.datetime(2026, 9, 25, 0, 0))
    )
    await db_session.commit()

    envelope = await StateAggregatorService(db_session)._build_engagement_state(user.id, NOW)

    assert envelope.value.last_active_at == dt.datetime(2026, 9, 25, 12, 0), (
        f"墙上钟胜出时返回值应为用户时区换算后的绝对 UTC 瞬间 09-25T12:00Z；"
        f"修前返回墙上钟 20:00 原样：{envelope.value.last_active_at}"
    )


async def test_engagement_utc_user_control_unchanged(db_session: AsyncSession):
    """UTC 用户控制组：墙上钟=UTC 钟同钟，赢家与修前一致（钉住时区驱动面）。"""
    user = await _seed_user(db_session, timezone="UTC")
    await _seed_focus(db_session, user.id, end=dt.datetime(2026, 9, 25, 1, 0))
    db_session.add(
        UserStreakStats(user_id=user.id, current_streak=1, last_activity_date=dt.datetime(2026, 9, 25, 0, 0))
    )
    await db_session.commit()

    envelope = await StateAggregatorService(db_session)._build_engagement_state(user.id, NOW)

    assert envelope.value.last_active_at == dt.datetime(2026, 9, 25, 1, 0)


# ---------------------------------------------------------------------------
# F6-2：calendar_context「今日」日界
# ---------------------------------------------------------------------------


async def _seed_calendar_pair(db: AsyncSession, user_id) -> None:
    db.add_all(
        [
            CalendarEvent(
                user_id=user_id,
                title="today-morning",
                start_time=dt.datetime(2026, 9, 26, 9, 0),  # 上海本地今日上午
                end_time=dt.datetime(2026, 9, 26, 10, 0),
                source="manual",
            ),
            CalendarEvent(
                user_id=user_id,
                title="yesterday-afternoon",
                start_time=dt.datetime(2026, 9, 25, 14, 0),  # 上海本地昨日下午
                end_time=dt.datetime(2026, 9, 25, 15, 0),
                source="manual",
            ),
        ]
    )
    await db.commit()


async def _build_calendar(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, user_id):
    service = StateAggregatorService(db_session)
    monkeypatch.setattr(
        service.predictive_service,
        "get_next_intent_forecast",
        AsyncMock(return_value={}),
    )
    return await service._build_calendar_context(user_id, NOW)


async def test_calendar_today_blocks_follow_local_day_shanghai(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海用户（本地 09-26 02:30）：今日忙碌 09-10 点在场、昨日 14-15 点缺席。

    修前参照日=UTC 09-25（=用户昨日）：昨日 14:00-15:00 事件把「今日」空闲格
    切开、本地今日 09:00-10:00 忙碌完全缺席。
    """
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_calendar_pair(db_session, user.id)

    value = (await _build_calendar(db_session, monkeypatch, user.id)).value

    assert _block_pairs(value) == [("07:00", "09:00"), ("10:00", "22:00")], (
        f"「今日」应按用户本地日 09-26 切：09:00-10:00 忙碌两侧空闲 07:00-09:00/10:00-22:00；"
        f"修前参照日=UTC 09-25（用户昨日）得 {_block_pairs(value)}"
    )


async def test_calendar_today_blocks_utc_user_control(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """UTC 用户控制组：同一冻结钟下「今日」=09-25，昨日午后事件在场。

    钉住边界确由用户时区驱动，而非把窗口硬编码平移一日。
    """
    user = await _seed_user(db_session, timezone="UTC")
    await _seed_calendar_pair(db_session, user.id)

    value = (await _build_calendar(db_session, monkeypatch, user.id)).value

    assert _block_pairs(value) == [("07:00", "14:00"), ("15:00", "22:00")]
