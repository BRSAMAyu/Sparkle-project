"""WT360-R2A 红测：task_event_consumer Goal.progress 口径修复的行为级回归。

卡面（v3-output/WT355-HUNT-R2/REPORT.md 卡 R2-A）要求：同一批种子
（1 COMPLETED + 1 PENDING + 1 软删 COMPLETED）下修复口径 (1,2)→progress 0.5。

与 test_wt348/test_wt355 两份取证探针（查询形状复演）不同，本文件直接驱动
TaskEventConsumer 的真实 handler（task.completed / task.abandoned）在 sqlite
内存库上写库，锁住的是产品代码行为本身：

- 修复前：小写字面量在 sqlite 数到 0 个已完成 → 字面写 0.0（生产 PG 上则是
  22P02 报错被内层 except 吞掉、写入不发生，进度冻结于列默认 0.0）；
- 修复后：枚举成员口径 + 软删过滤 → (1,2) → 0.5；
- 附带 H5 防御深度：多 Goal 挂同一 plan 时 limit(1)+first() 写入不再被
  MultipleResultsFound 吞掉。

PG 语义注记（发布说明人肉验证项，本文件无法覆盖）：修复后生产日志不应再出现
`Failed to update goal progress: ... invalid input value for enum taskstatus`。
"""

from __future__ import annotations

from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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
from app.services.task_event_consumer import TaskEventConsumer

# ---------------------------------------------------------------------------
# 基础设施：sqlite 内存库；handler 的 AsyncSessionLocal 换成同库 sessionmaker
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with maker() as session:
        yield session, maker
    await engine.dispose()


async def _seed_mixed_batch(session: AsyncSession) -> tuple:
    """卡面种子：1 COMPLETED + 1 PENDING + 1 软删 COMPLETED（同 plan）。"""
    user = User(username="wt360", email="wt360@test.local", hashed_password="x")
    session.add(user)
    await session.flush()
    plan = Plan(user_id=user.id, name="p360", type="growth", plan_stage="daily")
    session.add(plan)
    await session.flush()
    goal = Goal(user_id=user.id, title="g360", plan_id=plan.id)
    session.add(goal)
    await session.flush()
    tasks = [
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="done",
            type=TaskType.LEARNING,
            estimated_minutes=25,
            status=TaskStatus.COMPLETED,
        ),
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="todo",
            type=TaskType.LEARNING,
            estimated_minutes=25,
            status=TaskStatus.PENDING,
        ),
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="done-but-soft-deleted",
            type=TaskType.LEARNING,
            estimated_minutes=25,
            status=TaskStatus.COMPLETED,
        ),
    ]
    session.add_all(tasks)
    await session.flush()
    tasks[2].deleted_at = tasks[2].created_at  # 软删那个已完成任务
    await session.flush()
    return user, plan, goal, tasks


def _new_consumer() -> TaskEventConsumer:
    return TaskEventConsumer(event_bus=SimpleNamespace(connect=AsyncMock()))


def _collaborator_patches(consumer: TaskEventConsumer, maker) -> list:
    """隔离 handler 的全部重协作者；只保留 Goal.progress 块的真实 DB 行为。"""
    return [
        patch("app.services.task_event_consumer.AsyncSessionLocal", maker),
        patch(
            "app.services.task_event_consumer.BehaviorSignalCollector",
            return_value=SimpleNamespace(
                handle_task_completed_event=AsyncMock(),
                handle_task_abandoned_event=AsyncMock(),
            ),
        ),
        patch(
            "app.services.task_event_consumer.MetacognitionService",
            return_value=SimpleNamespace(refresh_snapshot=AsyncMock()),
        ),
        patch(
            "app.services.task_event_consumer.CommunitySignalBridge",
            return_value=SimpleNamespace(handle_group_task_completed=AsyncMock()),
        ),
        patch(
            "app.services.task_event_consumer.AutoFragmentCollector",
            return_value=SimpleNamespace(collect_from_task_completion=AsyncMock()),
        ),
        patch(
            "app.services.task_event_consumer.AdaptiveReplanner",
            return_value=SimpleNamespace(
                on_task_completed=AsyncMock(),
                evaluate_plan_health_now=AsyncMock(return_value=[]),
            ),
        ),
        patch(
            "app.signals.spine_orchestrator.get_spine_orchestrator",
            return_value=SimpleNamespace(on_task_completed=AsyncMock()),
        ),
        patch.object(consumer, "_record_task_outcome", new_callable=AsyncMock),
        patch.object(consumer, "_record_route_history_task_outcome", new_callable=AsyncMock),
        patch.object(consumer, "_record_belief_task_outcome", new_callable=AsyncMock),
        patch.object(consumer, "_handle_spine_bridge_event", new_callable=AsyncMock),
        patch.object(consumer, "_trigger_adaptive_plan_health_event", new_callable=AsyncMock),
    ]


