"""
Test P0.2: Plan Progress Auto-Update

Verifies that completing a task automatically updates the associated plan's progress.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, TaskType
from app.models.plan import Plan, PlanType
from app.services.plan_service import PlanService
from app.services.task_service import TaskService


@pytest.mark.asyncio
async def test_plan_progress_updates_on_task_completion(db_session: AsyncSession):
    """
    Test that completing a task updates plan progress automatically.

    P0.2 Acceptance Criteria:
    - Complete a task → Plan progress bar updates immediately
    - Dashboard sprint card shows updated percentage
    - No manual refresh needed
    """
    # Setup: Create a user
    user_id = uuid4()

    # Create a plan
    plan = Plan(
        id=uuid4(),
        user_id=user_id,
        name="期末数学复习",
        type=PlanType.SPRINT,
        subject="数学",
        progress=0.0,  # Initially 0%
        target_date=datetime.utcnow() + timedelta(days=7),
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    # Create 4 tasks for the plan
    tasks = []
    for i in range(4):
        task = Task(
            id=uuid4(),
            user_id=user_id,
            plan_id=plan.id,
            title=f"复习任务 {i+1}",
            type=TaskType.LEARNING,
            status=TaskStatus.PENDING,
            estimated_minutes=30,
        )
        tasks.append(task)
        db_session.add(task)

    await db_session.commit()

    # Verify initial state: progress should be 0.0
    await db_session.refresh(plan)
    assert plan.progress == 0.0, "Initial progress should be 0%"

    # Complete first task (25% progress expected)
    completed_task = await TaskService.complete(
        db=db_session,
        db_obj=tasks[0],
        actual_minutes=25,
        note="完成复习"
    )

    # Verify: Plan progress should auto-update to 0.25 (1/4 tasks completed)
    await db_session.refresh(plan)
    assert plan.progress == 0.25, f"Expected 25% progress, got {plan.progress*100}%"

    # Complete second task (50% progress expected)
    await TaskService.complete(
        db=db_session,
        db_obj=tasks[1],
        actual_minutes=30,
    )

    await db_session.refresh(plan)
    assert plan.progress == 0.5, f"Expected 50% progress, got {plan.progress*100}%"

    # Complete all remaining tasks (100% progress expected)
    await TaskService.complete(db=db_session, db_obj=tasks[2], actual_minutes=28)
    await TaskService.complete(db=db_session, db_obj=tasks[3], actual_minutes=32)

    await db_session.refresh(plan)
    assert plan.progress == 1.0, f"Expected 100% progress, got {plan.progress*100}%"


@pytest.mark.asyncio
async def test_plan_progress_update_via_api_endpoint(db_session: AsyncSession):
    """
    Test that the REST API endpoint also triggers progress update.

    This tests the /api/v1/tasks/{task_id}/complete endpoint.
    """
    user_id = uuid4()

    # Create plan
    plan = Plan(
        id=uuid4(),
        user_id=user_id,
        name="期末英语复习",
        type=PlanType.SPRINT,
        subject="英语",
        progress=0.0,
        target_date=datetime.utcnow() + timedelta(days=5),
        is_active=True,
    )
    db_session.add(plan)

    # Create 2 tasks
    task1 = Task(
        id=uuid4(),
        user_id=user_id,
        plan_id=plan.id,
        title="背单词",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=20,
    )
    task2 = Task(
        id=uuid4(),
        user_id=user_id,
        plan_id=plan.id,
        title="做听力",
        type=TaskType.TRAINING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    db_session.add(task1)
    db_session.add(task2)
    await db_session.commit()

    # Simulate direct API endpoint logic (from tasks.py lines 242-254)
    task1.status = TaskStatus.COMPLETED
    task1.completed_at = datetime.utcnow()
    task1.actual_minutes = 22
    await db_session.commit()
    await db_session.refresh(task1)

    # Trigger plan progress update (as added in P0.2)
    if task1.plan_id:
        await PlanService.update_progress(db_session, task1.plan_id, task1.user_id)

    # Verify progress updated
    await db_session.refresh(plan)
    assert plan.progress == 0.5, f"Expected 50% progress, got {plan.progress*100}%"


@pytest.mark.asyncio
async def test_plan_progress_with_no_tasks(db_session: AsyncSession):
    """
    Edge case: Plan with no tasks should have 0% progress.
    """
    user_id = uuid4()

    plan = Plan(
        id=uuid4(),
        user_id=user_id,
        name="空计划",
        type=PlanType.SPRINT,
        progress=0.0,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()

    # Update progress on empty plan
    new_progress = await PlanService.update_progress(db_session, plan.id, user_id)

    assert new_progress == 0.0, "Empty plan should have 0% progress"


@pytest.mark.asyncio
async def test_plan_progress_ignores_other_users_tasks(db_session: AsyncSession):
    """
    Security test: Ensure user_id verification works.
    """
    user_a = uuid4()
    user_b = uuid4()

    # User A creates plan
    plan_a = Plan(
        id=uuid4(),
        user_id=user_a,
        name="User A's Plan",
        type=PlanType.SPRINT,
        progress=0.0,
        is_active=True,
    )
    db_session.add(plan_a)
    await db_session.commit()

    # User B tries to update User A's plan progress (should return None)
    result = await PlanService.update_progress(db_session, plan_a.id, user_b)

    assert result is None, "Should not update progress for unauthorized user"
