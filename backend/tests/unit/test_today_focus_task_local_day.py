"""V3-FIX-233（tasks API 面）红绿测：「今日焦点任务」筛选切用户本地日。

定界（wt513 221 同族余量，233 登记面 2）：``_find_today_focus_task``
的 ``today = date.today()``（api/v1/tasks.py:247）是宿主机本地日，直接
流入 :256 的 ``Task.due_date <= today`` SQL——墙上语义 due_date 被宿主
机日直切，上海凌晨（本地已次日）把「本地今日到期」的候选排除。

修法：today 改 ``local_date(utcnow(), tz)``（tz 沿 207/211/221 先例——
PushPreference.timezone 标量直查 + valid_timezone_name 缺省
Asia/Shanghai）。冻结钟（沿双冻结钟族）：冻结 NOW=09-25 20:00Z（上海
本地今日=09-26、UTC 用户本地今日=09-25）+ 冻结宿主机 date.today()
=09-25：
- 上海用户：due 09-26（本地今日）候选必须入选（修前 09-26<=09-25 为假
  被排除，回退到更旧的 due 09-24）；
- UTC 用户（tz 通道控制组）：本地今日仍 09-25，due 09-26 候选不入选、
  回退 due 09-24——修前修后一致（证明切的是用户时区而非统一偏移）。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tasks import _find_today_focus_task
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User

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


async def _seed_focus_candidates(db: AsyncSession, user: User) -> tuple[Task, Task]:
    local_today = Task(
        user_id=user.id,
        title="wt519 due local-today",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        due_date=dt.date(2026, 9, 26),
        order_index=1,
        estimated_minutes=20,
    )
    older = Task(
        user_id=user.id,
        title="wt519 due older",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        due_date=dt.date(2026, 9, 24),
        order_index=2,
        estimated_minutes=20,
    )
    db.add_all([local_today, older])
    await db.commit()
    return local_today, older


def _freeze_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.v1.tasks.utcnow", lambda: NOW_LATE, raising=False)

    class _FrozenDate(dt.date):
        @classmethod
        def today(cls) -> dt.date:
            return dt.date(2026, 9, 25)  # 宿主机本地日（+8 时区下此刻真实值）

    monkeypatch.setattr("app.api.v1.tasks.date", _FrozenDate)


@pytest.mark.asyncio
async def test_today_focus_follows_user_local_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """上海凌晨（本地 09-26 04:00）：本地今日到期候选须被今日焦点选中。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    local_today, _older = await _seed_focus_candidates(db_session, user)

    picked = await _find_today_focus_task(db_session, user_id=user.id, exclude_task_id=uuid4())

    assert picked is not None and picked.id == local_today.id, (
        f"本地今日（09-26）到期任务应成为今日焦点；修前 today=宿主机日 09-25 把它排除、"
        f"回退到更旧的 due 09-24：{picked.title if picked else None}"
    )


@pytest.mark.asyncio
async def test_today_focus_utc_user_keeps_utc_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """UTC 用户（tz 通道控制组）：本地今日=09-25，due 09-26 仍不入选。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="UTC")
    _local_today, older = await _seed_focus_candidates(db_session, user)

    picked = await _find_today_focus_task(db_session, user_id=user.id, exclude_task_id=uuid4())

    assert picked is not None and picked.id == older.id, (
        f"UTC 用户本地今日仍 09-25，due 09-26 不应入选（控制组，证明走用户时区通道而非统一 +8h）："
        f"{picked.title if picked else None}"
    )
