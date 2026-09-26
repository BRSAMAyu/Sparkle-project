"""V3-FIX-300（state_aggregator 窗口端点 UTC 瞬间直比墙上钟列）红绿测。

定界（V3-FIX-297 同文件遗留，wt582 修 297 时登记）：
- ``FocusSession.end_time`` 存客户端本地墙上时间 naive（mobile 本地 ISO 串
  无时区后缀，V3-FIX-37 定界）→ ``_build_engagement_state`` 的
  ``session_count_7d`` 用 ``end_time >= now-7d``（UTC 瞬间）直比：UTC+8
  墙上钟 naive 比 UTC 瞬间「看起来」晚 8 小时，窗口下界松了 8 小时——
  本地 7 天前傍晚的会话（绝对已超 7 天）被算进 7d 计数；
- ``CalendarEvent.start_time/end_time`` 同为墙上钟列（
  calendar_event_model.dart toIso8601String 本地 ISO 无后缀）→
  ``_build_calendar_context`` week 窗口 ``start_time >= now`` 且
  ``<= now+7d`` 直比 UTC 瞬间：下界松 8 小时（已过去的本地今晚事件混进
  「未来一周」），上界紧 8 小时（第 7 天本地晚间事件被漏掉）。

修法（沿 V3-FIX-297 家族）：
- 窗口端点是 UTC 瞬间、存储列是墙上钟 naive，与 297 的 max 同构——先经
  用户时区把两侧换到同一只钟再比。SQL 过滤面（count/week 查询）采用
  ``wall_clock_to_utc_naive`` 的逆向（``utc_naive_to_wall_clock``）把
  UTC 端点换算成用户墙上钟入 WHERE（eb14c205 calendar「今日」窗口的
  local_midnight_wall 边界同向）；双射换算下与「列值先
  wall_clock_to_utc_naive 再比 UTC」的选中集合等价。时区来源同款
  ``_user_timezone``（push_preference.timezone 标量直查，缺省
  Asia/Shanghai）。

冻结钟（沿 test_state_aggregator_local_clock 双冻结钟族）：
- NOW = 2026-09-25 18:30 naive-UTC = 上海 2026-09-26 02:30——本地日界
  之后、now-7d/now+7d 的墙上钟换算与 naive 直比岔开 8 小时的正中缺陷面；
  UTC 用户同钟控制组钉住边界（含 >=/<= 端点包含性）。
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_event import CalendarEvent
from app.models.focus import FocusSession, FocusStatus
from app.models.user import PushPreference, User
from app.state_aggregator.service import StateAggregatorService

NOW = dt.datetime(2026, 9, 25, 18, 30)  # naive UTC；上海本地 = 2026-09-26 02:30


async def _seed_user(db: AsyncSession, *, timezone: str) -> User:
    user = User(
        username=f"wt586-{uuid4().hex[:8]}",
        email=f"wt586-{uuid4().hex[:8]}@test.local",
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
            # end_time 是客户端本地墙上钟列（无时区后缀 naive）
            start_time=end - dt.timedelta(hours=1),
            end_time=end,
            duration_minutes=60,
            status=FocusStatus.COMPLETED,
        )
    )
    await db.commit()


async def _seed_event(
    db: AsyncSession,
    user_id,
    *,
    title: str,
    start: dt.datetime,
    end: dt.datetime,
) -> UUID:
    event = CalendarEvent(
        user_id=user_id,
        title=title,
        start_time=start,  # 客户端本地墙上钟列（无时区后缀 naive）
        end_time=end,
        source="manual",
    )
    db.add(event)
    await db.commit()
    return event.id


async def _build_calendar(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, user_id):
    service = StateAggregatorService(db_session)
    monkeypatch.setattr(
        service.predictive_service,
        "get_next_intent_forecast",
        AsyncMock(return_value={}),
    )
    return await service._build_calendar_context(user_id, NOW)


def _week_ids(envelope) -> set[UUID]:
    return {
        UUID(sid.removeprefix("calendar_event:"))
        for sid in envelope.source_snapshot_ids
        if sid.startswith("calendar_event:")
    }


# ---------------------------------------------------------------------------
# 端点 1：_build_engagement_state.session_count_7d（end_time >= now-7d）
# ---------------------------------------------------------------------------


async def test_session_count_7d_wall_boundary_shanghai(db_session: AsyncSession):
    """上海用户：本地 7 天前 20:00 的会话（绝对 09-18T12:00Z）不得计入 7d。

    绝对窗口下界 = 09-18T18:30Z；该会话绝对早 6.5 小时——超出 7 天。
    修前 naive 直比：09-18 20:00 >= 09-18 18:30 → 被算进来（多 1）。
    """
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_focus(db_session, user.id, end=dt.datetime(2026, 9, 18, 20, 0))  # 绝对 7 天外
    await _seed_focus(db_session, user.id, end=dt.datetime(2026, 9, 22, 12, 0))  # 窗口内
    await _seed_focus(db_session, user.id, end=dt.datetime(2026, 9, 25, 10, 0))  # 窗口内

    envelope = await StateAggregatorService(db_session)._build_engagement_state(user.id, NOW)

    assert envelope.value.session_count_7d == 2, (
        "7d 计数应按绝对时刻=2（本地 09-18 20:00 绝对只到 09-18T12:00Z，"
        f"早于下界 09-18T18:30Z 不计入）；修前 naive 直比得 {envelope.value.session_count_7d}"
    )


async def test_session_count_7d_utc_control_boundary(db_session: AsyncSession):
    """UTC 用户控制组：墙上钟=UTC 钟同钟，边界含端点（>=）钉住。

    end=now-7d 整点计入、早 1 分钟不计入、窗口内计入 → 恰 2。
    """
    user = await _seed_user(db_session, timezone="UTC")
    await _seed_focus(db_session, user.id, end=dt.datetime(2026, 9, 18, 18, 30))  # == 下界，>= 计入
    await _seed_focus(db_session, user.id, end=dt.datetime(2026, 9, 18, 18, 29))  # 早 1 分钟不计
    await _seed_focus(db_session, user.id, end=dt.datetime(2026, 9, 22, 12, 0))  # 窗口内

    envelope = await StateAggregatorService(db_session)._build_engagement_state(user.id, NOW)

    assert envelope.value.session_count_7d == 2


# ---------------------------------------------------------------------------
# 端点 2：_build_calendar_context week 窗口（start_time >= now / <= now+7d）
# ---------------------------------------------------------------------------


async def test_calendar_week_window_wall_boundary_shanghai(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """上海用户：已过去的本地今晚事件不进未来一周；第 7 天本地晚间事件不漏。

    - past-evening 09-25 20:00-21:00 墙上（绝对 09-25T12:00Z，早于 now）→ 出；
      修前 naive 直比 09-25 20:00 >= 09-25 18:30 → 错进（下界松 8h）。
    - last-evening 10-02 20:00-21:00 墙上（绝对 10-02T12:00Z，在 now+7d 前）→ 进；
      修前 naive 直比 10-02 20:00 > 10-02 18:30（week_end）→ 错漏（上界紧 8h）。
    """
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    past_evening = await _seed_event(
        db_session,
        user.id,
        title="past-evening",
        start=dt.datetime(2026, 9, 25, 20, 0),
        end=dt.datetime(2026, 9, 25, 21, 0),
    )
    mid_week = await _seed_event(
        db_session,
        user.id,
        title="mid-week",
        start=dt.datetime(2026, 9, 28, 10, 0),
        end=dt.datetime(2026, 9, 28, 11, 0),
    )
    last_evening = await _seed_event(
        db_session,
        user.id,
        title="last-evening",
        start=dt.datetime(2026, 10, 2, 20, 0),
        end=dt.datetime(2026, 10, 2, 21, 0),
    )

    envelope = await _build_calendar(db_session, monkeypatch, user.id)

    week = _week_ids(envelope)
    assert week == {mid_week, last_evening}, (
        "week 窗口应含 mid-week/last-evening、排除已过去的 past-evening；"
        f"修前 naive 直比得 {week}（past-evening 错进、last-evening 错漏）"
    )
    assert past_evening not in week


async def test_calendar_week_window_utc_control_boundary(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """UTC 用户控制组：端点包含性钉住——now 整点进、早 1 小时出；now+7d 整点进、晚 1 小时出。"""
    user = await _seed_user(db_session, timezone="UTC")
    at_now = await _seed_event(
        db_session,
        user.id,
        title="at-now",
        start=dt.datetime(2026, 9, 25, 18, 30),
        end=dt.datetime(2026, 9, 25, 19, 30),
    )
    await _seed_event(
        db_session,
        user.id,
        title="before-now",
        start=dt.datetime(2026, 9, 25, 17, 30),
        end=dt.datetime(2026, 9, 25, 18, 0),
    )
    at_week_end = await _seed_event(
        db_session,
        user.id,
        title="at-week-end",
        start=dt.datetime(2026, 10, 2, 18, 30),
        end=dt.datetime(2026, 10, 2, 19, 30),
    )
    await _seed_event(
        db_session,
        user.id,
        title="after-week-end",
        start=dt.datetime(2026, 10, 2, 19, 30),
        end=dt.datetime(2026, 10, 2, 20, 30),
    )

    envelope = await _build_calendar(db_session, monkeypatch, user.id)

    assert _week_ids(envelope) == {at_now, at_week_end}
