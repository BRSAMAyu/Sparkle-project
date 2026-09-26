"""V3-FIX-250（写侧面 1）红绿测：snooze due_date 写侧派生切用户本地日。

定界（wt519 V3-FIX-233 同族写侧余量，250 登记面 1）：``snooze_task``
的 ``date.today() + timedelta(days=…)``（api/v1/tasks.py:1021）是宿主机
本地日，直接写进墙上语义 ``task.due_date``——UTC 宿主上服务上海用户，
用户本地已次日时 snooze 把 due_date 落错日网格。

修法：沿 233 同款——PushPreference.timezone 标量直查 + local_date
（缺省 Asia/Shanghai），today 换用户本地日再派生写库值。冻结钟（沿双
冻结钟族）：冻结 NOW=09-25 20:00Z（上海本地今日=09-26、UTC 用户本地
今日=09-25）+ 冻结宿主机 date.today()=09-25（UTC 宿主钟）：

- 上海用户：days=1 → due 09-27（本地今日 09-26 + 1）。**写侧语义差异
  如实标注**：修前该用例写 due=09-26（宿主机日 09-25 + 1），修后写
  09-27——落库值平移一天，属修目标本身，非回归；
- UTC 用户（tz 通道控制组）：days=1 → due 09-26（本地今日 09-25 + 1，
  修前修后一致——证明走用户时区通道而非统一偏移）。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tasks import snooze_task
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.schemas.task import TaskSnoozeRequest

NOW_LATE = dt.datetime(2026, 9, 25, 20, 0)  # naive UTC；上海本地 = 2026-09-26 04:00


def _freeze_clocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.v1.tasks.utcnow", lambda: NOW_LATE, raising=False)

    class _FrozenDate(dt.date):
        @classmethod
        def today(cls) -> dt.date:
            return dt.date(2026, 9, 25)  # 宿主机钟（UTC 宿主此刻真实值）

    monkeypatch.setattr("app.api.v1.tasks.date", _FrozenDate)


async def _seed_user(db: AsyncSession, *, timezone: str) -> User:
    user = User(
        username=f"wt526-{uuid4().hex[:8]}",
        email=f"wt526-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    db.add(PushPreference(user_id=user.id, timezone=timezone))
    await db.commit()
    return user


async def _seed_task(db: AsyncSession, user: User) -> Task:
    task = Task(
        user_id=user.id,
        title=f"wt526 snooze-{uuid4().hex[:6]}",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        due_date=dt.date(2026, 9, 25),
        order_index=1,
        estimated_minutes=20,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@pytest.mark.asyncio
async def test_snooze_due_date_follows_user_local_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """上海用户凌晨（本地 09-26 04:00）snooze 1 天：写侧 due=09-27。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    task = await _seed_task(db_session, user)

    await snooze_task(_fake_request(), TaskSnoozeRequest(days=1), task.id, user, db_session)

    assert task.due_date == dt.date(2026, 9, 27), (
        "snooze 写侧 due_date 应按用户本地日（09-26）+1=09-27 落库；"
        "修前 date.today()=宿主机日 09-25，写 09-26（写侧语义差异：落库值平移一天，修目标本身）"
    )
    assert "snoozed" in (task.tags or [])


@pytest.mark.asyncio
async def test_snooze_due_date_utc_user_keeps_utc_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """UTC 用户（tz 通道控制组）：本地今日=09-25，snooze 1 天 → due=09-26。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="UTC")
    task = await _seed_task(db_session, user)

    await snooze_task(_fake_request(), TaskSnoozeRequest(days=1), task.id, user, db_session)

    assert task.due_date == dt.date(2026, 9, 26), (
        "UTC 用户本地今日仍 09-25，snooze 1 天应写 due=09-26" "（控制组，证明走用户时区通道而非统一 +8h）"
    )


def _fake_request():
    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/tasks/x/snooze",
        "headers": [],
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
        "server": ("server", 80),
        "scheme": "http",
    }
    return Request(scope)