async def _drive(consumer: TaskEventConsumer, maker, handler, event: dict) -> None:
    with ExitStack() as stack:
        for ctx in _collaborator_patches(consumer, maker):
            stack.enter_context(ctx)
        await handler(event)


async def _reload_goal(session: AsyncSession, goal_id) -> Goal:
    session.expire_all()
    return (await session.execute(select(Goal).where(Goal.id == goal_id))).scalars().one()


# ---------------------------------------------------------------------------
# 行为级红测：真实 handler 写库
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_task_completed_event_writes_progress_with_fixed_caliber(db):
    """task.completed 事件后 Goal.progress = 1/2（软删 COMPLETED 不进分子分母）。"""
    session, maker = db
    user, plan, goal, tasks = await _seed_mixed_batch(session)
    consumer = _new_consumer()
    event = {
        "event_type": "task.completed",
        "user_id": str(user.id),
        "task_id": str(tasks[0].id),
        "plan_id": str(plan.id),
        "estimated_minutes": 0,
        "actual_minutes": 0,
        "completion_rate": 1.0,
    }
    await _drive(consumer, maker, consumer._handle_task_completed, event)

    reloaded = await _reload_goal(session, goal.id)
    assert reloaded.progress == pytest.approx(0.5), (
        "修复口径下（1 COMPLETED + 1 PENDING + 1 软删 COMPLETED）progress 应为 0.5；"
        "若为 0.0，说明枚举/软删口径回退"
    )


@pytest.mark.asyncio
async def test_task_abandoned_event_writes_progress_with_fixed_caliber(db):
    """task.abandoned 事件走同一修复口径。"""
    session, maker = db
    user, plan, goal, tasks = await _seed_mixed_batch(session)
    consumer = _new_consumer()
    event = {
        "event_type": "task.abandoned",
        "user_id": str(user.id),
        "task_id": str(tasks[1].id),
        "plan_id": str(plan.id),
    }
    await _drive(consumer, maker, consumer._handle_task_abandoned, event)

    reloaded = await _reload_goal(session, goal.id)
    assert reloaded.progress == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_multiple_goals_on_same_plan_no_longer_silences_write(db):
    """H5 防御深度：同 plan 挂两个 Goal 时写入不再被 MultipleResultsFound 吞掉。

    修复前 scalar_one_or_none() 抛 MultipleResultsFound，被内层 except 吞成
    warning → 两个 Goal 都不写；修复后 limit(1)+first() 至少写中一个。
    """
    session, maker = db
    user, plan, _goal, tasks = await _seed_mixed_batch(session)
    session.add(Goal(user_id=user.id, title="g360-b", plan_id=plan.id))
    await session.flush()

    consumer = _new_consumer()
    event = {
        "event_type": "task.completed",
        "user_id": str(user.id),
        "task_id": str(tasks[0].id),
        "plan_id": str(plan.id),
        "completion_rate": 1.0,
    }
    await _drive(consumer, maker, consumer._handle_task_completed, event)

    plan_id = plan.id  # expire_all 后再访问 plan.id 会触发同步 IO（MissingGreenlet）
    session.expire_all()  # handler 写入发生在另一 session（共享 StaticPool 连接）
    goals = (await session.execute(select(Goal).where(Goal.plan_id == plan_id))).scalars().all()
    written = [g for g in goals if g.progress is not None and abs(g.progress - 0.5) < 1e-9]
    assert written, "多 Goal 同 plan 时仍应有一个被写入 0.5（MultipleResultsFound 面已消）"


# ---------------------------------------------------------------------------
# 口径对照（小写串形状保留为回归证明，种子与卡面一致）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lowercase_literal_versus_fixed_caliber_on_card_seed(db):
    """同一混合种子：旧小写形状 (0,3)→0.0；修复口径 (1,2)→0.5。"""
    session, _maker = db
    user, plan, _goal, _tasks = await _seed_mixed_batch(session)
    lowercase_completed = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
            Task.status == "completed",  # 修复前消费者原文口径（回归证明）
        )
    )
    unfiltered_total = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
        )
    )
    fixed_completed = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
            Task.status == TaskStatus.COMPLETED,
            Task.deleted_at.is_(None),
        )
    )
    fixed_total = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
            Task.deleted_at.is_(None),
        )
    )
    assert (lowercase_completed, unfiltered_total) == (0, 3)
    assert (fixed_completed, fixed_total) == (1, 2)
    assert fixed_completed / fixed_total == pytest.approx(0.5)
