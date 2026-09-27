"""V3-FIX-329（dashboard flame 卡时钟族修漏）红绿测：今日桶与 days_left 切用户本地日。

定界（wt624 B-02 审计 F2；37/197/209/211 同族余量）：
- ``_get_today_completed_task_minutes``/``_get_today_completed_tasks`` 修前
  ``today_start = _utcnow().replace(hour=0, …)`` 是 naive-UTC 零点，直比
  ``Task.completed_at``（UTC 存储列，V3-FIX-37 定界）——UTC+8 晨间
  （本地 00:00-08:00，UTC 尚在前日）今日桶混入本地昨日 08:00-24:00 全部
  完成量（过计面），同屏 streak（本地日，V3-FIX-211 已修）与 flame 卡互相
  矛盾；UTC 负偏移时区（纽约等）晚间 UTC 日期先行翻转，本地今日傍晚完成
  整段漏计（漏计面）；
- ``_get_active_sprint`` 的 ``days_left`` 修前 ``plan.target_date -
  _utcnow().date()`` 是 UTC 日——上海晨间 deadline=本地今日时算 1 而非 0，
  sprint→weather 规则（<3 天且进度低 → rainy）随之误报。

修法（沿 calendar_service V3-FIX-320 / growth V3-FIX-211 先例）：
``local_date`` 取用户本地今日 + ``local_midnight_as_utc_naive`` 换算 UTC
存储列窗口起点；时区沿 wt608 先例 PushPreference.timezone 标量直查、缺省
Asia/Shanghai。本卡只修日界不改数据源语义（focus 实为任务 actual_minutes
而非 FocusSession——命名面由 V3-FIX-332 改名 today_completed_task_minutes
收口）。

冻结钟（沿双冻结钟族）：NOW_LATE = 2026-09-25 20:00 UTC（上海 = 09-26
04:00 晨间窗口）；UTC 控制组用户双版桶位不变。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.services.dashboard_service import DashboardService

NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；上海本地 = 2026-09-26 04:00


def _freeze(monkeypatch: pytest.MonkeyPatch, now: dt.datetime) -> None:
    monkeypatch.setattr("app.services.dashboard_service._utcnow", lambda: now)


async def _seed_user(db: AsyncSession, *, timezone: str | None = None) -> User:
    user = User(
        username=f"wt627-{uuid4().hex[:8]}",
        email=f"wt627-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if timezone is not None:
        db.add(PushPreference(user_id=user.id, timezone=timezone))
        await db.commit()
    return user


async def _seed_completed_task(
    db: AsyncSession,
    user_id,
    *,
    completed_at: dt.datetime,
    actual_minutes: int,
) -> Task:
    task = Task(
        user_id=user_id,
        title=f"wt627-{completed_at.isoformat()}",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        completed_at=completed_at,  # UTC 存储列（服务端 utcnow 写入惯例）
        actual_minutes=actual_minutes,
        estimated_minutes=actual_minutes,
    )
    db.add(task)
    await db.commit()
    return task


async def test_flame_today_buckets_follow_user_local_day(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海晨间（本地 09-26 04:00）：本地昨日白天的任务必须移出今日桶。

    冻结 NOW=09-25 20:00Z，修前 today_start=09-25 00:00Z（UTC 日界，比本地
    零点早 16h）：本地昨日（09-25）上午 10:00（= 09-25 02:00Z）完成的 30
    分钟任务仍留在「今日」桶、昨日 20:00（= 09-25 12:00Z）同理——桶内混入
    本地昨日 08:00-24:00 全部完成量（75/2），与同屏 streak（本地日，V3-FIX-
    211 已修）互相矛盾；修后窗口起点=本地零点 09-26 00:00（= 09-25 16:00Z），
    只剩本地今日凌晨 01:00（= 09-25 17:00Z）的 45 分钟任务（45/1）。
    """
    _freeze(monkeypatch, NOW_LATE)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    # 本地今日（09-26）凌晨 01:00 完成 45 分钟——双版都计入
    await _seed_completed_task(
        db_session, user.id, completed_at=dt.datetime(2026, 9, 25, 17, 0), actual_minutes=45
    )
    # 本地昨日（09-25）上午 10:00 完成 30 分钟——修前误计入今日桶
    await _seed_completed_task(
        db_session, user.id, completed_at=dt.datetime(2026, 9, 25, 2, 0), actual_minutes=30
    )
    # 本地昨日（09-25）晚间 20:00 完成 20 分钟——修前误计入今日桶
    await _seed_completed_task(
        db_session, user.id, completed_at=dt.datetime(2026, 9, 25, 12, 0), actual_minutes=20
    )
    # 本地前日（09-24）——双版都排除（防窗口过宽）
    await _seed_completed_task(
        db_session, user.id, completed_at=dt.datetime(2026, 9, 24, 12, 0), actual_minutes=20
    )

    service = DashboardService(db_session)

    completed_task_minutes = await service._get_today_completed_task_minutes(user.id)
    completed_count = await service._get_today_completed_tasks(user.id)

    assert completed_task_minutes == 45, (
        f"上海晨间今日桶应按本地零点（09-26 00:00 = 09-25 16:00Z）只计凌晨任务 45 分钟；"
        f"修前 UTC 日界（09-25 00:00Z）把本地昨日白天 50 分钟误计入今日桶：{completed_task_minutes}"
    )
    assert completed_count == 1, (
        f"本地今日完成任务数应为 1；修前把本地昨日 2 条任务计入今日桶得 3：{completed_count}"
    )


