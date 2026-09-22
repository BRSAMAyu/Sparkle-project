"""Sprint 任务账本单一事实源（BP-4 · P1-4 仪表盘对账，S7 同族）。

裁决（v3-output/P1-4-DASHBOARD/REPORT.md）：sprint 面的任务统计口径
（total / completed / completion_rate）由本模块唯一定义并导出（SQL 条件 +
取数 + 纯判定镜像），sprint-summary 等叙事消费面一律引用这里，禁止各自再写
第二套聚合。模式同 B1-A ``goal_today_view.py``（§9.4 口径单一事实源）。

背景（NORTHSTAR-LOOP1 BP-4）：sprint-summary 旧实现按单条 sprint plan 名下
任务计数（``Task.plan_id == plan.id``），跨 plan（goal 与 intake 并行计划，
BP-7）与无 plan 挂靠（用户手动建任务，plan→task 链缺口）的任务与完成事件
全部不可见 → 任务账本 completed=2 vs 仪表盘 completed=0、total=4（实际 20）。

口径（与任务账本 GET /api/v1/tasks 同一取数域，app/api/v1/tasks.py list_tasks）：
- 账本全集 = 该用户全部未删除任务（不按 plan 收窄、不按状态预过滤）；
- completed = 全集中 status == COMPLETED 的数量；total = 全集大小；
- 完成判定纯镜像与 SQL 同源，防止两处定义漂移。

边界：计划结构性判定（七日完成检测、自动归档等「这份计划做完了吗」）仍按
plan 域任务——它们判定的是计划本身，不是用户的执行账本，两类口径不得混用。
"""

from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import and_, asc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.task import Task, TaskStatus
from app.schemas.exam_sprint import SprintTaskStats


def sprint_ledger_condition(user_id: Any) -> ColumnElement[bool]:
    """Sprint 任务账本全集的 SQL 条件唯一定义点（所有消费面的查询都从这里取）。

    与任务账本视图（GET /api/v1/tasks）同一取数域：用户全域 + 非软删；
    刻意不按 plan 收窄、不按状态预过滤（total 需要全集）。
    """
    return and_(Task.user_id == user_id, Task.deleted_at.is_(None))


def _task_status(task: Task) -> str:
    return str(getattr(task.status, "value", task.status) or TaskStatus.PENDING.value)


def is_completed_task(task: Task) -> bool:
    """「已完成」纯判定镜像：与 SQL 侧 status == COMPLETED 语义完全一致。"""
    return _task_status(task) == TaskStatus.COMPLETED.value


def count_completed(tasks: Iterable[Task]) -> int:
    """账本全集中的完成数（纯判定，供内存集合与测试镜像使用）。"""
    return sum(1 for task in tasks if is_completed_task(task))


def build_ledger_task_stats(tasks: Iterable[Task]) -> SprintTaskStats:
    """Sprint 面任务统计的唯一构造点（total/completed/completion_rate）。"""
    ledger = list(tasks)
    total = len(ledger)
    completed = count_completed(ledger)
    completion_rate = (completed / total) if total else 0.0
    return SprintTaskStats(total=total, completed=completed, completion_rate=round(completion_rate, 4))


async def fetch_sprint_ledger_tasks(db: AsyncSession, *, user_id: Any) -> list[Task]:
    """Sprint 面任务统计的唯一取数入口（快照语义，随取随算）。"""
    result = await db.execute(
        select(Task).where(sprint_ledger_condition(user_id)).order_by(asc(Task.created_at), asc(Task.id))
    )
    return list(result.scalars().all())
