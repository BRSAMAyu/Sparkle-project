"""V3-FIX-211（growth_dashboard_service 墙钟余族）红绿测：period 窗口与 streak 按列定钟。

定界（V3-FIX-37 双存储钟实录 + 本卡逐列核）：
- ``_get_growth_status`` 修前 ``period_start = _utcnow() - 7d``（UTC 瞬间）
  同时喂 ``_sum_focus_minutes``（``FocusSession.start_time`` 墙上钟列——
  跨钟，窗口端点随时刻在本地日界附近漂移 ±8h）与 ``_count_completed_tasks``
  （``Task.completed_at`` UTC 存储列——无跨钟，保持不变）；
- ``_get_current_streak_days`` 修前单一 ``cutoff = _utcnow() - 30d`` 双列
  混用（completed_at 正确、start_time 跨钟），且 ``cursor = _utcnow().date()``
  是 UTC date——UTC+8 晨间（UTC 尚在前日）把墙上钟「本地今日」的会话
  排除在 streak 之外。

修法（沿 V3-FIX-208/209 先例）：
- focus 窗口端点 ``local_midnight_wall(today - LOOKBACK_DAYS)``（墙上钟列
  用本地零点 naive；勿用 local_midnight_as_utc_naive——那是 UTC 存储列）；
- streak 双 cutoff 按列选钟（completed_at=UTC 瞬间、start_time=墙上零点），
  活跃日按列归一到用户本地日（completed_at→``local_date(value, tz)``、
  start_time→``.date()``），cursor=用户本地日。

冻结钟（沿 test_growth_dashboard_focus_window_local 冻结钟族）：
- NOW_EVENING = 2026-09-25 12:00 UTC（上海 = 09-25 20:00）：证 period 漏计
  面与 30 天 cutoff 漏计面；
- NOW_LATE = 2026-09-25 20:00 UTC（上海 = 09-26 04:00）：证 streak 游标
  本地日面——墙上钟「本地今日 03:30」的会话修前不计入 streak。
"""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.focus import FocusSession, FocusStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.services.growth_dashboard_service import GrowthDashboardService

NOW_EVENING = dt.datetime(2026, 9, 25, 12, 0)  # naive UTC；上海本地 = 2026-09-25 20:00
NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；上海本地 = 2026-09-26 04:00


def _freeze(monkeypatch: pytest.MonkeyPatch, now: dt.datetime) -> None:
    monkeypatch.setattr("app.services.growth_dashboard_service._utcnow", lambda: now)


async def _seed_user(db: AsyncSession, *, timezone: str | None = None) -> User:
    user = User(
        username=f"wt507-{uuid4().hex[:8]}",
        email=f"wt507-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if timezone is not None:
        db.add(PushPreference(user_id=user.id, timezone=timezone))
        await db.commit()
    return user


async def _seed_session(
    db: AsyncSession,
    user_id,
    *,
    start: dt.datetime,
    minutes: int,
) -> FocusSession:
    session = FocusSession(
        user_id=user_id,
        # start_time 是客户端本地墙上钟列（无时区后缀 naive）
        start_time=start,
        end_time=start + dt.timedelta(minutes=minutes),
        duration_minutes=minutes,
        status=FocusStatus.COMPLETED,
    )
    db.add(session)
    await db.commit()
    return session


async def test_growth_status_focus_window_counts_local_week_morning(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海晚间（本地 09-25 20:00）：7 天前本地上午的专注必须计入 focus_hours_week。

    修前 period_start = 09-18 12:00（UTC 瞬间）直比墙上钟列，09-18 08:30 的
    50 分钟会话被漏计；completed_at 任务数是 UTC 列，两版都应为 1（控制组）。
    """
    _freeze(monkeypatch, NOW_EVENING)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 18, 8, 30), minutes=50)
    # 8 天前深夜——两个窗口都应排除（防窗口被修得过宽）
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 17, 23, 0), minutes=40)
    # 本地昨日（09-24）上午——两个窗口都应计入（防「修成全排」假绿）
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 24, 9, 0), minutes=60)
    db_session.add(
        Task(
            user_id=user.id,
            title="wt507 completed control",
            type=TaskType.LEARNING,
            status=TaskStatus.COMPLETED,
            completed_at=dt.datetime(2026, 9, 19, 6, 0),
            estimated_minutes=30,
        )
    )
    await db_session.commit()

    service = GrowthDashboardService(db_session)
    service._get_current_streak_days = AsyncMock(return_value=0)  # type: ignore[method-assign]
    status = await service._get_growth_status(
        user_id=user.id,
        user=SimpleNamespace(nickname="Mina", full_name=None, username="mina"),
        active_plan=None,
        growth_signal=None,
        most_important_task=None,
        weakest_area=None,
    )

    assert status["focus_hours_week"] == 1.8, (
        f"上海晚间 7d 窗口应按本地零点(09-18 00:00)计入 7 天前上午会话（50+60 分钟）；"
        f"修前起点=09-18 12:00 把它漏计：{status}"
    )
    assert status["tasks_completed_week"] == 1, f"UTC 存储列窗口保持 UTC 瞬间，不应被本卡改动：{status}"


async def test_streak_counts_wall_column_month_ago_morning(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """30 天 cutoff 按列定钟：墙上钟列 30 天前本地上午的会话必须计入链首。

    上海本地今日=09-25，正确墙钟 cutoff=08-26 00:00；修前 cutoff=09-25
    12:00−30d=08-26 12:00（UTC 瞬间直比）把 08-26 08:30 的链首会话漏计，
    连续链短一日（30 而非 31）。
    """
    _freeze(monkeypatch, NOW_EVENING)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    for day_offset in range(31):
        day = dt.datetime(2026, 8, 26) + dt.timedelta(days=day_offset)
        await _seed_session(db_session, user.id, start=day.replace(hour=8, minute=30), minutes=20)

    streak = await GrowthDashboardService(db_session)._get_current_streak_days(user.id)

    assert streak == 31, (
        f"墙上钟列 cutoff 应为本地零点 08-26 00:00，31 天连续链完整；"
        f"修前 cutoff=08-26 12:00（UTC 瞬间）把链首 08-26 08:30 会话漏计：{streak}"
    )


async def test_streak_cursor_follows_user_local_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """streak 游标=用户本地日：上海晨间（本地 09-26 04:00）本地今日会话必须计入。

    冻结 NOW=09-25 20:00Z：修前 cursor=_utcnow().date()=09-25（UTC date），
    墙上钟 09-26 03:30（本地今日凌晨）的会话在游标「未来」而不计，streak
    少一日；修后 cursor=本地 09-26，链为 09-26+09-25 两天。
    """
    _freeze(monkeypatch, NOW_LATE)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 26, 3, 30), minutes=30)
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 25, 9, 0), minutes=45)

    streak = await GrowthDashboardService(db_session)._get_current_streak_days(user.id)

    assert streak == 2, (
        f"streak 游标应为用户本地日 09-26（上海晨间），09-26 03:30 + 09-25 09:00 连续两天；"
        f"修前 cursor=UTC date 09-25 把本地今日会话排除：{streak}"
    )
