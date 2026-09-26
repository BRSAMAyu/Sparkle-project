"""V3-FIX-211（struggle_signal_aggregator 墙钟余族）红绿测：「今日」窗口按列定钟 + overdue 切本地日。

定界（V3-FIX-37 双存储钟实录 + 本卡逐列核）：
- ``_collect_signals`` 修前 ``today_start = combine(_utcnow().date(), 0:00)``
  （UTC 日零点，:166-168）同时喂两类列：
  * ``_short_session_counts``（:255）比 ``FocusSession.start_time``（墙上
    钟列）——跨钟且「今日」是 UTC 日，UTC+8 晨间漏计本地今日凌晨会话；
  * ``_task_skip_counts`` 比 ``Task.created_at``/``updated_at``（UTC 存储
    列）——无跨钟但「今日」是 UTC 日：UTC+8 晨间（UTC 尚在前日）把本地
    昨日傍晚的任务多计进「今日」。
- ``_overdue_task_count``/``_days_behind``：``Task.due_date`` 是客户端给到
  的到期日（V3-FIX-37 定界：墙上钟日界语义），修前比 UTC date/UTC 日零点
  ——UTC+8 晨间把「本地昨日到期」漏计逾期（V3-FIX-207 同族，同文件顺手
  按 207 教义收口）；
- ``_error_counts_3d``/``_completion_gap`` 是 UTC 列 × UTC 钟的同钟比较，
  无跨钟，本卡不动。

修法：今日窗口按列分端点——墙钟列 ``local_midnight_wall(local_today)``
（+1d 为界），UTC 列 ``local_midnight_as_utc_naive(local_today, tz)``；
overdue/days_behind 比用户本地日（207 教义）。

冻结钟 NOW_LATE = 2026-09-24 20:00 UTC（上海 = 09-25 04:00，UTC 尚在前日）：
- 本地今日（09-25）凌晨 03:00 的 3 分钟会话必须计入「今日短会话」；
- 本地昨日 22:00（=09-24 14:00Z）创建的 ABANDONED 任务必须出「今日」窗；
- 本地昨日到期（09-24）的待办必须计逾期、days_behind 均值 1.5。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.focus import FocusSession, FocusStatus
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.services.struggle_signal_aggregator import StruggleSignalAggregator

NOW_LATE = dt.datetime(2026, 9, 24, 20, 0)  # naive UTC；上海本地 = 2026-09-25 04:00


async def _seed_user_and_plan(db: AsyncSession, *, timezone: str | None = None) -> tuple[User, Plan]:
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"wt507-{user_id.hex[:8]}",
        email=f"wt507-{user_id.hex[:8]}@test.local",
        hashed_password="x",
    )
    plan = Plan(
        id=uuid4(),
        user_id=user_id,
        name="wt507 struggle plan",
        type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
        priority=PlanPriority.NORMAL,
        is_active=True,
    )
    db.add_all([user, plan])
    await db.commit()
    await db.refresh(user)
    if timezone is not None:
        db.add(PushPreference(user_id=user.id, timezone=timezone))
        await db.commit()
    return user, plan


async def _seed_task(db: AsyncSession, user, plan, *, status: TaskStatus, due_date=None, created_at=None) -> Task:
    task = Task(
        id=uuid4(),
        user_id=user.id,
        plan_id=plan.id,
        title=f"wt507 task {uuid4().hex[:6]}",
        type=TaskType.LEARNING,
        status=status,
        due_date=due_date,
        estimated_minutes=20,
        difficulty=2,
        energy_cost=2,
        created_at=created_at or dt.datetime(2026, 9, 20, 6, 0),
        updated_at=created_at or dt.datetime(2026, 9, 20, 6, 0),
    )
    db.add(task)
    await db.commit()
    return task


async def test_short_session_today_window_uses_local_wall_midnight(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海晨间（本地 09-25 04:00）：本地今日凌晨的短会话必须计入「今日短会话」。

    修前窗口 = UTC 日 [09-24 00:00Z, 09-25 00:00Z) 直比墙上钟列：墙上
    09-25 03:00 不在界内被漏计；修后窗口 = 墙上 [09-25 00:00, 09-26 00:00)。
    """
    monkeypatch.setattr("app.services.struggle_signal_aggregator._utcnow", lambda: NOW_LATE)
    user, plan = await _seed_user_and_plan(db_session, timezone="Asia/Shanghai")
    task = await _seed_task(db_session, user, plan, status=TaskStatus.PENDING)
    db_session.add(
        FocusSession(
            user_id=user.id,
            task_id=task.id,
            # start_time 是客户端本地墙上钟列（无时区后缀 naive）
            start_time=dt.datetime(2026, 9, 25, 3, 0),
            end_time=dt.datetime(2026, 9, 25, 3, 3),
            duration_minutes=3,
            status=FocusStatus.COMPLETED,
        )
    )
    await db_session.commit()

    signals = await StruggleSignalAggregator()._collect_signals(db_session, user_id=str(user.id), plan_id=str(plan.id))

    assert signals.total_sessions == 1, (
        f"「今日」短会话窗口应按用户本地墙钟日界（09-25 00:00 墙上零点起）；"
        f"修前 UTC 日零点直比墙上钟列把本地今日凌晨会话漏计：{signals.to_dict()}"
    )
    assert signals.short_sessions == 1, f"3 分钟会话应计短会话：{signals.to_dict()}"


