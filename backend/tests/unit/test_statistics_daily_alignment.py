"""R2-E（H7）红绿测：statistics `/daily` 今日完成口径对齐 goal_today_view SSOT。

缺陷（修前，backend/app/api/v1/statistics.py:49-77）：
- 分母 ``total_tasks_today``：``due_date == today`` 且**无任何状态/软删过滤**——
  已放弃、已软删的任务都计入今日分母；
- 分子 ``tasks_completed``：``completed_at >= today``（时间轴=补完成日）与分母
  ``due_date == today``（时间轴=到期日）**异轴**，逾期补完成的任务计入分子却
  不在分母，完成率可 >1；
- 分子/分母均未过滤 ``deleted_at``，软删任务污染分子分母。

修复后声明口径（对齐 SSOT ``app/services/goal_today_view.py`` 的「今日任务」基座
——``due_date == today`` 且 ``deleted_at IS NULL``；状态口径以注释声明）：
- 分母 = 今日到期 + 未软删 + 状态 != ABANDONED（SSOT 已把 ABANDONED 排除出
  「今日任务」，故不计分母；COMPLETED 保留，因其为分子的母集）；
- 分子 = 分母同基座上 ``status == COMPLETED``——**时间轴统一到 due_date**：
  逾期任务补完成计入其实际到期日而非补完成日，分子恒为分母子集，完成率 ∈ [0,1]；
- ``study_minutes`` 与分子同集合（今日到期且已完成任务的预计时长），避免同屏两口径。

红测关键例：同日 1 完成 + 1 已放弃 + 1 软删 + 1 逾期完成——
修前 tasks_completed=2（含逾期补完成）、total_tasks_today=3（含放弃+软删），
断言分母/分子按声明口径均为 1 即红。
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.statistics import get_daily_stats
from app.models.task import Task, TaskStatus
from app.models.user import User


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _utc_today() -> date:
    return datetime.now(UTC).date()


async def _seed_user(db: AsyncSession) -> User:
    user = User(username=f"wt368-{uuid4().hex[:8]}", email=f"wt368-{uuid4().hex[:8]}@test.local", hashed_password="x")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def test_daily_stats_denominator_matches_declared_scope(db_session: AsyncSession):
    """同日 1 完成 + 1 已放弃 + 1 软删 + 1 逾期完成：分母按声明口径 = 1，分子同源 = 1。"""
    user = await _seed_user(db_session)
    today = _utc_today()
    now = _utcnow_naive()

    seeds = [
        # 1 完成：今日到期、已完成 → 分子分母各计 1
        Task(
            user_id=user.id, title="今日完成", type="LEARNING", estimated_minutes=30,
            status=TaskStatus.COMPLETED, due_date=today, completed_at=now,
        ),
        # 1 已放弃：SSOT 已把 ABANDONED 排除出「今日任务」→ 不计分母
        Task(
            user_id=user.id, title="今日放弃", type="LEARNING", estimated_minutes=10,
            status=TaskStatus.ABANDONED, due_date=today,
        ),
        # 1 软删：deleted_at 非空 → 分子分母均不可见
        Task(
            user_id=user.id, title="今日软删", type="LEARNING", estimated_minutes=10,
            status=TaskStatus.PENDING, due_date=today, deleted_at=now,
        ),
        # 1 逾期完成：到期日在昨日、今日补完成 → 时间轴统一到 due_date，不计入今日分子/分母
        Task(
            user_id=user.id, title="逾期补完成", type="LEARNING", estimated_minutes=20,
            status=TaskStatus.COMPLETED, due_date=today - timedelta(days=1), completed_at=now,
        ),
    ]
    for task in seeds:
        db_session.add(task)
    await db_session.commit()

    result = await get_daily_stats(current_user=user, db=db_session)

    assert result["total_tasks_today"] == 1, (
        f"分母应按声明口径（今日到期+未软删+未放弃）=1，"
        f"修前为 3（含已放弃+软删）：{result['total_tasks_today']}"
    )
    assert result["tasks_completed"] == 1, (
        f"分子应与分母同轴（今日到期且已完成）=1，修前为 2（逾期补完成按 completed_at 混入）：{result['tasks_completed']}"
    )
    assert result["study_minutes"] == 30, (
        f"study_minutes 应与分子同集合（30 分钟）=30，修前为 50（逾期补完成的 20 分钟混入）：{result['study_minutes']}"
    )


async def test_daily_stats_active_pending_counts_in_denominator(db_session: AsyncSession):
    """今日到期的活跃待办（PENDING）计入分母——活跃态口径对齐 SSOT TODAY_ACTIVE_STATUSES。"""
    user = await _seed_user(db_session)
    today = _utc_today()

    db_session.add(
        Task(
            user_id=user.id, title="今日待办", type="LEARNING", estimated_minutes=15,
            status=TaskStatus.PENDING, due_date=today,
        )
    )
    await db_session.commit()

    result = await get_daily_stats(current_user=user, db=db_session)

    assert result["total_tasks_today"] == 1
    assert result["tasks_completed"] == 0