async def test_flame_today_buckets_negative_offset_local_evening(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """纽约晚间（UTC-4，本地 09-25 20:00 = 09-26 00:00Z）：本地今日傍晚完成必须计入。

    西半球面：UTC 日期已翻到 09-26 而本地还是 09-25，修前 today_start=
    09-26 00:00Z 把本地今日 19:00（= 09-25 23:00Z）的 60 分钟任务整段漏计
    （0/0）；修后窗口起点=本地零点 09-25 00:00（NY）= 09-25 04:00Z，计入
    （60/1）。
    """
    _freeze(monkeypatch, dt.datetime(2026, 9, 26, 0, 0))  # 纽约本地 = 09-25 20:00
    user = await _seed_user(db_session, timezone="America/New_York")
    # 本地今日（09-25）19:00 完成 60 分钟——修前漏计
    await _seed_completed_task(
        db_session, user.id, completed_at=dt.datetime(2026, 9, 25, 23, 0), actual_minutes=60
    )
    # 本地昨日（09-24）18:00 完成 30 分钟——双版都排除
    await _seed_completed_task(
        db_session, user.id, completed_at=dt.datetime(2026, 9, 24, 22, 0), actual_minutes=30
    )

    service = DashboardService(db_session)

    completed_task_minutes = await service._get_today_completed_task_minutes(user.id)
    completed_count = await service._get_today_completed_tasks(user.id)

    assert completed_task_minutes == 60, (
        f"纽约晚间今日桶应按本地零点（09-25 04:00Z）计入傍晚 60 分钟；"
        f"修前 UTC 日界（09-26 00:00Z）把本地今日任务整段漏计：{completed_task_minutes}"
    )
    assert completed_count == 1, f"本地今日完成任务数应为 1；修前 UTC 日界漏计得 0：{completed_count}"


async def test_flame_today_buckets_utc_user_unchanged(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """UTC 控制组：UTC 用户今日桶双版一致（修法不得移动 UTC 用户桶位）。

    冻结 NOW=09-25 20:00Z，UTC 用户本地面=UTC 面（local_date(…, "UTC")
    =09-25），窗口起点双版均为 09-25 00:00Z。
    """
    _freeze(monkeypatch, NOW_LATE)
    user = await _seed_user(db_session, timezone="UTC")
    # UTC 今日（09-25）02:00 完成 55 分钟——双版都计入
    await _seed_completed_task(
        db_session, user.id, completed_at=dt.datetime(2026, 9, 25, 2, 0), actual_minutes=55
    )
    # UTC 昨日（09-24）23:00 完成 40 分钟——双版都排除
    await _seed_completed_task(
        db_session, user.id, completed_at=dt.datetime(2026, 9, 24, 23, 0), actual_minutes=40
    )

    service = DashboardService(db_session)

    assert await service._get_today_completed_task_minutes(user.id) == 55, "UTC 用户今日桶应保持 UTC 日界不变"
    assert await service._get_today_completed_tasks(user.id) == 1, "UTC 用户完成数应保持 UTC 日界不变"


async def test_sprint_days_left_follows_user_local_day(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海晨间：sprint deadline=本地今日（09-26）时 days_left 应为 0。

    修前 ``_utcnow().date()``=UTC 日 09-25，target=09-26 算出 1——「今日截止」
    被误报成「还剩一天」，sprint→weather 规则（days_left<3 且进度<0.5 →
    rainy「临近截止日」）随之提前误报。
    """
    _freeze(monkeypatch, NOW_LATE)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    db_session.add(
        Plan(
            user_id=user.id,
            name="wt627-sprint-due-local-today",
            type=PlanType.SPRINT,
            target_date=dt.date(2026, 9, 26),  # 本地今日；UTC 日 09-25 的「明天」
            progress=0.2,
            is_active=True,
        )
    )
    await db_session.commit()

    sprint = await DashboardService(db_session)._get_active_sprint(user.id)

    assert sprint is not None
    assert sprint["days_left"] == 0, (
        f"deadline=本地今日（09-26）days_left 应为 0；修前 UTC 日（09-25）算出 1：{sprint}"
    )


async def test_sprint_days_left_utc_user_unchanged(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """UTC 控制组：UTC 用户的 days_left 双版一致（本地面=UTC 面重合）。"""
    _freeze(monkeypatch, NOW_LATE)
    user = await _seed_user(db_session, timezone="UTC")
    db_session.add(
        Plan(
            user_id=user.id,
            name="wt627-sprint-utc-control",
            type=PlanType.SPRINT,
            target_date=dt.date(2026, 9, 26),  # UTC 今日
            progress=0.2,
            is_active=True,
        )
    )
    await db_session.commit()

    sprint = await DashboardService(db_session)._get_active_sprint(user.id)

    assert sprint is not None
    assert sprint["days_left"] == 1, "UTC 用户（本地面=UTC 面）days_left 应保持 1 不变"
