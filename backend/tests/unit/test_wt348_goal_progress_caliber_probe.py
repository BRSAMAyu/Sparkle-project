"""WT348-HUNT-R1 定向探针：Goal.progress 派生口径取证（只找不修）。

复现 task_event_consumer._handle_task_completed / _handle_task_abandoned 中
Goal.progress 计算所用的精确查询形态，对照真实写入值，证伪/证实两条判据：

判据一（大小写口径）：
    Task.status 列为 Enum(TaskStatus)，TaskStatus 为 StrEnum 且成员值全大写
    （TaskStatus.COMPLETED == "COMPLETED"，task_service 全部以枚举成员写入）。
    消费者查询用 `Task.status == "completed"`（小写字面量）。
    预期：对同一批任务，小写字面量计数=0，枚举成员计数=N。

判据二（软删口径）：
    BaseModel 提供软删 deleted_at；goal_today_view.todays_task_condition 显式
    `Task.deleted_at.is_(None)`。消费者两处 count 查询均无软删过滤。
    预期：软删任务同时计入分子/分母。

本文件不修改任何产品代码；断言失败即代表缺陷不成立（可证伪）。
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.goal import Goal  # noqa: F401
from app.models.plan import Plan
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User  # noqa: F401


@pytest_asyncio.fixture()
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def _seed(session: AsyncSession) -> tuple:
    user = User(username="wt348", email="wt348@test.local", hashed_password="x")
    session.add(user)
    await session.flush()
    plan = Plan(user_id=user.id, name="p", type="growth", plan_stage="daily")
    session.add(plan)
    await session.flush()
    goal = Goal(user_id=user.id, title="g", plan_id=plan.id)
    session.add(goal)
    tasks = [
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="t1",
            type=TaskType.LEARNING,
            estimated_minutes=25,
            status=TaskStatus.COMPLETED,
        ),
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="t2",
            type=TaskType.LEARNING,
            estimated_minutes=25,
            status=TaskStatus.PENDING,
        ),
    ]
    session.add_all(tasks)
    await session.flush()
    return user, plan, goal, tasks


@pytest.mark.asyncio
async def test_judgement_1_lowercase_literal_counts_zero_completed(session):
    """判据一：消费者小写字面量查不到任何 COMPLETED 任务（进度恒 0）。"""
    user, plan, _goal, tasks = await _seed(session)
    # 消费者原文形态（task_event_consumer.py:258-264 / 319-325）
    lowercase_completed = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
            Task.status == "completed",
        )
    )
    # 同一批数据的真实口径（plan_progress_service.py:295 同族）
    enum_completed = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
            Task.status == TaskStatus.COMPLETED,
        )
    )
    total = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
        )
    )
    assert enum_completed == 1, "前置：枚举口径能数到 1 个已完成"
    assert total == 2
    assert lowercase_completed == 0, "若此处非 0，则『小写口径数不到已完成』这一缺陷判定不成立"


@pytest.mark.asyncio
async def test_judgement_2_soft_deleted_counted_in_numerator_and_denominator(session):
    """判据二：软删任务进入消费者 count 的分子与分母。"""
    user, plan, _goal, tasks = await _seed(session)
    tasks[0].deleted_at = tasks[0].created_at  # 软删那个已完成任务
    await session.flush()
    no_filter_completed = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
            Task.status == TaskStatus.COMPLETED,
        )
    )
    no_filter_total = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
        )
    )
    soft_filter_completed = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
            Task.status == TaskStatus.COMPLETED,
            Task.deleted_at.is_(None),
        )
    )
    soft_filter_total = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
            Task.deleted_at.is_(None),
        )
    )
    assert (no_filter_completed, no_filter_total) == (1, 2)
    assert (soft_filter_completed, soft_filter_total) == (0, 1), "若两口径相等，则『软删未过滤』这一缺陷判定不成立"
