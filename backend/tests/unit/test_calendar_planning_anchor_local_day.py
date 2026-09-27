"""V3-FIX-320（修2a）红绿测：CalendarService 规划窗 anchor 切用户本地日。

定界（wt604 普查 §3.1-6，列级钟源核实）：``CalendarEvent.start_time/end_time``
虽是 ``DateTime(timezone=True)`` 列类型，实际存客户端发来的无时区后缀本地
ISO（api/v1/calendar.py 直存 payload，wt582/wt602 取证）→ 读出 naive 墙上
钟。``get_busy_free_context`` 的窗口端点本就是 naive 零点（与墙列同钟），
但 anchor 缺省 ``datetime.utcnow().date()`` 是 **UTC 日**——上海 00:00-08:00
（= 前日 16:00-24:00Z）时 7 天忙闲规划窗起点落在本地昨日：``today`` 键指
昨天、第 7 天（本地）事件整日落窗外。

修法（承 293 已裁决契约）：anchor 缺省改 ``local_date(utcnow(), tz)``（tz
沿 PushPreference.timezone 标量直查，缺省 Asia/Shanghai，focus_service.
_local_today 先例）；窗口端点保持 naive 零点与墙列同钟不动。
冻结钟 NOW_LATE = 2026-09-25 17:00 UTC（上海本地 = 09-26 01:00）：
- ``payload["today"]`` 必须是本地今日 09-26（修前 09-25 = 本地昨日）；
- 本地第 7 天（10-02）的墙钟事件必须入 7 天窗（修前窗 [09-25, 10-02)
  整日漏掉）；
- UTC 控制组（tz=UTC）：修前修后行为逐位不变。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_event import CalendarEvent
from app.models.user import PushPreference, User
from app.services.calendar_service import CalendarService

NOW_LATE = dt.datetime(2026, 9, 25, 17, 0)  # naive UTC；上海本地 = 2026-09-26 01:00
LOCAL_TODAY = dt.date(2026, 9, 26)


class _FrozenDatetime(dt.datetime):
    """模块级 ``datetime`` 冻结子类：修前路径（datetime.utcnow）可控。"""

    @classmethod
    def utcnow(cls) -> dt.datetime:
        return NOW_LATE


async def _seed_user(db: AsyncSession, *, timezone: str | None = None) -> User:
    user = User(
        username=f"wt610-{uuid4().hex[:8]}",
        email=f"wt610-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if timezone is not None:
        db.add(PushPreference(user_id=user.id, timezone=timezone))
        await db.commit()
    return user


async def _seed_wall_event(
    db: AsyncSession, user_id, *, day: dt.date, title: str
) -> None:
    """墙上钟日历事件（客户端本地 naive 直存语义）：day 09:00-10:00（落在
    07:00-22:00 营业窗内，busy_minutes 计量可达）。"""
    db.add(
        CalendarEvent(
            user_id=user_id,
            title=title,
            start_time=dt.datetime.combine(day, dt.time(9, 0)),
            end_time=dt.datetime.combine(day, dt.time(10, 0)),
            is_all_day=False,
            source="local",
        )
    )
    await db.commit()


def _freeze_module_clock(monkeypatch: pytest.MonkeyPatch, module) -> None:
    monkeypatch.setattr(module, "datetime", _FrozenDatetime)
    # 修后路径：模块将从 time_utils 导入 utcnow（修前无此名，raising=False 垫底）。
    monkeypatch.setattr(module, "utcnow", lambda: NOW_LATE, raising=False)


@pytest.mark.asyncio
async def test_busy_free_context_anchor_follows_user_local_day(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海 00:00-08:00：规划窗 anchor 必须是本地今日，第 7 天事件不得漏。"""
    import app.services.calendar_service as calendar_service_module

    _freeze_module_clock(monkeypatch, calendar_service_module)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_wall_event(
        db_session, user.id, day=LOCAL_TODAY, title="wt610 local today event"
    )
    await _seed_wall_event(
        db_session, user.id, day=dt.date(2026, 10, 2), title="wt610 day7 event"
    )

    payload = await CalendarService(db_session).get_busy_free_context(user.id, days=7)

    assert payload["today"] == LOCAL_TODAY.isoformat(), (
        f"规划窗 anchor 应为用户本地今日 {LOCAL_TODAY}（修前 UTC 日 09-25 = 本地昨日）："
        f"today={payload['today']}"
    )
    assert len(payload["busy_events_by_date"].get(LOCAL_TODAY.isoformat(), [])) == 1, (
        "本地今日 09:00-10:00 的墙钟事件应计入今日桶"
    )
    assert len(payload["busy_events_by_date"].get("2026-10-02", [])) == 1, (
        "本地第 7 天（10-02）的墙钟事件应入 7 天窗（修前窗 [09-25, 10-02) 整日漏掉）"
    )
    assert payload["today_profile"]["busy_minutes"] == 60, (
        "今日画像忙闲分钟应来自本地今日事件（60 分钟）"
    )


@pytest.mark.asyncio
async def test_busy_free_context_utc_user_unchanged(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """UTC 控制组（同钟自洽）：anchor/窗口修前修后逐位不变。"""
    import app.services.calendar_service as calendar_service_module

    _freeze_module_clock(monkeypatch, calendar_service_module)
    user = await _seed_user(db_session, timezone="UTC")
    await _seed_wall_event(
        db_session, user.id, day=dt.date(2026, 9, 25), title="wt610 utc today event"
    )
    await _seed_wall_event(
        db_session, user.id, day=dt.date(2026, 10, 1), title="wt610 utc day7 event"
    )

    payload = await CalendarService(db_session).get_busy_free_context(user.id, days=7)

    assert payload["today"] == "2026-09-25"
    assert len(payload["busy_events_by_date"].get("2026-09-25", [])) == 1
    assert len(payload["busy_events_by_date"].get("2026-10-01", [])) == 1
    assert payload["today_profile"]["busy_minutes"] == 60