async def test_task_skip_today_window_uses_local_day_in_utc(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """上海晨间（本地 09-25 04:00）：本地昨日傍晚创建的任务必须出「今日」窗。

    Task.created_at 是 UTC 存储列：本地昨日（09-24）22:00 = 09-24 14:00Z。
    修前窗口 = UTC 日 [09-24 00:00Z, 09-25 00:00Z) 把它多计进「今日」；
    修后窗口 = 本地今日换算的 UTC 瞬间 [09-24 16:00Z, 09-25 16:00Z) → 不计。
    本地今日清晨（09-25 04:30 = 09-24 20:30Z）创建的 ABANDONED 任务两版都
    计入（防「修成全排」假绿）。
    """
    monkeypatch.setattr("app.services.struggle_signal_aggregator._utcnow", lambda: NOW_LATE)
    user, plan = await _seed_user_and_plan(db_session, timezone="Asia/Shanghai")
    await _seed_task(
        db_session,
        user,
        plan,
        status=TaskStatus.ABANDONED,
        created_at=dt.datetime(2026, 9, 24, 14, 0),  # 本地昨日 22:00
    )
    await _seed_task(
        db_session,
        user,
        plan,
        status=TaskStatus.ABANDONED,
        created_at=dt.datetime(2026, 9, 24, 20, 30),  # 本地今日 04:30
    )

    signals = await StruggleSignalAggregator()._collect_signals(db_session, user_id=str(user.id), plan_id=str(plan.id))

    assert signals.today_total == 1, (
        f"「今日」窗对 UTC 存储列应换算本地日界（local_midnight_as_utc_naive）：只计本地今日创建的任务；"
        f"修前 UTC 日界把本地昨日 22:00 的任务多计：{signals.to_dict()}"
    )
    assert signals.today_skipped == 1, f"本地今日创建的 ABANDONED 任务应计 skip：{signals.to_dict()}"


async def test_overdue_and_days_behind_follow_user_local_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """上海晨间（本地 09-25 04:00）：本地昨日/前日到期的待办必须计逾期。

    修前 overdue 比 ``now.date()``=09-24（UTC date）、days_behind 同源：
    due 09-24 被漏计（逾期数 1 而非 2、均值 1.0 而非 1.5）。
    """
    monkeypatch.setattr("app.services.struggle_signal_aggregator._utcnow", lambda: NOW_LATE)
    user, plan = await _seed_user_and_plan(db_session, timezone="Asia/Shanghai")
    await _seed_task(db_session, user, plan, status=TaskStatus.PENDING, due_date=dt.date(2026, 9, 24))
    await _seed_task(db_session, user, plan, status=TaskStatus.PENDING, due_date=dt.date(2026, 9, 23))

    context = await StruggleSignalAggregator().get_struggle_context(
        db_session, user_id=str(user.id), plan_id=str(plan.id)
    )

    assert context["overdue_tasks"] == 2, (
        f"overdue 应按用户本地日（09-25）切：due 09-24 与 09-23 都逾期；"
        f"修前比 UTC date 09-24 把本地昨日到期任务漏计：{context['overdue_tasks']}"
    )
    assert (
        context["days_behind"] == 1.5
    ), f"days_behind 应按用户本地日均值 (1+2)/2=1.5；修前把 due 09-24 漏计只算 (1)/1=1.0：{context['days_behind']}"
