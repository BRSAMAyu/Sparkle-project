"""V3-FIX-233（plan_adjustment 面）红绿测：到期窗 cutoff 切用户本地日。

定界（wt513 221 同族余量，233 登记面 4）：``_fetch_upcoming_tasks``
的 ``cutoff = date.today() + LOOKAHEAD_DAYS``（plan_adjustment_applier.py
:656）是宿主机本地日，流入 :664 ``Task.due_date <= cutoff``——上海凌晨
（本地已次日）把窗口末日的本地到期任务排除（漏 patch）。

修法：cutoff 基准改 ``local_date(utcnow(), tz)``（tz 沿 207/211/221 先例
——PushPreference.timezone 标量直查 + valid_timezone_name 缺省
Asia/Shanghai）。冻结钟（沿双冻结钟族）：冻结 NOW=09-25 20:00Z（上海
本地今日=09-26）+ 冻结宿主机 date.today()=09-25，LOOKAHEAD_DAYS=3：
- due 09-29（本地今日+3，恰在窗口末日）必须入选（修前 cutoff=09-25+3
  =09-28，09-29 被排除）；
- due 09-27 双版都入选（控制组）。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.services.plan_adjustment_applier import PlanAdjustmentApplier

NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；上海本地 = 2026-09-26 04:00


async def _seed_user(db: AsyncSession, *, timezone: str | None = None) -> User:
    user = User(
        username=f"wt519-{uuid4().hex[:8]}",
        email=f"wt519-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if timezone is not None:
        db.add(PushPreference(user_id=user.id, timezone=timezone))
        await db.commit()
    return user


def _freeze_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.plan_adjustment_applier.utcnow", lambda: NOW_LATE, raising=False)

    class _FrozenDate(dt.date):
        @classmethod
        def today(cls) -> dt.date:
            return dt.date(2026, 9, 25)  # 宿主机本地日（+8 时区下此刻真实值）

    # 修前宿主机钟走模块内 date.today()（红态种子）；修后模块不再导入 date
    # （时钟路径只有 utcnow），raising=False 允许缺种。
    monkeypatch.setattr("app.services.plan_adjustment_applier.date", _FrozenDate, raising=False)


@pytest.mark.asyncio
async def test_lookahead_window_follows_user_local_day(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海凌晨（本地 09-26 04:00）：窗口末日（本地今日+3=09-29）到期任务须入选。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    plan_id = uuid4()
    edge = Task(
        user_id=user.id,
        plan_id=plan_id,
        title="wt519 due window-edge",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        due_date=dt.date(2026, 9, 29),  # 本地今日 + LOOKAHEAD_DAYS，修前 cutoff=09-28 排除
        order_index=1,
        estimated_minutes=20,
    )
    control = Task(
        user_id=user.id,
        plan_id=plan_id,
        title="wt519 due in-window control",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        due_date=dt.date(2026, 9, 27),
        order_index=2,
        estimated_minutes=20,
    )
    db_session.add_all([edge, control])
    await db_session.commit()

    upcoming = await PlanAdjustmentApplier(db_session)._fetch_upcoming_tasks(user.id, plan_id)

    titles = {task.title for task in upcoming}
    assert "wt519 due window-edge" in titles, (
        f"窗口末日（本地今日+3=09-29）到期任务应入选 patch 候选；"
        f"修前 cutoff=宿主机日 09-25+3=09-28 把它排除：{sorted(titles)}"
    )
    assert "wt519 due in-window control" in titles, f"窗内到期任务仍须入选（控制组）：{sorted(titles)}"
