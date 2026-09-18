"""R2-P1-01 (sysrev round2) — JSONB in-place mutation silently dropped from UPDATE.

PlanStateService.on_task_completed / on_task_created used to mutate the
ORM-loaded ``task_index`` / ``facts`` dict in place and hand the same dict back
to ``upsert_plan_state`` as the patch. Inside the upsert, deepcopy + deep-merge
produces a value EQUAL to the already-mutated baseline, so SQLAlchemy's flush
equality check (``persistence._collect_update_commands`` → ``impl.is_equal``)
excludes the column from the UPDATE entirely — completion counts never reach
the database while ``version`` keeps bumping and masking the loss.

This file is the red/green proof and MUST run against real PostgreSQL with two
independent sessions (the second session verifies what the database actually
persisted). Skips when PostgreSQL is unavailable so SQLite-only environments
stay green.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.plan import Plan, PlanType
from app.models.user import User
from app.services.plan_state_service import PlanStateService

_USERNAME_PREFIX = "r2g2_p101_"


def _pg_url() -> str:
    database_url = getattr(settings, "DATABASE_URL", "") or ""
    if not database_url.startswith(("postgresql", "postgres")):
        pytest.skip(f"R2-P1-01 red test requires PostgreSQL, got {database_url!r}")
    return database_url


@pytest.fixture
async def pg_sessions():
    """Two independent async sessions over the real PostgreSQL database."""
    engine = create_async_engine(_pg_url())
    try:
        async with engine.connect() as conn:
            await conn.execute(sa.text("SELECT 1"))
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"PostgreSQL unavailable for R2-P1-01 test: {exc}")

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session_a = session_factory()
    session_b = session_factory()

    # Pre-clean leftovers from any previously crashed run (FK-safe order).
    await _cleanup(session_a)

    try:
        yield session_a, session_b
    finally:
        for session in (session_a, session_b):
            try:
                await _cleanup(session)
            except Exception:
                await session.rollback()
            await session.close()
        await engine.dispose()


async def _cleanup(session: AsyncSession) -> None:
    """Delete every row this test module may have created, children first."""
    await session.execute(
        sa.text(
            "DELETE FROM plan_states WHERE user_id IN "
            "(SELECT id FROM users WHERE username LIKE :pattern)"
        ),
        {"pattern": f"{_USERNAME_PREFIX}%"},
    )
    await session.execute(
        sa.text(
            "DELETE FROM plans WHERE user_id IN "
            "(SELECT id FROM users WHERE username LIKE :pattern)"
        ),
        {"pattern": f"{_USERNAME_PREFIX}%"},
    )
    await session.execute(
        sa.text("DELETE FROM users WHERE username LIKE :pattern"),
        {"pattern": f"{_USERNAME_PREFIX}%"},
    )
    await session.commit()


async def _create_user_and_plan(session_a: AsyncSession) -> tuple[User, Plan]:
    user = User(
        username=f"{_USERNAME_PREFIX}{uuid4().hex[:10]}",
        email=f"{_USERNAME_PREFIX}{uuid4().hex[:10]}@example.com",
        hashed_password="x",
    )
    session_a.add(user)
    await session_a.commit()
    await session_a.refresh(user)

    plan = Plan(user_id=user.id, name="R2-P1-01 验证计划", type=PlanType.GROWTH)
    session_a.add(plan)
    await session_a.commit()
    await session_a.refresh(plan)
    return user, plan


@pytest.mark.asyncio
async def test_on_task_completed_persists_task_index_across_sessions(pg_sessions):
    """Completing a task must persist completed/last_completed_task_id/facts to
    the database, verified from a second, independent session."""
    session_a, session_b = pg_sessions
    user, plan = await _create_user_and_plan(session_a)

    service = PlanStateService(session_a, redis=None)
    # 真实系统路径：建行时即写入非空默认 task_index（plan_state_service.py:188）
    await service.get_or_create_plan_state(user.id, plan.id)

    task_id = uuid4()
    await service.on_task_completed(
        user_id=user.id,
        plan_id=plan.id,
        task_id=task_id,
        task_type="LEARNING",
        actual_minutes=25,
    )

    # 第二个独立 session 只信数据库落库真值
    result = await session_b.execute(
        sa.text("SELECT task_index, facts FROM plan_states WHERE plan_id = :pid"),
        {"pid": str(plan.id)},
    )
    row = result.one()
    task_index, facts = dict(row.task_index), dict(row.facts)

    assert task_index.get("completed") == 1, (
        f"R2-P1-01: completed count not persisted (frozen at 0): {task_index}"
    )
    assert task_index.get("last_completed_task_id") == str(task_id), (
        f"last_completed_task_id not persisted: {task_index}"
    )
    assert task_index.get("by_type", {}).get("LEARNING", {}).get("completed") == 1, (
        f"by_type completed not persisted: {task_index}"
    )
    assert facts.get("avg_task_duration_minutes") == 25, (
        f"avg_task_duration not persisted: {facts}"
    )


@pytest.mark.asyncio
async def test_on_task_completed_counts_two_completions(pg_sessions):
    """Two sequential completions must both land (count reaches 2, not 1 or 0)."""
    session_a, session_b = pg_sessions
    user, plan = await _create_user_and_plan(session_a)

    service = PlanStateService(session_a, redis=None)
    await service.get_or_create_plan_state(user.id, plan.id)

    await service.on_task_completed(
        user_id=user.id, plan_id=plan.id, task_id=uuid4(), task_type="LEARNING"
    )
    await service.on_task_completed(
        user_id=user.id, plan_id=plan.id, task_id=uuid4(), task_type="TRAINING"
    )

    result = await session_b.execute(
        sa.text("SELECT task_index FROM plan_states WHERE plan_id = :pid"),
        {"pid": str(plan.id)},
    )
    task_index = dict(result.one().task_index)
    assert task_index.get("completed") == 2, f"completion count diverged: {task_index}"
    assert task_index["by_type"]["LEARNING"]["completed"] == 1
    assert task_index["by_type"]["TRAINING"]["completed"] == 1


@pytest.mark.asyncio
async def test_on_task_created_persists_total_across_sessions(pg_sessions):
    """Creating tasks must persist the incremented total to the database."""
    session_a, session_b = pg_sessions
    user, plan = await _create_user_and_plan(session_a)

    service = PlanStateService(session_a, redis=None)
    await service.get_or_create_plan_state(user.id, plan.id)

    await service.on_task_created(user_id=user.id, plan_id=plan.id, task_type="LEARNING")
    await service.on_task_created(user_id=user.id, plan_id=plan.id, task_type="LEARNING")

    result = await session_b.execute(
        sa.text("SELECT task_index FROM plan_states WHERE plan_id = :pid"),
        {"pid": str(plan.id)},
    )
    task_index = dict(result.one().task_index)
    assert task_index.get("total") == 2, f"created-task total not persisted: {task_index}"
    assert task_index.get("by_type", {}).get("LEARNING", {}).get("total") == 2, (
        f"by_type total not persisted: {task_index}"
    )
