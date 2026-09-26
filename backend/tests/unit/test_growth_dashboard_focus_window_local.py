"""V3-FIX-208（growth-dashboard 7 天专注窗口跨钟）红绿测：窗口端点切用户本地墙上零点。

定界实录（V3-FIX-37 / V3-FIX-208）：
- ``FocusSession.start_time`` 存客户端本地墙上时间 naive（mobile 发本地 ISO
  串、无时区后缀），是**墙上钟列**，不是 UTC 存储列；
- ``experience_readouts.get_experience_growth_dashboard`` 的 7 天窗口修前
  ``since = _utcnow() - timedelta(days=7)``（UTC naive 瞬间）直比墙上钟列
  —— 窗口起点在「本地 7 天前零点」附近随时刻漂移 ±8h：
  * UTC+8 本地 08:00–24:00（UTC date = 本地 date）：实际窗口起点晚于本地
    零点至多 16h，7 天前上午的会话被**漏计**（focus_minutes_7d /
    focus_sessions_7d 少计、quality_score 联动失真）；
  * UTC+8 本地 00:00–08:00（UTC date = 本地 date − 1）：实际窗口起点早于
    本地零点至多 8h，把 8 天前深夜的会话**多计**进窗口。
- 修法沿 ``FocusService.get_weekly_stats`` 先例（V3-FIX-37）：today=用户
  本地日（``_user_local_today``：push_preference.timezone 缺省
  Asia/Shanghai），窗口端点 ``local_midnight_wall(today - 7d)``（墙上钟
  零点 naive；勿用 local_midnight_as_utc_naive——那是 UTC 存储列的换算）。

两个冻结钟各证一面（沿 test_statistics_local_timezone_boundary /
test_today_view_local_date_boundary 的冻结钟族）：
- NOW_EVENING = 2026-09-25 12:00 UTC（上海 = 09-25 20:00）：证**漏计**面
  —— 7 天前（09-18）本地上午 08:30 的会话必须计入窗口，修前被
  ``>= 09-18 12:00`` 排除；
- NOW_MORNING = 2026-09-25 23:30 UTC（上海 = 09-26 07:30）：证**多计**面
  + 时区驱动面 —— 本地窗口起点是 09-19 00:00（墙上钟），修前
  ``>= 09-18 23:30`` 把 8 天前（09-18）深夜会话多计；UTC 用户同刻窗口
  起点是 09-18 00:00，同钟会话计入，证边界确由用户时区驱动。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import experience_readouts
from app.models.focus import FocusSession, FocusStatus
from app.models.user import PushPreference, User

NOW_EVENING = dt.datetime(2026, 9, 25, 12, 0)  # naive UTC；上海本地 = 2026-09-25 20:00
NOW_MORNING = dt.datetime(2026, 9, 25, 23, 30)  # naive UTC；上海本地 = 2026-09-26 07:30


def _freeze(monkeypatch: pytest.MonkeyPatch, now: dt.datetime) -> None:
    monkeypatch.setattr(experience_readouts, "_utcnow", lambda: now)


@pytest.fixture
def frozen_evening(monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze(monkeypatch, NOW_EVENING)


@pytest.fixture
def frozen_morning(monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze(monkeypatch, NOW_MORNING)


async def _seed_user(db: AsyncSession, *, timezone: str | None = None) -> User:
    user = User(
        username=f"wt499-{uuid4().hex[:8]}",
        email=f"wt499-{uuid4().hex[:8]}@test.local",
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


async def _dashboard(db: AsyncSession, user: User) -> dict:
    return await experience_readouts.get_experience_growth_dashboard(current_user=user, db=db)


async def test_week_ago_morning_session_counts_at_shanghai_evening(db_session: AsyncSession, frozen_evening: None):
    """上海晚间（本地 09-25 20:00）：7 天前本地上午的会话必须计入 7d 窗口。

    修前窗口起点 = UTC now − 7d = 09-18 12:00（直比墙上钟列），09-18
    08:30 的会话被漏计 → focus_minutes_7d 少 50 分钟、quality_score 联动
    失真（evidence 文案同步失真）。
    """
    user = await _seed_user(db_session)
    # 7 天前（09-18）本地上午 08:30 —— 正确窗口（本地零点 09-18 00:00 起）内
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 18, 8, 30), minutes=50)
    # 本地今日上午 —— 两个窗口都应计入（防「修成全排」假绿）
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 25, 7, 30), minutes=30)
    # 8 天前深夜 —— 两个窗口都应排除（防窗口被修得过宽）
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 17, 23, 0), minutes=40)

    payload = await _dashboard(db_session, user)

    learning = payload["learning_dashboard"]
    assert learning["focus_sessions_7d"] == 2, (
        f"上海晚间 7d 窗口应按本地零点(09-18 00:00)计入 7 天前上午会话；" f"修前起点=09-18 12:00 把它漏计：{learning}"
    )
    assert learning["focus_minutes_7d"] == 80, f"应计 50+30 分钟（8 天前 40 分钟不计）：{learning}"
    assert f"过去 7 天专注 {learning['focus_minutes_7d']} 分钟" in payload["streak_quality"]["evidence"]


async def test_local_midnight_boundary_excludes_eve_of_window(db_session: AsyncSession, frozen_morning: None):
    """上海晨间（本地 09-26 07:30）：本地窗口起点=09-19 00:00，8 天前深夜会话不计。

    修前窗口起点 = UTC now − 7d = 09-18 23:30，把 09-18 23:45（本地 8 天
    前深夜、正确窗口之外）的会话多计进 7d 窗口。
    """
    user = await _seed_user(db_session)
    await _seed_session(db_session, user.id, start=dt.datetime(2026, 9, 18, 23, 45), minutes=25)

    payload = await _dashboard(db_session, user)

    learning = payload["learning_dashboard"]
    assert learning["focus_sessions_7d"] == 0, (
        f"上海晨间本地窗口起点=09-19 00:00，8 天前(09-18)深夜会话不应计入；"
        f"修前起点=09-18 23:30 把它多计：{learning}"
    )
    assert learning["focus_minutes_7d"] == 0, f"8 天前深夜会话不属于 7d 窗口：{learning}"


async def test_timezone_drives_window_start(db_session: AsyncSession, frozen_morning: None):
    """边界确由用户时区驱动：同一冻结时刻、同钟会话，上海与 UTC 用户窗口不同。

    冻结 NOW=09-25 23:30 UTC：上海本地今日=09-26（窗口起点 09-19 00:00），
    UTC 用户本地今日=09-25（窗口起点 09-18 00:00）。墙钟 09-18 12:00 的
    会话：上海用户不计、UTC 用户计入。
    """
    shanghai_user = await _seed_user(db_session)
    utc_user = await _seed_user(db_session, timezone="UTC")
    await _seed_session(db_session, shanghai_user.id, start=dt.datetime(2026, 9, 18, 12, 0), minutes=25)
    await _seed_session(db_session, utc_user.id, start=dt.datetime(2026, 9, 18, 12, 0), minutes=25)

    shanghai = await _dashboard(db_session, shanghai_user)
    utc = await _dashboard(db_session, utc_user)

    assert (
        shanghai["learning_dashboard"]["focus_sessions_7d"] == 0
    ), f"上海用户窗口起点=09-19 00:00，09-18 12:00 会话不计：{shanghai['learning_dashboard']}"
    assert utc["learning_dashboard"]["focus_sessions_7d"] == 1, (
        f"UTC 用户窗口起点=09-18 00:00，09-18 12:00 会话应计入；"
        f"修前窗口起点=09-18 23:30 把它漏计：{utc['learning_dashboard']}"
    )
