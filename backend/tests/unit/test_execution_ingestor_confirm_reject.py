"""Regression tests for ExecutionIngestor confirm/reject fixes (sysrev round1 #02).

Covers:
- P2-3: HITL confirm double-click race — only one request may consume the
  waiting_approval placeholder; the loser must not re-apply the execution
  result (double task completion / double PlanExecutionRecord).
- P2-4: reject on an already-applied execution result must roll the plan
  progress and plan_state.task_index back, not only the task status.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.execution_intent import (
    ExecutionIntent,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutorType,
    TrustLevel,
)
from app.models.execution_record import ExecutionRecord
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.execution_ingestor import ExecutionIngestor
from app.services.plan_state_service import PlanStateService

_EXCLUDED_TABLES = {"accountability_partnership", "accountability_checkin"}


@pytest.fixture
async def sqlite_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    tables = [t for name, t in Base.metadata.tables.items() if name not in _EXCLUDED_TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def _make_ingestor(db: AsyncSession) -> ExecutionIngestor:
    """Ingestor with side-effect collaborators muted (events/learning/monitor)."""
    ingestor = ExecutionIngestor(db=db, redis=None)
    ingestor._learning_service = AsyncMock()
    ingestor._quality_service = AsyncMock()
    ingestor._plan_record_service = AsyncMock()
    return ingestor


def _mute_ingestor_events(monkeypatch) -> None:
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.execution_ingestor.event_bus.publish", _noop)
    monkeypatch.setattr("app.services.execution_ingestor.task_monitor_service.publish_progress", _noop)


async def _create_user(db) -> User:
    user = User(username=f"ing_{uuid4().hex[:8]}", email=f"ing_{uuid4().hex[:8]}@example.com", hashed_password="x")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_task(db, *, user_id: uuid4, status: TaskStatus) -> Task:
    task = Task(
        user_id=user_id,
        title="委派执行任务",
        type=TaskType.PLANNING,
        estimated_minutes=15,
        difficulty=2,
        energy_cost=1,
        status=status,
        priority=1,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def _create_waiting_intent_and_record(
    db,
    *,
    user: User,
    task: Task,
) -> tuple[ExecutionIntent, ExecutionRecord]:
    intent = ExecutionIntent(
        user_id=user.id,
        task_id=task.id,
        execution_mode=ExecutionMode.HYBRID,
        executor=ExecutorType.OPENCLAW,
        goal="完成表单填写",
        status=ExecutionIntentStatus.WAITING_APPROVAL,
        trust_level=TrustLevel.VALIDATED,
        idempotency_key=f"ik-{uuid4().hex}",
        dispatched_at=datetime.now(UTC).replace(tzinfo=None),
        policy={"approval_policy": "require_before_completion"},
    )
    db.add(intent)
    await db.commit()
    await db.refresh(intent)

    record = ExecutionRecord(
        execution_intent_id=intent.id,
        user_id=user.id,
        task_id=task.id,
        trust_level=TrustLevel.VALIDATED.value,
        raw_response={
            "id": "resp_confirm_race",
            "status": "completed",
            "output": [],
            "requires_approval": True,
            "success": False,
            "error_message": "Waiting for final user confirmation",
        },
        parsed_output={"draft": "已整理草稿"},
        quality_score=0.9,
        validation_passed=1,
        validation_total=1,
        approval_requested=1,
        error_category="approval_required",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return intent, record


# ===========================================================================
# P2-3: concurrent confirm double-click
# ===========================================================================


@pytest.mark.asyncio
async def test_confirm_lost_race_does_not_reapply_result(sqlite_session, monkeypatch):
    """When a concurrent request already consumed the waiting_approval claim,
    the loser must not run _apply_execution_result again (no double completion)."""
    _mute_ingestor_events(monkeypatch)
    user = await _create_user(sqlite_session)
    task = await _create_task(sqlite_session, user_id=user.id, status=TaskStatus.IN_PROGRESS)
    _, record = await _create_waiting_intent_and_record(sqlite_session, user=user, task=task)

    # Simulate the concurrent winner committing its claim behind our back:
    # conditional UPDATE + no session sync keeps the identity-map object stale.
    await sqlite_session.execute(
        update(ExecutionIntent)
        .where(
            ExecutionIntent.id == record.execution_intent_id,
            ExecutionIntent.status == ExecutionIntentStatus.WAITING_APPROVAL,
        )
        .values(status=ExecutionIntentStatus.SUCCEEDED)
        .execution_options(synchronize_session=False)
    )
    await sqlite_session.commit()

    ingestor = _make_ingestor(sqlite_session)
    apply_result_spy = AsyncMock(wraps=ingestor._apply_execution_result)
    ingestor._apply_execution_result = apply_result_spy

    await ingestor.confirm_result(record_id=record.id, user_id=user.id)

    apply_result_spy.assert_not_awaited()
    await sqlite_session.refresh(task)
    assert task.status != TaskStatus.COMPLETED, "loser of the confirm race re-applied the result"


@pytest.mark.asyncio
async def test_confirm_wins_race_and_applies_result(sqlite_session, monkeypatch):
    """Happy path stays intact: claiming the placeholder applies the result once."""
    _mute_ingestor_events(monkeypatch)
    user = await _create_user(sqlite_session)
    task = await _create_task(sqlite_session, user_id=user.id, status=TaskStatus.IN_PROGRESS)
    intent, record = await _create_waiting_intent_and_record(sqlite_session, user=user, task=task)

    ingestor = _make_ingestor(sqlite_session)
    await ingestor.confirm_result(record_id=record.id, user_id=user.id)

    await sqlite_session.refresh(task)
    await sqlite_session.refresh(intent)
    assert task.status == TaskStatus.COMPLETED
    assert intent.status == ExecutionIntentStatus.SUCCEEDED
    assert intent.trust_level == TrustLevel.TRUSTED


@pytest.mark.asyncio
async def test_sequential_double_confirm_does_not_double_apply(sqlite_session, monkeypatch):
    """Second confirm after the intent left waiting_approval keeps the existing
    guard: no second task completion."""
    _mute_ingestor_events(monkeypatch)
    user = await _create_user(sqlite_session)
    task = await _create_task(sqlite_session, user_id=user.id, status=TaskStatus.IN_PROGRESS)
    _, record = await _create_waiting_intent_and_record(sqlite_session, user=user, task=task)

    ingestor = _make_ingestor(sqlite_session)
    await ingestor.confirm_result(record_id=record.id, user_id=user.id)
    completed_at_first = task.completed_at

    record_refetched = (
        await sqlite_session.execute(select(ExecutionRecord).where(ExecutionRecord.id == record.id))
    ).scalar_one()
    await ingestor.confirm_result(record_id=record_refetched.id, user_id=user.id)

    await sqlite_session.refresh(task)
    assert task.status == TaskStatus.COMPLETED
    assert task.completed_at == completed_at_first


# ===========================================================================
# P2-4: reject rolls back plan progress and task_index
# ===========================================================================


async def _create_plan_with_completed_state(db, *, user: User, task: Task) -> Plan:
    plan = Plan(
        user_id=user.id,
        name="执行计划",
        type=PlanType.GROWTH,
        progress=1.0,  # completion-time sync left it at 100%
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    task.plan_id = plan.id
    await db.commit()
    await db.refresh(task)

    # PlanState as it looked right after the delegated completion was ingested.
    state_service = PlanStateService(db, redis=None)
    await state_service.get_or_create_plan_state(user.id, plan.id)
    await state_service.upsert_plan_state(
        user_id=user.id,
        plan_id=plan.id,
        patch={"task_index": {"total": 1, "completed": 1, "by_type": {}, "avg_completion_rate": 1.0}},
        bump_version=False,
    )
    return plan


@pytest.mark.asyncio
async def test_reject_rolls_back_plan_progress_and_task_index(sqlite_session, monkeypatch):
    """Rejecting a completed delegated execution must restore plan progress and
    plan_state.task_index, not just flip the task back to IN_PROGRESS."""
    _mute_ingestor_events(monkeypatch)
    user = await _create_user(sqlite_session)
    task = await _create_task(sqlite_session, user_id=user.id, status=TaskStatus.COMPLETED)
    plan = await _create_plan_with_completed_state(sqlite_session, user=user, task=task)
    intent, record = await _create_waiting_intent_and_record(sqlite_session, user=user, task=task)

    ingestor = _make_ingestor(sqlite_session)
    await ingestor.reject_result(record_id=record.id, user_id=user.id, reason="不满意")

    await sqlite_session.refresh(task)
    await sqlite_session.refresh(plan)
    assert task.status == TaskStatus.IN_PROGRESS  # existing behaviour

    state_service = PlanStateService(sqlite_session, redis=None)
    state = await state_service.get_plan_state(user.id, plan.id, refresh=True)
    assert state is not None
    assert state.task_index["completed"] == 0, f"task_index not rolled back: {state.task_index}"
    assert plan.progress == 0.0, f"plan progress not recomputed: {plan.progress}"
    # the reject must not have left the intent waiting
    await sqlite_session.refresh(intent)
    assert intent.status == ExecutionIntentStatus.HANDED_BACK


# ===========================================================================
# P2-8 (sysrev round1): concurrent dispatch double-run
# ===========================================================================


def _make_dispatch_service(db: AsyncSession):
    from app.services.execution_service import ExecutionService

    service = ExecutionService(db=db, redis=None)

    async def _noop(*args, **kwargs):
        return None

    async def _config(*args, **kwargs):
        return None

    service._ensure_runtime = _config
    service._client = AsyncMock()
    service._client.execute = AsyncMock(return_value={"id": "resp_p28", "status": "completed", "output": []})
    service._ingestor = AsyncMock()
    service._preference_service = AsyncMock()
    service._preference_service.check_budget_allowance = AsyncMock(return_value={"allowed": True})
    service._active_execution_count = AsyncMock(return_value=0)
    service._publish_status_event = _noop
    service._publish_monitor_progress = _noop
    service._record_execution_audit = _noop
    service._clear_failure_state = _noop
    return service


async def _create_ready_intent(db, *, user: User, task: Task) -> ExecutionIntent:
    intent = ExecutionIntent(
        user_id=user.id,
        task_id=task.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal="派发执行",
        status=ExecutionIntentStatus.READY,
        trust_level=TrustLevel.RAW,
        idempotency_key=f"ik-{uuid4().hex}",
    )
    db.add(intent)
    await db.commit()
    await db.refresh(intent)
    return intent


@pytest.mark.asyncio
async def test_dispatch_lost_race_does_not_create_second_run(sqlite_session):
    """When a concurrent request already claimed the dispatch slot, the loser
    must not create another external run."""
    from sqlalchemy import update as sa_update

    user = await _create_user(sqlite_session)
    task = await _create_task(sqlite_session, user_id=user.id, status=TaskStatus.PENDING)
    intent = await _create_ready_intent(sqlite_session, user=user, task=task)

    # Simulate the concurrent winner's committed claim behind our session.
    await sqlite_session.execute(
        sa_update(ExecutionIntent)
        .where(
            ExecutionIntent.id == intent.id,
            ExecutionIntent.status.in_(
                [
                    ExecutionIntentStatus.DRAFT,
                    ExecutionIntentStatus.READY,
                    ExecutionIntentStatus.QUEUED,
                ]
            ),
        )
        .values(status=ExecutionIntentStatus.DISPATCHED)
        .execution_options(synchronize_session=False)
    )
    await sqlite_session.commit()

    service = _make_dispatch_service(sqlite_session)

    with pytest.raises(ValueError, match="concurrently dispatched"):
        await service.dispatch(intent_id=intent.id, user_id=user.id)

    service._client.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_dispatch_wins_race_and_creates_run(sqlite_session):
    """Normal dispatch path stays intact with the claim in place."""
    user = await _create_user(sqlite_session)
    task = await _create_task(sqlite_session, user_id=user.id, status=TaskStatus.PENDING)
    intent = await _create_ready_intent(sqlite_session, user=user, task=task)

    service = _make_dispatch_service(sqlite_session)
    result = await service.dispatch(intent_id=intent.id, user_id=user.id)

    service._client.execute.assert_awaited_once()
    await sqlite_session.refresh(result)
    assert result.status == ExecutionIntentStatus.RUNNING
