"""P2-G (daily-flow R2): tasks/today's "today" filter must actually filter.

Undated open tasks used to be unconditionally today-relevant, so the intake's
32-day template (``day:N`` tags / day-encoded order_index) flooded the today
list (R2 eval: 50 PENDING rows, zero today semantics). Sequenced plan tasks
now count only up to the plan's current day; plan-less undated tasks count
only on their creation day.
"""

from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.services.daily_task_selection_service import (
    DailyTaskSelectionService,
    _is_today_relevant,
    _plan_current_day,
    _task_day_index,
)


def _make_task(*, status=TaskStatus.PENDING, due_date=None, tags=None, order_index=0, created_at=None) -> Task:
    task = Task(
        user_id=uuid4(),
        title="task",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        status=status,
        due_date=due_date,
        tags=tags or [],
        order_index=order_index,
    )
    if created_at is not None:
        task.created_at = created_at
    return task


def test_undated_plan_task_beyond_current_day_is_not_today_relevant():
    today = date.today()
    plan = Plan(
        name="32天冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        priority=PlanPriority.HIGH,
        target_date=today + timedelta(days=29),  # 32-day plan created 3 days ago
        created_at=today - timedelta(days=3),
    )
    assert _plan_current_day(plan, today) == 4

    future_day_task = _make_task(tags=["day:5"], order_index=5 * 1000)
    current_day_task = _make_task(tags=["day:3"], order_index=3 * 1000)

    assert _task_day_index(future_day_task) == 5
    assert _is_today_relevant(current_day_task, today, plan=plan) is True
    assert _is_today_relevant(future_day_task, today, plan=plan) is False


def test_undated_planless_task_counts_only_on_creation_day():
    today = date.today()
    fresh = _make_task(created_at=today)
    stale = _make_task(created_at=today - timedelta(days=2))

    assert _is_today_relevant(fresh, today, plan=None) is True
    assert _is_today_relevant(stale, today, plan=None) is False


def test_due_and_active_tasks_keep_existing_semantics():
    today = date.today()
    overdue = _make_task(due_date=today - timedelta(days=1))
    due_today = _make_task(due_date=today)
    future = _make_task(due_date=today + timedelta(days=3))
    in_progress = _make_task(status=TaskStatus.IN_PROGRESS, due_date=today + timedelta(days=3))

    assert _is_today_relevant(overdue, today) is True
    assert _is_today_relevant(due_today, today) is True
    # Future-dated open tasks were already excluded before P2-G.
    assert _is_today_relevant(future, today) is False
    assert _is_today_relevant(in_progress, today) is True


@pytest.mark.asyncio
async def test_select_tasks_today_excludes_later_sprint_days(db_session):
    """End-to-end over select_tasks: the 32-day template collapses to the
    current frontier days instead of returning everything."""
    from app.models.user import User

    user = User(username="p2g_user", email="p2g_user@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()

    today = date.today()
    plan = Plan(
        user_id=user.id,
        name="32天冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        priority=PlanPriority.HIGH,
        target_date=today + timedelta(days=29),
    )
    db_session.add(plan)
    await db_session.flush()
    plan.created_at = today - timedelta(days=2)  # 31-day window, day 3 of it today

    # A 32-day intake-style template: only day 1-3 may surface for today.
    for day in range(1, 33):
        db_session.add(
            Task(
                user_id=user.id,
                plan_id=plan.id,
                title=f"Day {day} · 冲刺",
                type=TaskType.LEARNING,
                estimated_minutes=60,
                tags=[f"day:{day}"],
                order_index=day * 1000,
            )
        )
    # Plus a stale plan-less undated self-created task: not today's.
    db_session.add(
        Task(
            user_id=user.id,
            title="旧的自建任务",
            type=TaskType.LEARNING,
            estimated_minutes=30,
            created_at=today - timedelta(days=5),
        )
    )
    await db_session.commit()

    service = DailyTaskSelectionService(db_session, redis=None)
    selections = await service.select_tasks(
        user_id=user.id,
        limit=50,
        include_completed_today=True,
        only_today_relevant=True,
    )

    titles = {selection.task.title for selection in selections}
    assert len(selections) <= 3
    assert all("Day 4" not in t and "Day 32" not in t and "旧的自建任务" not in t for t in titles)
    assert any("Day 1" in t for t in titles)
