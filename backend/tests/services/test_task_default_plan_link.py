"""PLAN-LINK · 手动任务默认关联计划（TaskService.create 默认解析面）红绿测试.

P1-4 遗留（LOOP1 C1b）：手动创建的任务不带 plan_id，脱离计划域。本族测试锁定
修复后的裁决语义：

- 未显式给 plan_id 的学习型任务 → active SPRINT 计划优先默认关联；
- 无 SPRINT 回落 goal plan（goal_id 非空的活跃计划）；两者皆无 → NULL（不强行造计划）；
- 显式传 plan_id → 一字尊重（intake/goal 生成路径不受影响）；
- 显式传 plan_id=None（fields_set 含 plan_id）→ 视为「明确不关联」保持 NULL
  （card_protocol 单卡导入依赖此语义）；
- 多个 SPRINT 计划 → is_primary 优先、创建最新（对齐群任务认领先例）；
- 非学习型（SOCIAL/PLANNING/OCR）不做默认关联。
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskType
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService


def _make_plan(
    user_id,
    *,
    type_: PlanType = PlanType.SPRINT,
    goal_id=None,
    name: str = "计划",
    is_primary: bool = False,
    created_at: datetime | None = None,
    is_active: bool = True,
) -> Plan:
    plan = Plan(user_id=user_id, name=name, type=type_, goal_id=goal_id)
    plan.is_primary = is_primary
    plan.is_active = is_active
    if created_at is not None:
        plan.created_at = created_at
    return plan


async def _create_task(db: AsyncSession, user_id, *, type_: TaskType = TaskType.LEARNING, **kwargs) -> Task:
    return await TaskService.create(db, TaskCreate(title="手动任务", type=type_, **kwargs), user_id)


@pytest.mark.usefixtures("db_session")
class TestManualTaskDefaultPlanLink:
    async def test_manual_task_defaults_to_active_sprint_plan(self, db, test_user):
        """红→绿主断言：手动学习任务默认关联唯一 active SPRINT 计划。"""
        plan = _make_plan(test_user.id, name="冲刺计划")
        db.add(plan)
        await db.flush()

        task = await _create_task(db, test_user.id)
        assert task.plan_id == plan.id

    async def test_explicit_plan_id_is_respected(self, db, test_user):
        """显式传 plan_id 一字尊重（intake/goal 生成路径零影响）。"""
        sprint = _make_plan(test_user.id, name="冲刺")
        growth = _make_plan(test_user.id, type_=PlanType.GROWTH, name="成长")
        db.add_all([sprint, growth])
        await db.flush()

        task = await _create_task(db, test_user.id, plan_id=growth.id)
        assert task.plan_id == growth.id

    async def test_explicit_none_keeps_unlinked(self, db, test_user):
        """显式 plan_id=None（fields_set 含 plan_id）=「明确不关联」→ 保持 NULL。"""
        sprint = _make_plan(test_user.id, name="冲刺")
        db.add(sprint)
        await db.flush()

        task = await _create_task(db, test_user.id, plan_id=None)
        assert "plan_id" in task.__dict__  # 行存在
        assert task.plan_id is None

    async def test_no_plans_stays_null(self, db, test_user):
        """无任何计划 → 保持 NULL，不强行造计划。"""
        task = await _create_task(db, test_user.id)
        assert task.plan_id is None

    async def test_goal_plan_fallback(self, db, test_user):
        """无 SPRINT 计划时回落 goal plan（goal 分解产出的活跃计划）。"""
        goal_plan = _make_plan(
            test_user.id, type_=PlanType.GROWTH, goal_id="00000000-0000-0000-0000-00000000abcd", name="目标计划"
        )
        db.add(goal_plan)
        await db.flush()

        task = await _create_task(db, test_user.id)
        assert task.plan_id == goal_plan.id

    async def test_sprint_beats_goal_plan(self, db, test_user):
        """SPRINT 优先于 goal plan。"""
        goal_plan = _make_plan(
            test_user.id, type_=PlanType.GROWTH, goal_id="00000000-0000-0000-0000-00000000abcd", name="目标"
        )
        sprint = _make_plan(test_user.id, name="冲刺")
        db.add_all([goal_plan, sprint])
        await db.flush()

        task = await _create_task(db, test_user.id)
        assert task.plan_id == sprint.id

    async def test_inactive_or_deleted_plans_are_ignored(self, db, test_user):
        """is_active=False 的计划不参与默认关联（回落 goal 或 NULL）。"""
        inactive_sprint = _make_plan(test_user.id, name="旧冲刺", is_active=False)
        db.add(inactive_sprint)
        await db.flush()

        task = await _create_task(db, test_user.id)
        assert task.plan_id is None

    async def test_multiple_sprint_plans_pick_primary_then_newest(self, db, test_user):
        """多冲刺计划：is_primary 优先，其次创建最新（对齐群任务认领先例）。"""
        old = _make_plan(test_user.id, name="旧冲刺", created_at=datetime(2026, 9, 1))
        newest = _make_plan(test_user.id, name="新冲刺", created_at=datetime(2026, 9, 20))
        primary = _make_plan(test_user.id, name="主冲刺", is_primary=True, created_at=datetime(2026, 8, 15))
        db.add_all([old, newest, primary])
        await db.flush()

        task = await _create_task(db, test_user.id)
        assert task.plan_id == primary.id

        # 无 primary 时取最新
        primary.is_primary = False
        db.add(primary)
        await db.flush()
        task2 = await _create_task(db, test_user.id)
        assert task2.plan_id == newest.id

    @pytest.mark.parametrize("task_type", [TaskType.SOCIAL, TaskType.PLANNING, TaskType.OCR])
    async def test_non_learning_types_not_linked(self, db, test_user, task_type):
        """非学习型任务（社交/规划/OCR）不做默认关联。"""
        sprint = _make_plan(test_user.id, name="冲刺")
        db.add(sprint)
        await db.flush()

        task = await _create_task(db, test_user.id, type_=task_type)
        assert task.plan_id is None

    async def test_learning_family_types_are_linked(self, db, test_user):
        """学习族任务（LEARNING/TRAINING/ERROR_FIX/REFLECTION）默认关联。"""
        sprint = _make_plan(test_user.id, name="冲刺")
        db.add(sprint)
        await db.flush()

        for task_type in (TaskType.LEARNING, TaskType.TRAINING, TaskType.ERROR_FIX, TaskType.REFLECTION):
            task = await _create_task(db, test_user.id, type_=task_type)
            assert task.plan_id == sprint.id, f"{task_type} 应默认关联冲刺计划"
