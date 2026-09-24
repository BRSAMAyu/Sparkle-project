"""「今日任务」单一事实源（S7 · 批1-A 信任地基）。

裁决（v3-output/B1-A/REPORT.md，依据 DL-R2 D10 批1 信任地基）：
「今天有没有待执行任务」由本模块唯一定义并导出，快照（home
experience_readouts goal-detail）、详情（experience/goal_router
goal-detail）、指挥台等消费面一律引用这里，禁止各自再写判定。

口径（与客户端看板分组字面一致，客户端仅作展示分组、不作真假判定，
见 mobile/lib/features/home/presentation/providers/task_board_provider.dart）：
- 「今日待执行」= ``due_date == today`` 且状态 ∈ TODAY_ACTIVE_STATUSES
  （即未完成、未放弃的一切任务，含暂停/卡住——它们仍属「待执行」）；
- 已完成/已放弃任务不算「待执行」；
- 无到期日的任务不属于「今日」（属于「无日期」分组），未来的任务同理；
- 下一步选取顺序：进行中优先 → 优先级降序 → order_index → created_at。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, cast

from sqlalchemy import and_, asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.task import Task, TaskStatus

# 「今日待执行」状态集：排除 COMPLETED / ABANDONED（与客户端看板分组一致）。
TODAY_ACTIVE_STATUSES: tuple[TaskStatus, ...] = (
    TaskStatus.PENDING,
    TaskStatus.IN_PROGRESS,
    TaskStatus.PAUSED,
    TaskStatus.STUCK,
    TaskStatus.RESTORE,
)


def todays_task_condition(today: date) -> ColumnElement[bool]:
    """「今日待执行」SQL 条件的唯一定义点（所有消费面的查询都从这里取）。"""
    return and_(
        Task.status.in_(TODAY_ACTIVE_STATUSES),
        Task.deleted_at.is_(None),
        Task.due_date == today,
    )


def is_todays_task(*, status: Any, due_date: Any, today: date) -> bool:
    """纯判定镜像：与 :func:`todays_task_condition` 语义完全一致。"""
    if isinstance(status, str):
        try:
            status = TaskStatus(status)
        except ValueError:
            return False
    if status not in TODAY_ACTIVE_STATUSES:
        return False
    return cast("bool", (due_date == today))


def pick_todays_next_task(tasks: Iterable[Task], today: date) -> Task | None:
    """从给定任务中选出「今日最小下一步」（与取数层排序一致）。"""
    candidates = [
        task
        for task in tasks
        if is_todays_task(status=task.status, due_date=task.due_date, today=today)
    ]
    if not candidates:
        return None

    def _status_rank(task: Task) -> int:
        status = task.status
        if isinstance(status, str):
            status = TaskStatus(status)
        return 0 if status == TaskStatus.IN_PROGRESS else 1

    def _created_key(task: Task) -> datetime:
        created = task.created_at
        if isinstance(created, datetime):
            return created
        return datetime.max

    return min(
        candidates,
        key=lambda task: (
            _status_rank(task),
            -int(task.priority or 0),
            int(task.order_index or 0),
            _created_key(task),
        ),
    )


def has_todays_task(tasks: Iterable[Task], today: date) -> bool:
    """「今天有没有待执行任务」的真假判定唯一入口（纯形式）。"""
    return any(
        is_todays_task(status=task.status, due_date=task.due_date, today=today)
        for task in tasks
    )


# 取数层统一排序（与 pick_todays_next_task 的纯排序一致）。
TODAY_NEXT_TASK_ORDER: tuple[Any, ...] = (
    desc(Task.status == TaskStatus.IN_PROGRESS),
    desc(Task.priority),
    asc(Task.order_index),
    asc(Task.created_at),
)


async def fetch_todays_next_task(
    db: AsyncSession,
    *,
    user_id: Any,
    plan_id: Any | None,
    today: date,
) -> Task | None:
    """从库里取「今日最小下一步」。快照/详情消费面的唯一取数入口。"""
    conditions = [todays_task_condition(today), Task.user_id == user_id]
    if plan_id is not None:
        conditions.append(Task.plan_id == plan_id)
    result = await db.execute(
        select(Task).where(*conditions).order_by(*TODAY_NEXT_TASK_ORDER).limit(1)
    )
    return result.scalar_one_or_none()


def todays_task_payload(task: Task | None) -> dict[str, Any] | None:
    """home 快照（experience_readouts goal-detail ``next_task``）载荷形状。"""
    if task is None:
        return None

    def _iso(value: Any) -> str | None:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return cast("str | None", (value.isoformat()))
        return str(value)

    def _value(value: Any) -> Any:
        return getattr(value, "value", value)

    return {
        "id": str(task.id),
        "title": task.title,
        "status": _value(task.status),
        "priority": task.priority,
        "due_date": _iso(task.due_date),
        "estimated_minutes": task.estimated_minutes,
        "knowledge_node_id": str(task.knowledge_node_id) if task.knowledge_node_id else None,
    }
