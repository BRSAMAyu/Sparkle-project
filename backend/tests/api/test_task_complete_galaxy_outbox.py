"""Regression tests for the P1-A fix (sysrev round2).

POST /tasks/{id}/complete returned 500 on every call after the DF-5 galaxy
hook entered the main path: GalaxyStatsService._write_spark_outbox_event used
a ":param::jsonb" PG cast inside sa_text(). SQLAlchemy's TextClause regex
backtracks the bogus name to "payloa" and the asyncpg compiler leaves the raw
":payload" in the statement, so Postgres answers "syntax error at or near
':'"; the warning is swallowed but the transaction stays aborted and the next
SELECT (group_task_claims) blows up with InFailedSqlTransactionError.

On top of the broken cast, the old INSERT omitted aggregate_type (NOT NULL,
no default) and wrote sequence_number=1 for every event, which the gateway's
cursor-based projector (WHERE aggregate_type = $1 AND sequence_number > $2)
would never deliver past the first event. The fix mirrors the proven
GalaxyService._write_mastery_outbox_event pipeline: sequence counters upsert
plus a full-column, cast-free named-parameter INSERT.

These tests pin both layers:
- the SQL statements themselves must compile clean against the asyncpg
  dialect (no bare ":" may survive into what Postgres receives);
- completing a task through the real API must persist a projector-visible
  galaxy outbox row and still answer 200.
"""

from __future__ import annotations

import json
import re
from datetime import date
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_user, get_db
from app.api.v1.tasks import router as tasks_router
from app.core.cache import cache_service
from app.models.base import Base
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User

# ---------------------------------------------------------------------------
# Local SQLite fixture — same approach as test_task_complete_and_update_api.py
# (the shared conftest db_session fixture is not SQLite-safe), plus raw DDL for
# the two CQRS outbox tables, which have no ORM models and therefore would not
# exist in the SQLite schema otherwise.
# ---------------------------------------------------------------------------

_EXCLUDED_TABLES = {"accountability_partnership", "accountability_checkin"}

_OUTBOX_DDL = [
    """
    CREATE TABLE event_outbox (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id TEXT NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        event_version INTEGER NOT NULL DEFAULT 1,
        payload TEXT NOT NULL,
        metadata TEXT,
        sequence_number INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        published_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE event_sequence_counters (
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id TEXT NOT NULL,
        next_sequence INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (aggregate_type, aggregate_id)
    )
    """,
]


@pytest.fixture
async def sqlite_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    tables = [t for name, t in Base.metadata.tables.items() if name not in _EXCLUDED_TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))
        for ddl in _OUTBOX_DDL:
            await conn.execute(text(ddl))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def tasks_client(sqlite_session):
    app = FastAPI()
    app.include_router(tasks_router, prefix="/tasks")

    state = {"current_user": None}

    async def _override_get_db():
        yield sqlite_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    cache_service._local_cache.clear()

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, state

    cache_service._local_cache.clear()


