"""R2-P2-03 (sysrev round2) — feedback delete_task must decrement total for real.

``FeedbackDrivenAdjustmentService._apply_action`` used to write the MongoDB-style
pseudo-operator ``{"total": {"$dec": N}}`` into ``plan_state.task_index``.
``upsert_plan_state._deep_merge`` has no operator support, so the literal dict
landed in the column and ``plan_progress_service`` (``completed / total``)
blew up with a TypeError. The fix reads, decrements (floored at 0) and writes
back a real integer, refreshing ``avg_completion_rate`` like
``on_task_completed`` does.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.plan import Plan, PlanType
from app.models.plan_state import PlanState
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.feedback_adjustment_service import (
    AdjustmentAction,
    FeedbackDrivenAdjustmentService,
)
from app.services.plan_state_service import PlanStateService

_TABLES = [
    "users",
    "push_preferences",  # users 的 eager relationship 附属表
    "user_intervention_settings",  # 同上
    "plans",
    "tasks",
    "plan_states",
]


@pytest.fixture
async def sqlite_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    tables = [Base.metadata.tables[name] for name in _TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _seed_plan_with_three_tasks(db: AsyncSession) -> tuple[User, Plan, list[Task]]:
    user = User(username=f"fb_{uuid4().hex[:8]}", email=f"fb_{uuid4().hex[:8]}@example.com", hashed_password="x")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    plan = Plan(user_id=user.id, name="反馈删除计划", type=PlanType.GROWTH)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    tasks = []
    for i in range(3):
        task = Task(
            user_id=user.id,
            plan_id=plan.id,
            title=f"相似任务 {i}",
            type=TaskType.LEARNING,
            estimated_minutes=20,
            difficulty=2,
            energy_cost=1,
            status=TaskStatus.PENDING,
            priority=1,
        )
        db.add(task)
        tasks.append(task)
    await db.commit()
    for task in tasks:
        await db.refresh(task)
    return user, plan, tasks


async def _seed_task_index(db: AsyncSession, *, user_id, plan_id) -> None:
    state_service = PlanStateService(db, redis=None)
    await state_service.get_or_create_plan_state(user_id, plan_id)
    await state_service.upsert_plan_state(
        user_id=user_id,
        plan_id=plan_id,
        patch={
            "task_index": {
                "total": 3,
                "completed": 1,
                "by_type": {"LEARNING": {"total": 3, "completed": 1}},
                "avg_completion_rate": 0.333,
            }
        },
        bump_version=False,
    )


async def _reload_task_index(db: AsyncSession, plan_id) -> dict:
    db.expire_all()
    result = await db.execute(select(PlanState).where(PlanState.plan_id == plan_id))
    return dict(result.scalar_one().task_index)


@pytest.mark.asyncio
async def test_delete_task_decrements_total_to_real_int(sqlite_session):
    """delete_task writes a real decremented integer, not a {"$dec": N} dict."""
    user, plan, tasks = await _seed_plan_with_three_tasks(sqlite_session)
    await _seed_task_index(sqlite_session, user_id=user.id, plan_id=plan.id)

    service = FeedbackDrivenAdjustmentService(
        sqlite_session, PlanStateService(sqlite_session, redis=None)
    )
    action = AdjustmentAction(
        action_type="delete_task",
        target_task_ids=[tasks[0].id, tasks[1].id],
        parameters={"reason": "user_skip_similar"},
        reason="skip similar",
        confidence=0.9,
    )
    assert await service._apply_action(action, user.id, plan.id) is True

    task_index = await _reload_task_index(sqlite_session, plan.id)
    assert task_index["total"] == 1, f"total not really decremented: {task_index}"
    assert isinstance(task_index["total"], int)
    assert task_index["completed"] == 1  # completed tasks untouched
    assert task_index["avg_completion_rate"] == 1.0  # 1/1, recomputed
    assert task_index["by_type"]["LEARNING"]["total"] == 3  # by_type untouched (legacy semantics)


@pytest.mark.asyncio
async def test_delete_task_floors_total_at_zero(sqlite_session):
    """Deleting more tasks than the recorded total must not go negative."""
    user, plan, tasks = await _seed_plan_with_three_tasks(sqlite_session)
    await _seed_task_index(sqlite_session, user_id=user.id, plan_id=plan.id)

    service = FeedbackDrivenAdjustmentService(
        sqlite_session, PlanStateService(sqlite_session, redis=None)
    )
    action = AdjustmentAction(
        action_type="delete_task",
        target_task_ids=[t.id for t in tasks],  # 3 deletes vs recorded total 3
        parameters={},
        reason="all removed",
        confidence=0.9,
    )
    # index records 3, delete 3 → 0; a 4th phantom delete must clamp, not wrap
    action.target_task_ids.append(uuid4())
    assert await service._apply_action(action, user.id, plan.id) is True

    task_index = await _reload_task_index(sqlite_session, plan.id)
    assert task_index["total"] == 0, f"total must floor at 0: {task_index}"
    assert task_index["avg_completion_rate"] == 0  # deep-merge 下显式覆盖，不留旧值
