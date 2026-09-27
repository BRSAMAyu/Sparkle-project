"""V3-FIX-323（修3）红绿测：guest_seed 混钟收口——种子日锚切用户本地日。

定界（wt604 普查 §3.1 余项）：``_seed_guest_user_data`` 同函数混两钟——
行时间戳（created_at/started_at/completed_at 等）用 ``datetime.utcnow()``
（UTC 钟），而 ``Plan.target_date`` / ``Task.due_date`` 的「今日+N」派生用
``date.today()``（**宿主机本地日**钟）。两个 Date 列都是用户面对的墙上日历
日：UTC 宿主在上海 00:00-08:00（= 前日 16:00-24:00Z）窗口播种时，「今日」
任务落本地昨日、计划目标日整体偏移一日；且随宿主时区漂移、不可复现。

修法（承 293/320 已裁决契约）：全函数「今日」锚统一
``local_date(now, DEFAULT_USER_TIMEZONE)``——访客无 PushPreference，按市
场缺省 Asia/Shanghai 口径（time_utils 对缺省/非法同此回落）。测试把模块级
``datetime``/``date`` 双钟各自冻结成分歧形态：NOW_LATE = 2026-09-25 17:00
UTC（上海本地 = 09-26 01:00），冻结 ``date.today()`` = UTC 日 09-25——修前
种子按 09-25 播种（红），修后按本地 09-26 播种（绿）；控制组 NOW_MID =
09-25 05:00 UTC（上海 09-25 13:00，双钟同日）修前修后逐位不变。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.task import Task
from app.models.user import User
from app.services.guest_seed_service import seed_guest_user_data

NOW_LATE = dt.datetime(2026, 9, 25, 17, 0)  # naive UTC；上海本地 = 2026-09-26 01:00
NOW_MID = dt.datetime(2026, 9, 25, 5, 0)  # naive UTC；上海本地 = 2026-09-25 13:00
UTC_TODAY = dt.date(2026, 9, 25)


class _FrozenDatetime(dt.datetime):
    """模块级 ``datetime`` 冻结子类：种子内 utcnow 取受控 NOW。"""

    _frozen_now: dt.datetime = NOW_LATE

    @classmethod
    def utcnow(cls) -> dt.datetime:
        return cls._frozen_now


class _FrozenDate(dt.date):
    """模块级 ``date`` 冻结子类：修前路径（date.today）钉在 UTC 日。"""

    @classmethod
    def today(cls) -> dt.date:
        return UTC_TODAY


async def _seed_guest(db: AsyncSession) -> User:
    guest = User(
        username=f"wt613-guest-{uuid4().hex[:6]}",
        email=f"wt613-guest-{uuid4().hex[:6]}@guest.local",
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
    # 修后模块不再 import date（日锚全走 local_date）；raising=False 垫底——
    # 若回归再引入 date.today()，此处冻结钟仍能钉住宿主钟，红测保持确定。
    monkeypatch.setattr(module, "date", _FrozenDate, raising=False)


@pytest.mark.asyncio
async def test_guest_seed_day_anchor_follows_market_default_local_day(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海 00:00-08:00 窗：种子 target_date/due_date 应按本地今日 09-26 播种。"""
    import app.services.guest_seed_service as guest_seed_module

    _freeze_module_clock(monkeypatch, guest_seed_module, NOW_LATE)
    guest = await _seed_guest(db_session)
    await seed_guest_user_data(db_session, guest)
    await db_session.commit()

    local_today = dt.date(2026, 9, 26)

    sprint_plan = (
        await db_session.execute(
            select(Plan).where(Plan.user_id == guest.id, Plan.name == "数据结构期中冲刺")
        )
    ).scalar_one_or_none()
    assert sprint_plan is not None
    assert sprint_plan.target_date == local_today + dt.timedelta(days=7), (
        f"冲刺计划目标日应=本地今日+7（{local_today + dt.timedelta(days=7)}）"
        f"（修前 date.today()=UTC 日 09-25 → 落 10-02）：got {sprint_plan.target_date}"
    )

    growth_plan = (
        await db_session.execute(
            select(Plan).where(Plan.user_id == guest.id, Plan.name == "计算机科学基础巩固")
        )
    ).scalar_one_or_none()
    assert growth_plan is not None
    assert growth_plan.target_date == local_today + dt.timedelta(days=90), (
        f"成长计划目标日应=本地今日+90：got {growth_plan.target_date}"
    )

    binary_tree_task = (
        await db_session.execute(
            select(Task).where(
                Task.user_id == guest.id, Task.title == "数据结构 - 二叉树遍历算法"
            )
        )
    ).scalar_one_or_none()
    assert binary_tree_task is not None
    assert binary_tree_task.due_date == local_today, (
        f"「今日」任务 due_date 应=本地今日 {local_today}"
        f"（修前落 UTC 日 09-25 = 本地昨日）：got {binary_tree_task.due_date}"
    )

    aze_plan = (
        await db_session.execute(select(Plan).where(Plan.name == "阿泽的树与图复盘计划"))
    ).scalar_one_or_none()
    assert aze_plan is not None
    assert aze_plan.target_date == local_today + dt.timedelta(days=5), (
        f"好友示范计划目标日应=本地今日+5：got {aze_plan.target_date}"
    )


@pytest.mark.asyncio
async def test_guest_seed_day_anchor_unchanged_when_clocks_agree(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """控制组（UTC 日=上海日）：种子日锚修前修后逐位不变。"""
    import app.services.guest_seed_service as guest_seed_module

    _freeze_module_clock(monkeypatch, guest_seed_module, NOW_MID)
    guest = await _seed_guest(db_session)
    await seed_guest_user_data(db_session, guest)
    await db_session.commit()

    sprint_plan = (
        await db_session.execute(
            select(Plan).where(Plan.user_id == guest.id, Plan.name == "数据结构期中冲刺")
        )
    ).scalar_one_or_none()
    assert sprint_plan is not None
    assert sprint_plan.target_date == UTC_TODAY + dt.timedelta(days=7), (
        f"双钟同日窗（UTC 09-25 05:00 = 上海 13:00）行为应不变：got {sprint_plan.target_date}"
    )
