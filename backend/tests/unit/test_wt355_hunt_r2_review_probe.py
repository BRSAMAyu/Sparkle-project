"""WT355-HUNT-R2 第二轮独立复核探针（只找不修，不依赖第一轮测试文件）。

固化第二轮复核的两个增量证据：

R2-E1（H1 机制精化——PG 上的真实症状是「写入路径报错被吞、进度冻结于默认 0.0」，
       而非字面写 0.0；sqlite/测试环境才是字面写 0.0）：
    - 生产 schema 快照（backend/gateway/internal/db/schema.sql:528-536）中
      tasks.status 为原生 PG 枚举 taskstatus，标签全大写。
    - 本仓实际安装的 SQLAlchemy 2.0.48 对「未知小写字符串」的 bind 处理是
      原样透传到 SQL 层（不校验、不改写、不报客户端错）。
    - 因此生产 PG 收到 WHERE status = 'completed' 时抛 22P02 invalid input
      value for enum，被 task_event_consumer 内层 except Exception 吞成
      warning（:270/:335）→ 整个写入不发生；叠加 Goal.progress 列默认
      0.0 且该消费者是全仓唯一写入方 → 生产结局同样是进度恒 0.0。
    - 本探针断言 bind 透传行为与持久化值口径；若 SQLAlchemy 未来版本改为
      客户端校验/报错，本断言即失效，提示需重新评估 H1 的 PG 症状描述。

R2-E2（H1 用户可见口径——用与消费者逐字相同的查询形状在 sqlite 上复演写值）：
    - 在含 1 个 COMPLETED + 1 个 PENDING 任务的 plan 上，消费者形状的查询
      得 completed=0、total=2 → goal.progress = 0.0（字面写 0.0）。
    - 修复口径（TaskStatus.COMPLETED + deleted_at.is_(None)）得 (1, 2) → 0.5。

本文件不修改任何产品代码；断言失败即代表对应复核判定不成立（可证伪）。
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import Enum as SAEnum, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import sqlalchemy as _sa

from app.models.base import Base
from app.models.goal import Goal  # noqa: F401
from app.models.plan import Plan
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User  # noqa: F401


# ---------------------------------------------------------------------------
# R2-E1: bind 层行为（无 DB）
# ---------------------------------------------------------------------------

def test_r2_e1_lowercase_unknown_string_is_passed_through_and_persisted_value_is_uppercase():
    """SQLAlchemy 对未知小写串透传给 SQL 层；持久化值=大写成员名。

    前半段成立 ⇒ 生产 PG 上 `status = 'completed'` 由 PG 端枚举输入解析报错
    （22P02），写入整体不发生（被 except 吞掉）；并非「数到 0 后写 0.0」。
    后半段成立 ⇒ 修复必须以枚举成员为口径（bind 到 'COMPLETED' 标签）。
    """
    e = SAEnum(TaskStatus)
    # 未知小写串透传（SQLAlchemy 2.0.48 实测行为；版本变更则本断言失效）
    assert e._db_value_for_elem("completed") == "completed"
    # 成员 → 持久化值 = 成员名 = 大写（与 schema.sql 的 taskstatus 标签一致）
    assert e._db_value_for_elem(TaskStatus.COMPLETED) == "COMPLETED"


def test_r2_e1_sqlalchemy_version_recorded():
    """记录取证所用 SQLAlchemy 版本，便于未来复现口径。"""
    major_minor = tuple(int(p) for p in _sa.__version__.split(".")[:2])
    assert major_minor >= (2, 0)


# ---------------------------------------------------------------------------
# R2-E2: 消费者查询形状复演（sqlite 内存库）
# ---------------------------------------------------------------------------

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


async def _seed_plan_with_tasks(session: AsyncSession) -> tuple:
    user = User(username="wt355", email="wt355@test.local", hashed_password="x")
    session.add(user)
    await session.flush()
    plan = Plan(user_id=user.id, name="p355", type="growth", plan_stage="daily")
    session.add(plan)
    await session.flush()
    session.add(Goal(user_id=user.id, title="g355", plan_id=plan.id))
    session.add_all(
        [
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
        ]
    )
    await session.flush()
    return user, plan


@pytest.mark.asyncio
async def test_r2_e2_consumer_shaped_query_writes_zero_progress(session):
    """消费者形状（小写字面量、无软删过滤）→ completed=0/total=2 → 写 0.0。"""
    user, plan = await _seed_plan_with_tasks(session)
    completed = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
            Task.status == "completed",  # 消费者原文口径（task_event_consumer.py:262/323）
        )
    )
    total = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
        )
    )
    progress = (completed / total) if total and total > 0 else 0.0  # 消费者原文写回式
    assert (completed, total) == (0, 2)
    assert progress == 0.0, "若非 0.0，则『消费者把进度写 0』这一判定不成立"


@pytest.mark.asyncio
async def test_r2_e2_fixed_caliber_yields_correct_progress(session):
    """修复口径（枚举成员 + 软删过滤）→ (1, 2) → 0.5。"""
    user, plan = await _seed_plan_with_tasks(session)
    completed = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
            Task.status == TaskStatus.COMPLETED,
            Task.deleted_at.is_(None),
        )
    )
    total = await session.scalar(
        select(func.count(Task.id)).where(
            Task.plan_id == plan.id,
            Task.user_id == user.id,
            Task.deleted_at.is_(None),
        )
    )
    assert (completed, total) == (1, 2)
    assert (completed / total) == pytest.approx(0.5)
