"""Regression tests for JSONB same-object write-back losses (sysrev round1 #02).

Covers:
- P2-1a: PlanStateService.append_task_summary silently lost the new summary when
  existing summaries were loaded on the same ORM list instance (in-place insert
  + re-assignment of the identical object is a no-op for SQLAlchemy history).
- P2-1b: PlanFeedbackService.update_feedback_decision lost the user's decision
  when no Redis cache is configured (in-place entry mutation + replace_feedback_log
  assigning the identical list object back).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.plan_state import PlanState
from app.services.plan_feedback_service import PlanFeedbackService
from app.services.plan_state_service import PlanStateService


@pytest.fixture
async def sqlite_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    tables = [Base.metadata.tables["plan_states"]]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _reload(session: AsyncSession, state: PlanState) -> PlanState:
    """Expire the identity map and re-read the row exactly as the DB has it."""
    plan_id = state.plan_id  # read before expiring (access would trigger a refresh)
    session.expire_all()
    result = await session.execute(select(PlanState).where(PlanState.plan_id == plan_id))
    return result.scalar_one()


# ===========================================================================
# P2-1a: append_task_summary must persist the new summary
# ===========================================================================


@pytest.mark.asyncio
async def test_append_task_summary_persists_with_existing_entries(sqlite_session):
    """With 1..limit-1 existing summaries (the non-empty, non-trimming branch),
    the freshly appended summary must survive commit + reload."""
    service = PlanStateService(sqlite_session, redis=None)
    user_id, plan_id = uuid4(), uuid4()

    await service.get_or_create_plan_state(user_id, plan_id)
    first = {"task_id": "task-1", "title": "旧总结"}
    await service.append_task_summary(user_id, plan_id, first, limit=20)

    state = await service.get_plan_state(user_id, plan_id, refresh=True)
    second = {"task_id": "task-2", "title": "带笔记的新总结"}
    await service.append_task_summary(user_id, plan_id, second, limit=20)

    reloaded = await _reload(sqlite_session, state)
    titles = [s["task_id"] for s in (reloaded.task_summaries or [])]
    assert "task-2" in titles, f"new summary lost after write-back: {reloaded.task_summaries}"
    assert "task-1" in titles
    assert titles[0] == "task-2"  # newest first


@pytest.mark.asyncio
async def test_append_task_summary_trims_to_limit(sqlite_session):
    """The trimming branch (which used to create a new object) keeps working."""
    service = PlanStateService(sqlite_session, redis=None)
    user_id, plan_id = uuid4(), uuid4()
    await service.get_or_create_plan_state(user_id, plan_id)

    for i in range(3):
        await service.append_task_summary(user_id, plan_id, {"task_id": f"task-{i}"}, limit=2)

    state = await service.get_plan_state(user_id, plan_id, refresh=True)
    reloaded = await _reload(sqlite_session, state)
    ids = [s["task_id"] for s in reloaded.task_summaries]
    assert ids == ["task-2", "task-1"]


# ===========================================================================
# P2-1b: update_feedback_decision must persist without Redis
# ===========================================================================


@pytest.mark.asyncio
async def test_update_feedback_decision_persists_without_redis(sqlite_session):
    """User approve/reject decisions must survive a DB reload even when the
    plan state is read straight from the DB session (no Redis cache)."""
    service = PlanStateService(sqlite_session, redis=None)
    user_id, plan_id = uuid4(), uuid4()
    await service.get_or_create_plan_state(user_id, plan_id)

    await service.append_feedback(
        user_id=user_id,
        plan_id=plan_id,
        feedback_type="auto_adjustment",
        content="调整了执行参数",
        applied_adjustment={"review_id": "rev-1", "decision": "pending"},
    )

    feedback_service = PlanFeedbackService(sqlite_session, redis=None)
    result = await feedback_service.update_feedback_decision(
        user_id=user_id,
        plan_id=plan_id,
        review_id="rev-1",
        user_decision="approve",
        user_comment="看起来不错",
    )
    assert result is not None

    state = await service.get_plan_state(user_id, plan_id, refresh=True)
    reloaded = await _reload(sqlite_session, state)
    entry = reloaded.feedback_log[0]
    assert entry["applied_adjustment"]["decision"] == "approve", f"decision lost without redis: {entry}"
    assert entry["decision"] == "approve"
    assert entry["user_comment"] == "看起来不错"


@pytest.mark.asyncio
async def test_update_feedback_decision_reject_bumps_priority(sqlite_session):
    service = PlanStateService(sqlite_session, redis=None)
    user_id, plan_id = uuid4(), uuid4()
    await service.get_or_create_plan_state(user_id, plan_id)
    await service.append_feedback(
        user_id=user_id,
        plan_id=plan_id,
        feedback_type="auto_adjustment",
        content="调整了执行参数",
        applied_adjustment={"review_id": "rev-2", "decision": "pending"},
    )

    feedback_service = PlanFeedbackService(sqlite_session, redis=None)
    await feedback_service.update_feedback_decision(
        user_id=user_id,
        plan_id=plan_id,
        review_id="rev-2",
        user_decision="reject",
    )

    state = await service.get_plan_state(user_id, plan_id, refresh=True)
    reloaded = await _reload(sqlite_session, state)
    entry = reloaded.feedback_log[0]
    assert entry["applied_adjustment"]["decision"] == "reject"
    assert entry["applied_adjustment"]["priority"] == "high"
    assert entry["priority"] == "high"
