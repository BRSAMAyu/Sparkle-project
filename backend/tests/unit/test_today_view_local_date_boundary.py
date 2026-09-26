"""V3-FIX-197（「今日任务」SSOT 调用方 UTC 日期债）红绿测：调用方 today 切用户本地日。

定界实录（主市场 Asia/Shanghai = UTC+8）：
- ``goal_today_view`` SSOT 本身完全参数化 today（本卡不动其签名与判定），
  但其调用方 ``experience_readouts._next_task``（home 快照/指挥台）传
  ``_utcnow().date()``、``experience/goal_router._todays_next_task``
  （goal 详情）传 ``datetime.now(UTC).date()`` —— 都是 UTC date；
- ``statistics /stats/daily`` 的 due_date 分母沿同一 UTC 钟（wt487 FIX-37
  定界时为保 H7 字面一致未动，本卡一并收口）；
- UTC+8 本地 00:00–08:00（UTC 尚在前一日 16:00–24:00）间，到期日=本地
  今日的任务被按「昨日到期」取数 → home 快照/指挥台「今日下一步」
  报无/错任务、/stats/daily 今日分母漏计。

红测冻结 NOW = 2026-09-25 23:30 UTC（上海本地 = 2026-09-26 07:30，
沿 test_statistics_local_timezone_boundary 的冻结钟模式），任务
due_date=2026-09-26（本地今日）：修前三面全按 UTC 今日 09-25 取数 →
报无任务/分母 0；修后按用户本地日（push_preference.timezone，缺省
Asia/Shanghai，沿 focus_service._local_today 先例）命中。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.v1.statistics as statistics_module
from app.api.v1 import experience_readouts
from app.api.v1.experience import goal_router
from app.api.v1.statistics import get_daily_stats
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User

NOW = dt.datetime(2026, 9, 25, 23, 30)  # naive UTC；Asia/Shanghai 本地 = 2026-09-26 07:30
UTC_TODAY = dt.date(2026, 9, 25)
LOCAL_TODAY = dt.date(2026, 9, 26)


@pytest.fixture
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """冻结三个消费面的时钟源。

    goal_router 修前自带 ``datetime.now(UTC)``，用同型替身类冻结（沿
    test_goal_today_view.test_surface_queries_both_filter_by_ssot_condition
    的既有写法）；experience_readouts._utcnow 与 statistics._utcnow 直接
    monkeypatch。
    """

    class _FrozenDatetime(dt.datetime):
        @staticmethod
        def now(tz=None):  # type: ignore[override]
            return NOW.replace(tzinfo=dt.UTC)

    monkeypatch.setattr(goal_router, "datetime", _FrozenDatetime)
    monkeypatch.setattr(experience_readouts, "_utcnow", lambda: NOW)
    monkeypatch.setattr(statistics_module, "_utcnow", lambda: NOW)


async def _seed_user(db: AsyncSession) -> User:
    user = User(
        username=f"wt494-{uuid4().hex[:8]}",
        email=f"wt494-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _seed_local_today_task(db: AsyncSession, user_id) -> Task:
    """due_date=本地今日（09-26）的待执行任务；UTC 侧看是「明日」到期。"""
    task = Task(
        user_id=user_id,
        title="本地今日下一步",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=25,
        status=TaskStatus.PENDING,
        priority=5,
        due_date=LOCAL_TODAY,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def test_home_next_task_uses_user_local_today(db_session: AsyncSession, frozen_clock: None):
    """home 快照/指挥台「今日下一步」必须按用户本地日取数。"""
    user = await _seed_user(db_session)
    task = await _seed_local_today_task(db_session, user.id)

    payload = await experience_readouts._next_task(db_session, user.id)

    assert payload is not None, (
        f"上海晨间（本地 09-26 07:30）home 快照应取到 due_date=09-26 的今日任务；"
        f"修前调用方传 UTC 今日 09-25 → 被当「明日」任务排除：{payload}"
    )
    assert payload["id"] == str(task.id)


async def test_goal_detail_todays_next_task_uses_user_local_today(db_session: AsyncSession, frozen_clock: None):
    """goal 详情「今日最小下一步」必须按用户本地日取数（与 home 快照同源同日）。"""
    user = await _seed_user(db_session)
    task = await _seed_local_today_task(db_session, user.id)

    fetched = await goal_router._todays_next_task(db_session, user_id=user.id, plan_id=None)

    assert fetched is not None, (
        f"上海晨间 goal 详情应取到 due_date=09-26 的今日任务；" f"修前传 UTC 今日 09-25 → 取不到：{fetched}"
    )
    assert fetched.id == task.id


async def test_two_surfaces_stay_literal_consistent_at_frozen_instant(db_session: AsyncSession, frozen_clock: None):
    """H7 字面一致：同一冻结时刻，home 快照与 goal 详情必得同一「今日下一步」。"""
    user = await _seed_user(db_session)
    task = await _seed_local_today_task(db_session, user.id)

    home_payload = await experience_readouts._next_task(db_session, user.id)
    goal_task = await goal_router._todays_next_task(db_session, user_id=user.id, plan_id=None)

    assert home_payload is not None and goal_task is not None, (
        f"两个消费面在同一本地日必须同时报有任务；修前双双按 UTC 今日报无：" f"home={home_payload} goal={goal_task}"
    )
    assert home_payload["id"] == str(goal_task.id) == str(task.id)


async def test_push_preference_timezone_drives_boundary(db_session: AsyncSession, frozen_clock: None):
    """边界确由用户时区驱动：UTC 用户在冻结时刻的「今日」仍是 09-25，不得误取 09-26。"""
    user = await _seed_user(db_session)
    db_session.add(PushPreference(user_id=user.id, timezone="UTC"))
    await _seed_local_today_task(db_session, user.id)
    await db_session.commit()

    payload = await experience_readouts._next_task(db_session, user.id)

    assert payload is None, f"UTC 用户本地今日=09-25，due_date=09-26 的任务不属于其今日：{payload}"


async def test_stats_daily_due_date_denominator_uses_user_local_today(db_session: AsyncSession, frozen_clock: None):
    """/stats/daily 的 due_date 分母随 SSOT 调用方一起切用户本地日。"""
    user = await _seed_user(db_session)
    await _seed_local_today_task(db_session, user.id)

    result = await get_daily_stats(current_user=user, db=db_session)

    assert result["total_tasks_today"] == 1, (
        f"上海晨间 /stats/daily 今日分母应含 due_date=本地今日(09-26) 的任务；"
        f"修前分母按 UTC 今日 09-25 切 → 漏计：{result}"
    )
    assert result["tasks_completed"] == 0
    assert result["focus_sessions"] == 0
