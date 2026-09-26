"""V3-FIX-233（task_priority 面）红绿测：reasoning 的「今日」切用户本地日。

定界（wt513 221 同族余量，233 登记面 1）：``generate_priority_reasoning``
的 ``today = date.today()``（task_priority_service.py:103）是宿主机本地
日——既非 UTC 亦非用户时区。它流入：
- ``score_candidate(today=today)`` 的 days_to_due/deadline 文案（209 同族
  派生量；:431 登记的调用方）；
- ``_spaced_repetition_detail`` 的 ``due_date - today`` 天数文案；
- ``_primary_reason``（:431）的 ``task.due_date <= today`` /
  ``next_review_at.date() <= today``——本地今日到期任务修后被
  ``09-26 <= 09-25`` 判假，理由层不认「今日时效」。

修法：today 改 ``local_date(utcnow(), tz)``（tz 沿 207/211/221 先例——
PushPreference.timezone 标量直查 + valid_timezone_name 缺省
Asia/Shanghai）；``next_review_at`` 是 UTC 存储列（galaxy.py DateTime），
比本地日先换算（221 ``_as_local_date`` 同款）。冻结钟（沿双冻结钟族）：
冻结 NOW=09-25 20:00Z（上海本地今日=09-26）+ 冻结宿主机 date.today()
=09-25：
- due 09-26（本地今日）任务：primary_reason 应为「time-sensitive for
  today」（修前落 09-25 判假，给兜底平衡理由）；spaced_repetition 细节
  文案应为 due today 而非 due in 1 day。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.services.task_priority_service import TaskPriorityService

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
    """冻结 UTC 钟与宿主机 date.today()（沿 211/233 冻结宿主机日族）。"""
    monkeypatch.setattr("app.services.task_priority_service.utcnow", lambda: NOW_LATE, raising=False)

    class _FrozenDate(dt.date):
        @classmethod
        def today(cls) -> dt.date:
            return dt.date(2026, 9, 25)  # 宿主机本地日（+8 时区下此刻真实值）

    monkeypatch.setattr("app.services.task_priority_service.date", _FrozenDate)


@pytest.mark.asyncio
async def test_primary_reason_follows_user_local_day(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """上海凌晨（本地 09-26 04:00）：本地今日到期任务理由层认「今日时效」。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    task = Task(
        user_id=user.id,
        title="wt519 due local-today",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        due_date=dt.date(2026, 9, 26),
        estimated_minutes=20,
    )
    db_session.add(task)
    await db_session.commit()

    reasoning = await TaskPriorityService(db_session).generate_priority_reasoning(
        user_id=user.id, task_id=task.id
    )

    assert "time-sensitive for today" in reasoning.primary_reason, (
        f"本地今日（09-26）到期任务 primary_reason 应认「今日时效」；"
        f"修前 today=宿主机日 09-25 把 09-26<=09-25 判假，落兜底理由：{reasoning.primary_reason}"
    )


@pytest.mark.asyncio
async def test_spaced_repetition_detail_days_follow_user_local_day(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """days_to_due 文案（209 同族派生量）：本地今日到期应为 due today 而非 due in 1 day。"""
    _freeze_clocks(monkeypatch)
    user = await _seed_user(db_session, timezone="Asia/Shanghai")
    task = Task(
        user_id=user.id,
        title="wt519 due local-today detail",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        due_date=dt.date(2026, 9, 26),
        estimated_minutes=20,
    )
    db_session.add(task)
    await db_session.commit()

    reasoning = await TaskPriorityService(db_session).generate_priority_reasoning(
        user_id=user.id, task_id=task.id
    )

    spaced = next(
        (signal.detail for signal in reasoning.supporting_signals if signal.type == "spaced_repetition"),
        "",
    )
    assert "due today" in spaced, f"本地今日到期 spaced_repetition 文案应含 due today（修前 due in 1 day）：{spaced}"
