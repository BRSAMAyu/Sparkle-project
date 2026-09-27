"""V3-FIX-318（calendar API UTC 日界端点直比墙上钟列）红绿测。

定界（wt604 时钟普查，证据 v3-output/WT604-CLOCK/census.md §3.1-1/2）：
- ``CalendarEvent.start_time/end_time`` 存客户端本地 ISO 串（无时区后缀）
  的**用户墙上钟 naive**（V3-FIX-37 定界，wt582/wt602 取证；aggregator 侧
  同列已在 eb14c205/027bb028 修完）。
- ``api/v1/calendar.py`` list_events 日期过滤（:74-80）把 ``start_date/
  end_date``（语义 = 用户本地日）构造成 **aware UTC 日界**
  （``datetime.combine(d, min/max).replace(tzinfo=UTC)``）与墙上钟列直比：
  生产 asyncpg/timestamptz 面上每日 16:00-24:00Z 窗口事件错日（上海
  00:00-08:00 最烈）；aware-vs-naive 直比在 asyncpg 属未定义行为面
  （DataError 族，time_utils.ensure_naive_utc 同源）。
- ``get_event_summary``（:170-188）``now=datetime.now(UTC)`` 后按 **UTC 日**
  切「今日」窗、按 UTC 瞬间切「未来 7 天」窗：上海 00:00-08:00（=前日
  16:00-24:00Z）的事件计入「昨日」、本地今日清晨缺席「今日」计数；
  upcoming 下界松 8h（已过去的本地今晚事件错进）、上界紧 8h（第 7 天
  本地晚间/次日凌晨事件错漏）——与 V3-FIX-300 week 窗口同构。

修法（沿 297/300 wall_clock 纪律）：
- list_events：日期参数即用户本地日，窗口直接用**同一墙钟**的本地日界
  naive（``datetime.combine(d, min/max)`` 不再 replace(tzinfo=UTC)）查墙上
  钟列——墙上钟窗对任意时区都是「该日 00:00-24:00 墙上钟」，无 UTC 换算
  面（tz 隐含在入参语义里，无需 _user_timezone 数值参与）。
- summary：「今日」改 time_utils.local_date + local_midnight_wall 按用户
  本地日界切（eb14c205 calendar「今日」同向）；「未来 7 天」端点经
  utc_naive_to_wall_clock 换成用户墙上钟入 WHERE（027bb028 同款，双射）。
  时区来源同款 push_preference.timezone 标量直查、缺省 Asia/Shanghai。

冻结钟（沿 test_state_aggregator_local_clock 双冻结钟族）：
- NOW = 2026-09-25 18:30 naive-UTC = 上海 2026-09-26 02:30——UTC 日与本地
  日岔开、now 时刻上下窗端点与墙上钟换算岔开 8 小时的正中缺陷面；经
  monkeypatch 模块级 ``datetime`` 类冻结（修前 ``datetime.now(UTC)`` 与
  修后同调用面，红绿同一冻结点）。UTC 用户同钟控制组钉住端点包含性
  （>=/<=）与修复不外溢。

可观测面说明：本仓测试基建是 SQLite（aiosqlite），绑定参数按分量字符串
落库（tzinfo 在 bind 时被剥掉，实测 aware/naive 存串相同）——list_events
的「选不中」错位在 SQLite 上不可复现（分量串比较下 UTC 日窗与本地日窗
恰同串），故 list_events 用 **Python 级绑定参数契约**（do_orm_execute 捕获
语句 compile().params：必须 naive 且等于本地日界墙上钟值）钉住 aware-UTC
构造面（asyncpg DataError 隐患 + 生产 timestamptz 错日本源）；summary 的
「今日/未来 7 天」错位（UTC 日 vs 本地日、瞬间 vs 墙上钟）在 SQLite 上
即行为级可复现，直接断言计数。
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.calendar import router as calendar_router
from app.db.session import get_db
from app.models.calendar_event import CalendarEvent
from app.models.user import PushPreference, User

NOW = dt.datetime(2026, 9, 25, 18, 30)  # naive UTC；上海本地 = 2026-09-26 02:30
NOW_AWARE = NOW.replace(tzinfo=dt.UTC)

LOCAL_DAY = dt.date(2026, 9, 26)  # 上海用户冻结钟下的本地今日


class _FrozenDatetime(dt.datetime):
    """模块级 datetime 冻结替身：now() 恒返 NOW_AWARE，其余行为原样。"""

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        if tz is not None:
            return NOW_AWARE
        return NOW


@pytest.fixture
def calendar_client(db_session):
    app = FastAPI()
    app.include_router(calendar_router, prefix="/calendar")

    state: dict[str, Any] = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


async def _seed_user(db: AsyncSession, *, timezone: str) -> User:
    user = User(
        username=f"wt608-{uuid4().hex[:8]}",
        email=f"wt608-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.flush()
    db.add(PushPreference(user_id=user.id, timezone=timezone))
    await db.commit()
    return user


async def _seed_event(
    db: AsyncSession,
    user_id,
    *,
    title: str,
    start: dt.datetime,
    end: dt.datetime,
) -> None:
    db.add(
        CalendarEvent(
            user_id=user_id,
            title=title,
            start_time=start,  # 客户端本地墙上钟列（无时区后缀 naive）
            end_time=end,
            source="manual",
        )
    )
    await db.commit()


# ---------------------------------------------------------------------------
# 端点 1：list_events 日期过滤（:74-80 aware UTC 日界 vs 墙上钟列）
# ---------------------------------------------------------------------------


async def test_list_events_binds_naive_wall_day_window_shanghai(db_session: AsyncSession, calendar_client):
    """上海用户按本地日查询：窗口绑定参数必须是本地日界墙上钟 naive。

    修前：datetime.combine(d, min/max).replace(tzinfo=UTC) —— 绑定参数带
    UTC tzinfo（asyncpg aware-vs-naive 未定义行为面、生产 timestamptz
    错日本源）→ 红。
    修后：同一墙钟本地日界 naive（09-26 00:00 / 09-26 23:59:59.999999）
    → 绿。选中集（本地日事件）两侧一致，作 sanity 钉。
    """
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_event(
        db_session,
        user.id,
        title="local-morning",
        start=dt.datetime(2026, 9, 26, 8, 0),
        end=dt.datetime(2026, 9, 26, 9, 0),
    )
    await _seed_event(
        db_session,
        user.id,
        title="local-evening",
        start=dt.datetime(2026, 9, 26, 20, 0),
        end=dt.datetime(2026, 9, 26, 21, 0),
    )
    await _seed_event(
        db_session,
        user.id,
        title="prev-day",
        start=dt.datetime(2026, 9, 25, 10, 0),
        end=dt.datetime(2026, 9, 25, 11, 0),
    )
    await _seed_event(
        db_session,
        user.id,
        title="next-day",
        start=dt.datetime(2026, 9, 27, 10, 0),
        end=dt.datetime(2026, 9, 27, 11, 0),
    )

    client, state = calendar_client
    state["current_user"] = user

    captured: list[Any] = []

    def _capture(orm_state: Any) -> None:
        if orm_state.is_select:
            captured.append(orm_state.statement)

    event.listen(Session, "do_orm_execute", _capture)
    try:
        response = client.get("/calendar", params={"start_date": "2026-09-26", "end_date": "2026-09-26"})
    finally:
        event.remove(Session, "do_orm_execute", _capture)

    assert response.status_code == 200
    titles = {item["title"] for item in response.json()["data"]}
    assert titles == {"local-morning", "local-evening"}, f"本地日事件应恰选中 2 条，实得 {titles}"

    assert captured, "未捕获到 list_events 的 SELECT 语句"
    datetime_params: list[dt.datetime] = []
    for stmt in captured:
        for value in stmt.compile().params.values():
            if isinstance(value, dt.datetime):
                datetime_params.append(value)

    assert datetime_params, "日期过滤未下发任何 datetime 绑定参数"
    for value in datetime_params:
        assert value.tzinfo is None, (
            f"日期窗绑定参数应为 naive 墙上钟值，实得 aware {value!r}"
            "（asyncpg aware-vs-naive 未定义行为面，V3-FIX-318）"
        )
    assert set(datetime_params) == {
        dt.datetime(2026, 9, 26, 0, 0),
        dt.datetime(2026, 9, 26, 23, 59, 59, 999999),
    }, f"日期窗应钉在本地日界墙上钟 09-26 00:00/23:59:59.999999，实得 {datetime_params}"


# ---------------------------------------------------------------------------
# 端点 2：get_event_summary（:170-188 UTC 日「今日」+ UTC 瞬间「未来 7 天」）
# ---------------------------------------------------------------------------


async def test_summary_today_counts_user_local_day_shanghai(db_session: AsyncSession, calendar_client, monkeypatch):
    """上海用户「今日事件数」按本地日计：本地今日清晨/晚间计入、昨日晚间不计。

    冻结钟 NOW=09-25 18:30Z（上海 09-26 02:30）：
    - today-early 09-26 02:00 与 today-evening 09-26 20:00（本地今日）→ 计入；
    - yesterday-evening 09-25 20:00（本地昨日）→ 不计入 → today == 2。
    修前 UTC 日窗 [09-25 00:00, 23:59:59] 只圈中 yesterday-evening → 1 → 红。
    """
    monkeypatch.setattr("app.api.v1.calendar.datetime", _FrozenDatetime)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_event(
        db_session,
        user.id,
        title="yesterday-evening",
        start=dt.datetime(2026, 9, 25, 20, 0),
        end=dt.datetime(2026, 9, 25, 21, 0),
    )
    await _seed_event(
        db_session,
        user.id,
        title="today-early",
        start=dt.datetime(2026, 9, 26, 2, 0),
        end=dt.datetime(2026, 9, 26, 3, 0),
    )
    await _seed_event(
        db_session,
        user.id,
        title="today-evening",
        start=dt.datetime(2026, 9, 26, 20, 0),
        end=dt.datetime(2026, 9, 26, 21, 0),
    )

    client, state = calendar_client
    state["current_user"] = user
    response = client.get("/calendar/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["today"] == 2, (
        f"今日计数应按用户本地日（09-26）=2（early+evening），实得 {body['today']}"
        "（修前按 UTC 日 09-25 切窗错计昨日晚间）"
    )


async def test_summary_upcoming_wall_window_shanghai(db_session: AsyncSession, calendar_client, monkeypatch):
    """上海用户「未来 7 天」端点换墙上钟：已过去的本地今晚不进、第 7 天本地凌晨不漏。

    - past-evening-a/b 09-25 20:00/21:00（绝对 09-25T12:00/13:00Z，早于 now
      18:30Z）→ 不计入；修前 naive 直比 >= 09-25 18:30 → 错进（下界松 8h）。
    - last-night 10-03 01:00（绝对 10-02T17:00Z，在 end=10-02T23:59:59Z 前）
      → 计入；修前 naive 直比 10-03 01:00 > 10-02 23:59:59 → 错漏（上界紧 8h）。
    - mid-week 09-30 10:00 → 计入。upcoming == 2（mid-week+last-night）。
    """
    monkeypatch.setattr("app.api.v1.calendar.datetime", _FrozenDatetime)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_event(
        db_session,
        user.id,
        title="past-evening-a",
        start=dt.datetime(2026, 9, 25, 20, 0),
        end=dt.datetime(2026, 9, 25, 21, 0),
    )
    await _seed_event(
        db_session,
        user.id,
        title="past-evening-b",
        start=dt.datetime(2026, 9, 25, 21, 0),
        end=dt.datetime(2026, 9, 25, 22, 0),
    )
    await _seed_event(
        db_session,
        user.id,
        title="mid-week",
        start=dt.datetime(2026, 9, 30, 10, 0),
        end=dt.datetime(2026, 9, 30, 11, 0),
    )
    await _seed_event(
        db_session,
        user.id,
        title="last-night",
        start=dt.datetime(2026, 10, 3, 1, 0),
        end=dt.datetime(2026, 10, 3, 2, 0),
    )

    client, state = calendar_client
    state["current_user"] = user
    response = client.get("/calendar/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["upcoming"] == 2, (
        f"未来 7 天应含 mid-week+last-night=2，实得 {body['upcoming']}"
        "（修前下界松 8h 错进 past-evening、上界紧 8h 错漏 last-night）"
    )


# ---------------------------------------------------------------------------
# UTC 控制组：墙上钟 = UTC 钟同钟，端点包含性（>=/<=）钉住、修复不外溢
# ---------------------------------------------------------------------------


async def test_summary_today_utc_control_preserves_utc_day(db_session: AsyncSession, calendar_client, monkeypatch):
    """UTC 用户：本地日=UTC 日，「今日」窗 [09-25 00:00, 23:59:59] 两侧一致 → 3。"""
    monkeypatch.setattr("app.api.v1.calendar.datetime", _FrozenDatetime)
    user = await _seed_user(db_session, timezone="UTC")
    await _seed_event(
        db_session,
        user.id,
        title="early",
        start=dt.datetime(2026, 9, 25, 0, 30),
        end=dt.datetime(2026, 9, 25, 1, 30),
    )
    await _seed_event(
        db_session,
        user.id,
        title="midday",
        start=dt.datetime(2026, 9, 25, 12, 0),
        end=dt.datetime(2026, 9, 25, 13, 0),
    )
    await _seed_event(
        db_session,
        user.id,
        title="late",
        start=dt.datetime(2026, 9, 25, 23, 0),
        end=dt.datetime(2026, 9, 25, 23, 30),
    )
    await _seed_event(
        db_session,
        user.id,
        title="next-day",
        start=dt.datetime(2026, 9, 26, 2, 0),
        end=dt.datetime(2026, 9, 26, 3, 0),
    )

    client, state = calendar_client
    state["current_user"] = user
    response = client.get("/calendar/summary")

    assert response.status_code == 200
    assert response.json()["today"] == 3


async def test_summary_upcoming_utc_control_boundary(db_session: AsyncSession, calendar_client, monkeypatch):
    """UTC 用户：upcoming 端点包含性钉住——now 整点/末日晚 23:00 进，前后 30 分钟出 → 2。"""
    monkeypatch.setattr("app.api.v1.calendar.datetime", _FrozenDatetime)
    user = await _seed_user(db_session, timezone="UTC")
    await _seed_event(
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
        start=dt.datetime(2026, 9, 25, 18, 0),
        end=dt.datetime(2026, 9, 25, 18, 15),
    )
    await _seed_event(
        db_session,
        user.id,
        title="near-end",
        start=dt.datetime(2026, 10, 2, 23, 0),
        end=dt.datetime(2026, 10, 2, 23, 30),
    )
    await _seed_event(
        db_session,
        user.id,
        title="after-end",
        start=dt.datetime(2026, 10, 3, 0, 30),
        end=dt.datetime(2026, 10, 3, 1, 30),
    )

    client, state = calendar_client
    state["current_user"] = user
    response = client.get("/calendar/summary")

    assert response.status_code == 200
    assert response.json()["upcoming"] == 2
