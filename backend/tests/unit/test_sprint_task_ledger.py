"""Sprint 任务账本单一事实源回归（BP-4 · P1-4 仪表盘对账）。

NORTHSTAR-LOOP1 BP-4（S7「AI 叙事失去地基」sprint 面实例）：
sprint-summary 旧实现按单条 plan 名下任务计数（``Task.plan_id == plan.id``），
跨 plan（goal 与 intake 并行计划）与无 plan 挂靠（手动建任务）的任务/完成事件
全部不可见 → 任务账本 completed=2 vs 仪表盘 completed=0、total=4（实际 20）。

修复裁决（v3-output/P1-4-DASHBOARD/REPORT.md）：sprint 面的任务统计口径由
app/services/sprint_task_ledger.py 唯一导出（纯判定 + SQL 条件 + 取数），
sprint-summary 等消费面一律改引用；计划结构性判定（七日完成检测、自动归档）
仍按 plan 域任务——它们判定的是「这份计划」而非「这个用户的执行账本」。

口径（与任务账本 GET /api/v1/tasks 同一取数域，app/api/v1/tasks.py list_tasks）：
账本全集 = 该用户全部未删除任务；completed = 全集中 status == COMPLETED 的数量。

本文件先于实现编写（TDD 红证，范本：test_goal_today_view.py）：实现落地前
import 失败即红。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import sqlite

from app.models.task import Task, TaskStatus


def _task(
    status: TaskStatus = TaskStatus.PENDING,
    *,
    user_id=None,
    plan_id=None,
    title: str = "",
) -> Task:
    return Task(
        user_id=user_id or uuid4(),
        plan_id=plan_id,
        title=title or f"task-{status.value}",
        type="LEARNING",
        estimated_minutes=25,
        status=status,
    )


# ---------------------------------------------------------------------------
# 1. 契约：模块存在且导出唯一定义点
# ---------------------------------------------------------------------------
def test_ssot_module_exists_and_exports_contract():
    from app.services import sprint_task_ledger as stl

    for name in (
        "sprint_ledger_condition",
        "fetch_sprint_ledger_tasks",
        "count_completed",
        "build_ledger_task_stats",
    ):
        assert hasattr(stl, name), f"SSOT 模块缺少契约成员: {name}"


# ---------------------------------------------------------------------------
# 2. SQL 条件是账本口径的唯一镜像（用户全域 + 非软删；不得按 plan/状态收窄）
# ---------------------------------------------------------------------------
def test_condition_is_user_ledger_scope_without_plan_narrowing():
    from app.services import sprint_task_ledger as stl

    user_id = uuid4()
    stmt = select(Task.id).where(stl.sprint_ledger_condition(user_id))
    compiled = stmt.compile(dialect=sqlite.dialect())
    params = compiled.params
    sql = str(compiled)

    # 用户域
    assert any(v == user_id for v in params.values()), "账本条件必须限定 user_id"
    # 排除软删
    assert "deleted_at" in sql, "账本条件必须排除软删任务"
    # 不得按 plan 收窄（BP-4 根因：plan 域收窄使跨 plan/无 plan 完成事件不可见）
    assert "plan_id" not in sql, "账本条件不得按 plan_id 收窄"
    # 不得按状态预过滤（total 需要全量，completed 由纯判定镜像统计）
    assert "status" not in sql, "账本条件不得按 status 预过滤"


# ---------------------------------------------------------------------------
# 3. 纯判定镜像：completed 判定与统计语义
# ---------------------------------------------------------------------------
def test_count_completed_mirror_and_stats_semantics():
    from app.schemas.exam_sprint import SprintTaskStats
    from app.services import sprint_task_ledger as stl

    tasks = [
        _task(TaskStatus.COMPLETED),
        _task(TaskStatus.COMPLETED),
        _task(TaskStatus.PENDING),
        _task(TaskStatus.IN_PROGRESS),
        _task(TaskStatus.ABANDONED),
    ]
    assert stl.count_completed(tasks) == 2

    stats = stl.build_ledger_task_stats(tasks)
    assert isinstance(stats, SprintTaskStats)
    assert stats.total == 5
    assert stats.completed == 2
    assert stats.completion_rate == round(2 / 5, 4)

    empty = stl.build_ledger_task_stats([])
    assert empty.total == 0
    assert empty.completed == 0
    assert empty.completion_rate == 0.0


def test_count_completed_accepts_enum_and_raw_values():
    from app.services import sprint_task_ledger as stl

    assert stl.count_completed([_task(TaskStatus.COMPLETED)]) == 1
    raw = Task(
        user_id=uuid4(),
        title="raw",
        type="LEARNING",
        estimated_minutes=10,
        status="COMPLETED",
    )
    assert stl.count_completed([raw]) == 1


# ---------------------------------------------------------------------------
# 4. 取数层端到端（conftest 内存 SQLite）：跨 plan + 无 plan 全可见，软删/他人不可见
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_fetch_sprint_ledger_tasks_sees_across_plans_and_planless(db_session):
    from app.models.plan import Plan
    from app.models.user import User
    from app.services import sprint_task_ledger as stl

    user = User(username=f"stl_{uuid4().hex[:10]}", email=f"{uuid4().hex[:10]}@t.example", hashed_password="x")
    other = User(username=f"stl_o_{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@t.example", hashed_password="x")
    db_session.add_all([user, other])
    await db_session.flush()
    goal_plan = Plan(user_id=user.id, name="goal-plan", type="sprint")
    intake_plan = Plan(user_id=user.id, name="intake-plan", type="sprint")
    db_session.add_all([goal_plan, intake_plan])
    await db_session.flush()

    milestone = Task(
        user_id=user.id,
        plan_id=goal_plan.id,
        title="milestone",
        type="LEARNING",
        estimated_minutes=10,
        status=TaskStatus.PENDING,
    )
    intake_day = Task(
        user_id=user.id,
        plan_id=intake_plan.id,
        title="intake-day1",
        type="LEARNING",
        estimated_minutes=10,
        status=TaskStatus.COMPLETED,
    )
    planless = Task(
        user_id=user.id,
        plan_id=None,
        title="manual-day1",
        type="TRAINING",
        estimated_minutes=10,
        status=TaskStatus.COMPLETED,
    )
    deleted = Task(
        user_id=user.id,
        plan_id=None,
        title="soft-deleted",
        type="LEARNING",
        estimated_minutes=10,
        status=TaskStatus.COMPLETED,
        deleted_at=datetime.now(UTC).replace(tzinfo=None),
    )
    foreign = Task(
        user_id=other.id,
        plan_id=None,
        title="other-user",
        type="LEARNING",
        estimated_minutes=10,
        status=TaskStatus.COMPLETED,
    )
    db_session.add_all([milestone, intake_day, planless, deleted, foreign])
    await db_session.commit()

    ledger = await stl.fetch_sprint_ledger_tasks(db_session, user_id=user.id)

    titles = {task.title for task in ledger}
    assert titles == {"milestone", "intake-day1", "manual-day1"}, "账本取数必须跨 plan 且含无 plan 任务"
    assert stl.count_completed(ledger) == 2
    stats = stl.build_ledger_task_stats(ledger)
    assert (stats.total, stats.completed) == (3, 2)
