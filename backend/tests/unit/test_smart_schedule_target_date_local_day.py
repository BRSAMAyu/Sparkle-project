"""V3-FIX-320（修2b）红绿测：SmartScheduleService target_date 切用户本地日。

定界（wt604 普查 §3.1-7，列级钟源核实）：``CalendarEvent.start_time/end_time``
为客户端墙上钟 naive 直存（同修2a 定界）；``suggest_time_slots`` 的 naive
零点日窗与墙列**同钟自洽**（census 判定），唯独日源
``request.preferred_date or date.today()``（:49）是**宿主机本地日**
（V3-FIX-233 族残留）——UTC 宿主上海 00:00-08:00 时排程目标日落在本地昨日，
已有事件查窗错日、占用过滤失效。

修法（承 293 已裁决契约）：缺省日源改 ``local_date(utcnow(), tz)``（tz 沿
PushPreference.timezone 标量直查，缺省 Asia/Shanghai）；日窗端点保持 naive
与墙列同钟不动。冻结钟 NOW_LATE = 2026-09-25 17:00 UTC（上海本地 = 09-26
01:00）：本地今日（09-26）09:00-10:00 的墙钟事件必须挡掉该时段的槽位建议
（修前目标日=UTC 09-25 → 查不到该事件 → 09:00 槽位照推）；UTC 控制组
（tz=UTC）修前修后行为逐位不变。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_event import CalendarEvent
from app.models.user import PushPreference, User
from app.schemas.smart_schedule import SmartScheduleRequest
from app.services.smart_schedule_service import SmartScheduleService

NOW_LATE = dt.datetime(2026, 9, 25, 17, 0)  # naive UTC；上海本地 = 2026-09-26 01:00
LOCAL_TODAY = dt.date(2026, 9, 26)


class _FrozenDate(dt.date):
    """模块级 ``date`` 冻结子类：修前路径（date.today）可控且确定。"""

    @classmethod
    def today(cls) -> dt.date:
        return dt.date(2026, 9, 25)


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


async def _seed_busy_event(db: AsyncSession, user_id, *, day: dt.date) -> None:
    """目标日 09:00-10:00 的墙上钟事件（排程应避开的占用窗）。"""
    db.add(
        CalendarEvent(
            user_id=user_id,
            title="wt610 busy window",
            start_time=dt.datetime.combine(day, dt.time(9, 0)),
            end_time=dt.datetime.combine(day, dt.time(10, 0)),
            is_all_day=False,
            source="local",
        )
    )
    await db.commit()


def _freeze_module_clock(monkeypatch: pytest.MonkeyPatch, module) -> None:
    monkeypatch.setattr(module, "date", _FrozenDate)
    # 修后路径：模块将从 time_utils 导入 utcnow（修前无此名，raising=False 垫底）。
    monkeypatch.setattr(module, "utcnow", lambda: NOW_LATE, raising=False)


def _overlaps_busy_window(suggestion) -> bool:
    """槽位是否与 09:00-10:00 占用窗重叠（HH:MM 字典序即时比较）。"""
    return suggestion.start_time < "10:00" and suggestion.end_time > "09:00"


@pytest.mark.asyncio
async def test_suggest_time_slots_target_date_follows_user_local_day(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海 00:00-08:00：缺省目标日应为本地今日，且避开本地今日占用窗。"""
    import app.services.smart_schedule_service as smart_schedule_module

    _freeze_module_clock(monkeypatch, smart_schedule_module)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_busy_event(db_session, user.id, day=LOCAL_TODAY)

    response = await SmartScheduleService(db_session).suggest_time_slots(
        user.id,
        SmartScheduleRequest(estimated_minutes=60, preferred_date=None),
    )

    assert response.suggestions, "本地今日应有可排槽位"
    for suggestion in response.suggestions:
        assert suggestion.date == LOCAL_TODAY, (
            f"缺省排程目标日应为用户本地今日 {LOCAL_TODAY}"
            f"（修前宿主/UTC 日 09-25 = 本地昨日）：got {suggestion.date}"
        )
        assert not _overlaps_busy_window(suggestion), (
            f"本地今日 09:00-10:00 的墙钟事件应挡掉重叠槽位（修前目标日错日查窗漏事件）："
            f"{suggestion.start_time}-{suggestion.end_time}"
        )


@pytest.mark.asyncio
async def test_suggest_time_slots_utc_user_unchanged(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """UTC 控制组（同钟自洽）：目标日/占用过滤修前修后逐位不变。"""
    import app.services.smart_schedule_service as smart_schedule_module

    _freeze_module_clock(monkeypatch, smart_schedule_module)
    user = await _seed_user(db_session, timezone="UTC")
    await _seed_busy_event(db_session, user.id, day=dt.date(2026, 9, 25))

    response = await SmartScheduleService(db_session).suggest_time_slots(
        user.id,
        SmartScheduleRequest(estimated_minutes=60, preferred_date=None),
    )

    assert response.suggestions
    for suggestion in response.suggestions:
        assert suggestion.date == dt.date(2026, 9, 25)
        assert not _overlaps_busy_window(suggestion)
