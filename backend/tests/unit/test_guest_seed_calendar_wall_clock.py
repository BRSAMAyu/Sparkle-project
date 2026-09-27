"""V3-FIX-327 红绿测：guest_seed CalendarEvent 种子块切墙上钟构造。

定界（wt613 修 323 时的范围外发现；V3-FIX-37 墙上钟列契约 + wt608
calendar 日界端点同钟先例）：``_seed_guest_user_data`` 的 CalendarEvent
种子块 start/end 用 ``datetime(now.year, now.month, now.day, H, M,
tzinfo=UTC) ± timedelta(days=N)`` 构造——aware-UTC、以 **UTC 日**为
「今日」锚。而 CalendarEvent.start_time/end_time 是用户本地墙上钟列
（37 定界，wt608 已裁决同一列只与同一墙钟比较）：上海 00:00-08:00
（= 前日 16:00-24:00Z）窗播种时「明天 9:00」事件落本地**今日**、
「昨天 10:00」落在本地前日——种子事件整体错位一日，且 aware 构造与
墙上钟列混钟（生产 asyncpg/timestamptz 面未定义行为隐患）。

修法（承 323 同文件 ``today_local`` 锚 + 608 naive 墙上钟窗先例）：构造切
``datetime(today_local.year, today_local.month, today_local.day, H, M)
± timedelta(days=N)``——naive 墙上钟、本地日锚，与列语义同钟。

冻结钟形态沿 test_guest_seed_local_day.py：NOW_LATE = 2026-09-25 17:00
UTC（上海本地 = 09-26 01:00，错位窗）——修前「明天」事件按 UTC 明日
09-26 播种（= 本地今日，红），修后按本地明日 09-27 播种（绿）；
控制组 NOW_MID = 09-25 05:00 UTC（上海 09-25 13:00，双钟同日）修前
修后墙上钟逐位不变。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_event import CalendarEvent
from app.models.user import User
from app.services.guest_seed_service import seed_guest_user_data

NOW_LATE = dt.datetime(2026, 9, 25, 17, 0)  # naive UTC；上海本地 = 2026-09-26 01:00
NOW_MID = dt.datetime(2026, 9, 25, 5, 0)  # naive UTC；上海本地 = 2026-09-25 13:00
UTC_TODAY = dt.date(2026, 9, 25)
LOCAL_TODAY_LATE = dt.date(2026, 9, 26)  # NOW_LATE 的用户本地日


class _FrozenDatetime(dt.datetime):
    """模块级 ``datetime`` 冻结子类：种子内 utcnow 取受控 NOW。"""

    _frozen_now: dt.datetime = NOW_LATE

    @classmethod
    def utcnow(cls) -> dt.datetime:  # type: ignore[override]  # wt608 同款冻结替身
        return cls._frozen_now


async def _seed_guest(db: AsyncSession) -> User:
    guest = User(
        username=f"wt619-guest-{uuid4().hex[:6]}",
        email=f"wt619-guest-{uuid4().hex[:6]}@guest.local",
        hashed_password="hashed",
        password_login_enabled=False,
        nickname="访客",
        registration_source="guest",
        is_active=True,
    )
    db.add(guest)
    await db.commit()
    await db.refresh(guest)
    return guest


def _freeze_module_clock(monkeypatch: pytest.MonkeyPatch, module, now: dt.datetime) -> None:
    frozen_datetime = type("_FrozenDatetime", (_FrozenDatetime,), {"_frozen_now": now})
    monkeypatch.setattr(module, "datetime", frozen_datetime)
    monkeypatch.setattr(module, "date", dt.date, raising=False)


async def _calendar_events_by_title(db: AsyncSession, user_id, title: str) -> CalendarEvent:
    event = (
        await db.execute(select(CalendarEvent).where(CalendarEvent.user_id == user_id, CalendarEvent.title == title))
    ).scalar_one_or_none()
    assert event is not None, f"种子日历事件缺失：{title}"
    return event


@pytest.mark.asyncio
async def test_guest_seed_calendar_events_follow_local_wall_clock(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海 00:00-08:00 窗：种子事件 start/end 应按用户本地墙上钟播种。"""
    import app.services.guest_seed_service as guest_seed_module

    _freeze_module_clock(monkeypatch, guest_seed_module, NOW_LATE)
    guest = await _seed_guest(db_session)
    await seed_guest_user_data(db_session, guest)
    await db_session.commit()

    all_events = (
        (await db_session.execute(select(CalendarEvent).where(CalendarEvent.user_id == guest.id))).scalars().all()
    )
    assert len(all_events) >= 10
    for event in all_events:
        assert event.start_time.tzinfo is None and event.end_time.tzinfo is None, (
            f"墙上钟列（37 定界）种子值应为 naive：{event.title} got start={event.start_time!r}"
        )

    # 「明天 9:00-11:00」：本地明日 = 09-27（修前按 UTC 明日 09-26 = 本地今日，红）
    binary_tree = await _calendar_events_by_title(db_session, guest.id, "数据结构复习 — 二叉树专题")
    assert binary_tree.start_time == dt.datetime(2026, 9, 27, 9, 0), (
        f"「明天」事件应落本地明日（{LOCAL_TODAY_LATE + dt.timedelta(days=1)}）09:00 墙上钟"
        f"（修前按 UTC 日 09-25+1 播种落本地今日）：got {binary_tree.start_time!r}"
    )
    assert binary_tree.end_time == dt.datetime(2026, 9, 27, 11, 0), f"end 应同钟：got {binary_tree.end_time!r}"

    algo = await _calendar_events_by_title(db_session, guest.id, "算法刷题打卡")
    assert algo.start_time == dt.datetime(2026, 9, 27, 14, 0)
    assert algo.end_time == dt.datetime(2026, 9, 27, 16, 0)

    # 「昨天 10:00-12:00」：本地昨日 = 09-25（修前按 UTC 昨日 09-24 = 本地前日）
    lab = await _calendar_events_by_title(db_session, guest.id, "数据结构实验课")
    assert lab.start_time == dt.datetime(2026, 9, 25, 10, 0), f"「昨天」事件应落本地昨日 10:00：got {lab.start_time!r}"
    assert lab.end_time == dt.datetime(2026, 9, 25, 12, 0)

    # 「今日 7:30」晨读（无天数偏移）：本地今日 = 09-26
    morning = await _calendar_events_by_title(db_session, guest.id, "每日晨读")
    assert morning.start_time == dt.datetime(2026, 9, 26, 7, 30), (
        f"「今日」事件应落本地今日 07:30：got {morning.start_time!r}"
    )
    assert morning.end_time == dt.datetime(2026, 9, 26, 8, 0)


@pytest.mark.asyncio
async def test_guest_seed_calendar_wall_clock_unchanged_when_clocks_agree(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """控制组（UTC 日=上海日）：种子日历墙上钟修前修后逐位不变。"""
    import app.services.guest_seed_service as guest_seed_module

    _freeze_module_clock(monkeypatch, guest_seed_module, NOW_MID)
    guest = await _seed_guest(db_session)
    await seed_guest_user_data(db_session, guest)
    await db_session.commit()

    binary_tree = await _calendar_events_by_title(db_session, guest.id, "数据结构复习 — 二叉树专题")
    assert binary_tree.start_time == dt.datetime(2026, 9, 26, 9, 0), (
        f"双钟同日窗（UTC 09-25 05:00 = 上海 13:00）行为应不变：got {binary_tree.start_time!r}"
    )
    assert binary_tree.end_time == dt.datetime(2026, 9, 26, 11, 0)

    lab = await _calendar_events_by_title(db_session, guest.id, "数据结构实验课")
    assert lab.start_time == dt.datetime(2026, 9, 24, 10, 0)
    assert lab.end_time == dt.datetime(2026, 9, 24, 12, 0)