async def _create_user(session) -> User:
    user = User(
        username=f"outbox_p1a_{uuid4().hex[:8]}",
        email=f"outbox_p1a_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_task(session, *, user_id) -> Task:
    task = Task(
        user_id=user_id,
        title=f"P1A outbox 回归任务 {uuid4().hex[:8]}",
        type=TaskType.LEARNING,
        tags=["sysrev-p1-a"],
        estimated_minutes=30,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.IN_PROGRESS,
        priority=1,
        due_date=date.today(),
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


# ===========================================================================
# Layer 1: the outbox SQL must compile clean for the asyncpg dialect
# ===========================================================================


_BARE_NAMED_PARAM = re.compile(r"(?<![:\w\$]):(\w+)")


def _assert_asyncpg_clean(statement_sql: str, params: dict) -> None:
    from sqlalchemy import create_engine as _ce  # noqa: PLC0415 — test helper

    dialect = _ce("postgresql+asyncpg://u:p@localhost/db").dialect
    compiled = text(statement_sql).compile(dialect=dialect)
    rendered = str(compiled)

    leaked = _BARE_NAMED_PARAM.search(rendered)
    assert leaked is None, (
        f"statement still leaks a named ':param' to asyncpg (found ':{leaked.group(1)}'); "
        f"rendered SQL: {rendered!r}"
    )
    assert "::" not in rendered, f"text() + ':param::type' PG casts are forbidden (P1-A); SQL: {rendered!r}"

    positional = compiled.construct_params(params)
    missing = [k for k in positional if positional[k] is None and k in params]
    assert not missing, f"bind params unexpectedly None: {missing}"


def test_spark_outbox_statements_compile_clean_on_asyncpg():
    """The spark outbox SQL must not mix named params with PG '::' casts.

    Regression for P1-A: ':payload::jsonb' made SQLAlchemy register a bogus
    backtracked bind name ('payloa') and left ':payload' literally in the SQL
    handed to asyncpg -> PostgresSyntaxError -> aborted transaction -> 500.
    """
    from app.services.galaxy import stats_service

    payload = {"user_id": "u", "node_id": "n", "mastery_score": 5, "revision": 0}

    _assert_asyncpg_clean(
        stats_service.SPARK_OUTBOX_SEQUENCE_SQL,
        {"aggregate_type": "galaxy_node_mastery", "aggregate_id": str(uuid4())},
    )
    _assert_asyncpg_clean(
        stats_service.SPARK_OUTBOX_INSERT_SQL,
        {
            "aggregate_type": "galaxy_node_mastery",
            "aggregate_id": str(uuid4()),
            "event_type": "galaxy.node.mastery_updated",
            "sequence_number": 1,
            "payload": json.dumps(payload),
            "metadata": json.dumps({"service": "galaxy_stats_service"}),
        },
    )


def test_spark_outbox_insert_covers_not_null_columns():
    """The INSERT must provide every NOT NULL column without a server default.

    The original statement omitted aggregate_type (NOT NULL, no default), so
    even with valid syntax the write would abort the transaction.
    """
    from app.services.galaxy import stats_service

    insert_sql = " ".join(stats_service.SPARK_OUTBOX_INSERT_SQL.split())
    assert "INSERT INTO event_outbox" in insert_sql
    assert "aggregate_type" in insert_sql, "aggregate_type is NOT NULL with no default"
    assert "sequence_number" in insert_sql, (
        "sequence_number must come from event_sequence_counters so the gateway "
        "cursor projector (sequence_number > $2) can deliver every event"
    )


# ===========================================================================
# Layer 2: completing a task through the API persists a projector-visible
# galaxy outbox row and answers 200
# ===========================================================================


async def _fetch_outbox_rows(session) -> list:
    result = await session.execute(
        text(
            "SELECT aggregate_type, aggregate_id, event_type, sequence_number, payload "
            "FROM event_outbox ORDER BY sequence_number"
        )
    )
    return result.all()


@pytest.mark.asyncio
async def test_complete_task_persists_galaxy_outbox_event_and_returns_200(tasks_client, sqlite_session):
    """IN_PROGRESS -> complete: endpoint 200 AND one galaxy outbox event row."""
    client, state = tasks_client
    user = await _create_user(sqlite_session)
    state["current_user"] = user
    task = await _create_task(sqlite_session, user_id=user.id)

    resp = client.post(f"/tasks/{task.id}/complete", json={"actual_minutes": 25})

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["task"]["status"] == TaskStatus.COMPLETED.value

    rows = await _fetch_outbox_rows(sqlite_session)
    assert len(rows) == 1, f"expected exactly one galaxy outbox event, got {len(rows)}"

    aggregate_type, aggregate_id, event_type, sequence_number, payload_raw = rows[0]
    assert aggregate_type == "galaxy_node_mastery"
    assert aggregate_id == str(user.id)
    assert event_type == "galaxy.node.mastery_updated"
    assert sequence_number == 1

    payload = json.loads(payload_raw)
    assert payload["user_id"] == str(user.id)
    assert payload["node_id"]
    assert payload["mastery_score"] > 0


@pytest.mark.asyncio
async def test_second_complete_increments_outbox_sequence(tasks_client, sqlite_session):
    """A second completed task must get sequence_number=2 for the same aggregate.

    The gateway projector reads events with 'sequence_number > cursor'; every
    event at sequence 1 would make all but the first one undeliverable.
    """
    client, state = tasks_client
    user = await _create_user(sqlite_session)
    state["current_user"] = user
    task_a = await _create_task(sqlite_session, user_id=user.id)
    task_b = await _create_task(sqlite_session, user_id=user.id)

    resp_a = client.post(f"/tasks/{task_a.id}/complete", json={"actual_minutes": 20})
    resp_b = client.post(f"/tasks/{task_b.id}/complete", json={"actual_minutes": 20})
    assert resp_a.status_code == 200, resp_a.text
    assert resp_b.status_code == 200, resp_b.text

    rows = await _fetch_outbox_rows(sqlite_session)
    assert len(rows) == 2, f"expected two galaxy outbox events, got {len(rows)}"
    assert [row[3] for row in rows] == [1, 2], "sequence numbers must increment per aggregate"
