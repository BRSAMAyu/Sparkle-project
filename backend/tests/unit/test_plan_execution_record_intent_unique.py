"""C2 (sysrev round2) — intent-level uniqueness for plan_execution_records.

Migration ``sr8r2g2_c2_intent`` adds ``plan_execution_records.execution_intent_id``
with a partial unique index (PG) / full unique index with NULLs-distinct
(SQLite), and ``PlanExecutionRecordService.create_record`` now writes the
intent id and falls back to returning the existing record on IntegrityError —
the DB-level second line of defense behind the P2-3 conditional claim.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.execution_intent import ExecutionIntent, ExecutionIntentStatus, ExecutionMode, ExecutorType, TrustLevel
from app.models.plan import Plan, PlanType
from app.models.plan_execution_record import PlanExecutionRecord
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.plan_execution_record_service import PlanExecutionRecordService

_TABLES = [
    "users",
    "push_preferences",
    "user_intervention_settings",
    "plans",
    "tasks",
    "execution_intents",
    "plan_execution_records",
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


async def _seed_intent(db: AsyncSession) -> tuple[User, Plan, ExecutionIntent]:
    user = User(username=f"c2_{uuid4().hex[:8]}", email=f"c2_{uuid4().hex[:8]}@example.com", hashed_password="x")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    plan = Plan(user_id=user.id, name="C2 验证计划", type=PlanType.GROWTH)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="委派任务",
        type=TaskType.PLANNING,
        estimated_minutes=15,
        difficulty=2,
        energy_cost=1,
        status=TaskStatus.IN_PROGRESS,
        priority=1,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    intent = ExecutionIntent(
        user_id=user.id,
        task_id=task.id,
        plan_id=plan.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal="完成执行",
        status=ExecutionIntentStatus.SUCCEEDED,
        trust_level=TrustLevel.TRUSTED,
        idempotency_key=f"ik-{uuid4().hex}",
    )
    db.add(intent)
    await db.commit()
    await db.refresh(intent)
    return user, plan, intent


def _service_kwargs(plan: Plan, user: User, intent: ExecutionIntent) -> dict:
    return dict(
        plan_id=plan.id,
        user_id=user.id,
        validation_status="passed",
        quality_score=0.9,
        criteria_results={"trust_level": "trusted"},
        tool_summary={"total": 1, "successful": 1, "failed": 0},
        issues=[],
        execution_intent_id=intent.id,
    )


def _orm_kwargs(plan: Plan, user: User, intent: ExecutionIntent) -> dict:
    return dict(
        plan_id=plan.id,
        user_id=user.id,
        validation_status="passed",
        quality_score=0.9,
        criteria_results={"trust_level": "trusted"},
        total_tools=1,
        successful_tools=1,
        failed_tools=0,
        issues=[],
        execution_intent_id=intent.id,
    )


@pytest.mark.asyncio
async def test_duplicate_intent_record_returns_existing(sqlite_session):
    """A second create_record for the same intent must return the existing row
    instead of raising (DB-level idempotency behind the P2-3 claim)."""
    user, plan, intent = await _seed_intent(sqlite_session)
    service = PlanExecutionRecordService(sqlite_session)
    plan_id = plan.id  # rollback 会过期会话内对象，先取值

    first = await service.create_record(**_service_kwargs(plan, user, intent))
    first_id = first.id
    second = await service.create_record(**_service_kwargs(plan, user, intent))

    assert second.id == first_id, "duplicate intent record was not deduplicated"
    count = len((await service.get_records_by_plan(plan_id)))
    assert count == 1, f"expected exactly 1 record for the intent, got {count}"


@pytest.mark.asyncio
async def test_unique_index_blocks_duplicate_intent_rows(sqlite_session):
    """The unique index itself must reject a second row for the same intent
    (direct ORM insert bypassing create_record's fallback)."""
    user, plan, intent = await _seed_intent(sqlite_session)
    payload = _orm_kwargs(plan, user, intent)

    sqlite_session.add(PlanExecutionRecord(**payload))
    await sqlite_session.commit()

    sqlite_session.add(PlanExecutionRecord(**payload))
    with pytest.raises(Exception):
        await sqlite_session.commit()
    await sqlite_session.rollback()


@pytest.mark.asyncio
async def test_null_intent_records_do_not_conflict(sqlite_session):
    """Legacy rows without intent attribution (NULL) must coexist — the PG
    partial index only covers non-NULL values (SQLite: NULLs are distinct)."""
    user, plan, intent = await _seed_intent(sqlite_session)
    service = PlanExecutionRecordService(sqlite_session)
    kwargs = _service_kwargs(plan, user, intent)
    kwargs["execution_intent_id"] = None

    await service.create_record(**kwargs)
    await service.create_record(**kwargs)

    assert len(await service.get_records_by_plan(plan.id)) == 2
