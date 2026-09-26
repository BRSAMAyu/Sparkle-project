"""V3-FIX-221（context_builder 余族）红绿测：_get_task_status_summary overdue 切用户本地日。

定界（wt507 207 同族，列级钟源沿 V3-FIX-37 实录）：Task.due_date 是客户端
给到的到期日（无时刻成分，墙上钟日界语义）。``_get_task_status_summary``
（context_builder.py:530）``Task.due_date < utcnow()`` 把 Date 列与 UTC
datetime 瞬间在 SQL 里直比——date 被升为当日零点，UTC+8 晚间（本地今日
08:00 后）「本地今日到期」任务被计 overdue；同文件 :1704 的 207 修面
（returning-context overdue 窗）之外的第二处。

修法：右值改用户本地日 ``local_date(utcnow(), tz)``（tz 沿 207 先例——
PushPreference.timezone 标量直查 + valid_timezone_name 缺省 Asia/Shanghai），
语义 due_date < 本地今日 才逾期。冻结钟（沿双冻结钟族）：
- NOW_EVENING = 2026-09-25 12:00 UTC（上海 = 09-25 20:00）：证晚间误报面——
  修前 ``due_date(09-25) < 09-25 12:00`` 为真，本地今日到期被计逾期；
- UTC 用户控制组：同一时刻 tz=UTC 的本地今日也是 09-25，修前同样误报，
  证修的不是上海特例而是钟源本身。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.orchestration.context_builder import ContextBuilderMixin

NOW_EVENING = dt.datetime(2026, 9, 25, 12, 0)  # naive UTC；上海本地 = 2026-09-25 20:00


async def _seed_user(db: AsyncSession, *, timezone: str | None = None) -> User:
    user = User(
        username=f"wt513-{uuid4().hex[:8]}",
        email=f"wt513-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    if timezone is not None:
        db.add(PushPreference(user_id=user.id, timezone=timezone))
        await db.commit()
    return user


async def _seed_due_tasks(db: AsyncSession, user_id, *, due_local_today: dt.date, due_yesterday: dt.date) -> None:
    db.add_all(
        [
            Task(
                user_id=user_id,
                title="wt513 due local-today",
                type=TaskType.LEARNING,
                status=TaskStatus.PENDING,
                due_date=due_local_today,
                estimated_minutes=20,
            ),
            Task(
                user_id=user_id,
                title="wt513 due yesterday",
                type=TaskType.LEARNING,
                status=TaskStatus.PENDING,
                due_date=due_yesterday,
                estimated_minutes=20,
            ),
        ]
    )
    await db.commit()


@pytest.mark.asyncio
async def test_overdue_summary_excludes_local_today_due_shanghai(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """上海晚间（本地 09-25 20:00）：本地今日（09-25）到期的待办不算逾期。

    修前 ``due_date < utcnow()``（09-25 12:00 瞬间）把 due 09-25 一并计逾
    → overdue=2；修后比用户本地日 09-25 → 只剩本地昨日（09-24）那 1 条。
    """
    monkeypatch.setattr("app.orchestration.context_builder.utcnow", lambda: NOW_EVENING)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    await _seed_due_tasks(
        db_session,
        user.id,
        due_local_today=dt.date(2026, 9, 25),
        due_yesterday=dt.date(2026, 9, 24),
    )

    summary = await ContextBuilderMixin._get_task_status_summary(
        object.__new__(ContextBuilderMixin), str(user.id), db_session
    )

    assert summary["overdue"] == 1, (
        f"overdue 应按用户本地日切：本地今日（09-25）到期不计逾期、本地昨日（09-24）计；"
        f"修前 Date 列与 UTC 瞬间 09-25 12:00 直比把今日到期也计入：{summary}"
    )
    assert summary["pending"] == 2, f"pending 计数不受本卡改动：{summary}"


@pytest.mark.asyncio
async def test_overdue_summary_excludes_local_today_due_utc_user(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """UTC 用户控制组：同一 UTC 瞬间下 tz=UTC 的本地今日（09-25）到期同样不算逾期。

    修前无 tz 概念，``due_date(09-25) < 09-25 12:00`` 对 UTC 用户同样误报
    overdue=2——证明这是钟源错切而非某市场特例。
    """
    monkeypatch.setattr("app.orchestration.context_builder.utcnow", lambda: NOW_EVENING)
    user = await _seed_user(db_session, timezone="UTC")
    await _seed_due_tasks(
        db_session,
        user.id,
        due_local_today=dt.date(2026, 9, 25),
        due_yesterday=dt.date(2026, 9, 24),
    )

    summary = await ContextBuilderMixin._get_task_status_summary(
        object.__new__(ContextBuilderMixin), str(user.id), db_session
    )

    assert (
        summary["overdue"] == 1
    ), f"tz=UTC 用户 overdue 同样应只含昨日到期：修前 UTC 瞬间直比把今日到期计入：{summary}"
