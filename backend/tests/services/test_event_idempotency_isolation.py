"""D-01 guards: event idempotency + cross-user isolation (acceptance item 2).

Two layers, both on in-memory SQLite (no dev-DB access):

1. Client telemetry (tracking_events): duplicate event_id re-ingest is deduped
   (no double row, no double downstream publish), and event_ids are globally
   unique so a replay from ANOTHER user cannot create a second row attributed
   to that user. Reads are user-scoped: user B cannot fetch user A's event by
   id.
2. Authoritative outbox writers (galaxy stats_service / galaxy_service /
   learning_asset_service): rows carry the event.v1 shared-field envelope
   (user_id isolation key, deterministic event_id, source, correlation ids),
   so downstream consumers can dedupe by metadata event_id and filter by user.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.event_registry import EVENT_SCHEMA_VERSION, read_event_metadata
from app.models.base import Base
from app.models.event import TrackingEvent
from app.services.event_service import EventService

pytestmark = pytest.mark.asyncio

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


class _RecordingBus:
    """EventBus stand-in that records publishes (downstream-effect proxy)."""

    def __init__(self):
        self.published: list[dict] = []

    async def publish(self, *, event_type: str, payload: dict, stream: str) -> None:
        self.published.append({"event_type": event_type, "payload": payload, "stream": stream})


def _telemetry_event(event_id: str | None = None) -> dict:
    return {
        "event_id": event_id or uuid4().hex,
        "event_type": "question_submit",
        "schema_version": "event.v1",
        "source": "mobile",
        "ts_ms": 1_700_000_000_000,
        "entities": {"question_id": "q1"},
        "payload": {"correct": False},
    }


# --- Layer 1: tracking_events (client telemetry) ------------------------------


async def test_duplicate_event_id_is_deduped_without_double_downstream(sqlite_session):
    bus = _RecordingBus()
    service = EventService(sqlite_session, bus)
    event = _telemetry_event()

    first = await service.ingest_events(uuid4(), [event])
    second = await service.ingest_events(uuid4(), [event])  # full replay

    assert first["accepted"] == 1
    assert second["accepted"] == 0
    assert second["deduped"] == 1

    rows = (await sqlite_session.execute(text("SELECT event_id FROM tracking_events"))).scalars().all()
    assert rows == [event["event_id"]]  # single physical row
    assert len(bus.published) == 1  # exactly one downstream publish


async def test_same_batch_duplicate_is_deduped_in_memory(sqlite_session):
    bus = _RecordingBus()
    service = EventService(sqlite_session, bus)
    event = _telemetry_event()

    result = await service.ingest_events(uuid4(), [event, dict(event)])

    assert result["accepted"] == 1
    assert result["deduped"] == 1
    assert len(bus.published) == 1


async def test_cross_user_replay_cannot_create_or_read_foreign_rows(sqlite_session):
    user_a, user_b = uuid4(), uuid4()
    shared_event_id = uuid4().hex
    bus = _RecordingBus()
    service = EventService(sqlite_session, bus)

    await service.ingest_events(user_a, [_telemetry_event(shared_event_id)])
    # user B replays the SAME event_id: globally unique constraint + pre-fetch
    # dedupe means no second row and nothing attributed to user B.
    replay = await service.ingest_events(user_b, [_telemetry_event(shared_event_id)])
    assert replay["accepted"] == 0
    assert replay["deduped"] == 1

    rows = await sqlite_session.execute(text("SELECT user_id, event_id FROM tracking_events"))
    all_rows = rows.all()
    assert len(all_rows) == 1
    assert str(all_rows[0][0]) == str(user_a)

    # user-scoped read: B cannot fetch A's event even knowing its id.
    assert await service.get_event(user_a, shared_event_id) is not None
    assert await service.get_event(user_b, shared_event_id) is None


async def test_state_estimator_reads_are_user_scoped(sqlite_session):
    # The telemetry-fed Phase-1 estimator must only ever see the calling
    # user's events (user_id predicate in _fetch_recent_events).
    from datetime import datetime

    from app.models.user_state import UserStateSnapshot
    from app.services.state_estimator_service import StateEstimatorService

    user_a, user_b = uuid4(), uuid4()
    for uid, count in ((user_a, 3), (user_b, 2)):
        for i in range(count):
            sqlite_session.add(
                TrackingEvent(
                    event_id=uuid4().hex,
                    user_id=uid,
                    event_type="question_submit",
                    schema_version="event.v1",
                    source="mobile",
                    ts_ms=1_700_000_000_000 + i,
                    entities={},
                    payload={"correct": False},
                    received_at=datetime.utcnow(),
                )
            )
    await sqlite_session.commit()

    estimator = StateEstimatorService(sqlite_session)
    snapshot = await estimator.update_state(user_a, None)
    assert isinstance(snapshot, UserStateSnapshot)
    assert snapshot.user_id == user_a
    # 3 events from user A only — user B's 2 events must not leak in.
    assert len(snapshot.derived_event_ids or []) == 3


# --- Layer 2: outbox writers carry the V3 envelope -----------------------------


async def test_stats_service_spark_outbox_row_carries_envelope_and_task_correlation(sqlite_session):
    from app.services.galaxy.stats_service import GalaxyStatsService

    user_id, node_id, task_id = uuid4(), uuid4(), uuid4()
    service = GalaxyStatsService(sqlite_session)
    await service._write_spark_outbox_event(
        user_id=user_id,
        node_id=node_id,
        new_mastery=7,
        revision=2,
        task_id=task_id,
    )

    row = (
        await sqlite_session.execute(
            text("SELECT aggregate_type, event_type, sequence_number, payload, metadata " "FROM event_outbox")
        )
    ).one()
    assert row.aggregate_type == "galaxy_node_mastery"
    assert row.event_type == "galaxy.node.mastery_updated"
    assert row.sequence_number == 1

    view = read_event_metadata(row.metadata)
    assert view.is_v3_envelope
    assert view.schema_version == EVENT_SCHEMA_VERSION
    assert view.user_id == str(user_id)
    assert view.source == "server_service"
    assert view.service == "galaxy_stats_service"
    assert view.occurred_at is not None and view.occurred_at.tzinfo is None
    assert view.correlation["task_id"] == str(task_id)
    assert view.correlation["node_id"] == str(node_id)
    assert view.event_id and view.event_id.startswith("evt_")

    payload = json.loads(row.payload)
    assert payload["task_id"] == str(task_id)  # causal link visible in payload too


async def test_stats_service_spark_event_id_is_idempotent_per_causal_inputs(sqlite_session):
    from app.services.galaxy.stats_service import GalaxyStatsService

    service = GalaxyStatsService(sqlite_session)
    user_id, node_id, task_id = uuid4(), uuid4(), uuid4()
    await service._write_spark_outbox_event(
        user_id=user_id, node_id=node_id, new_mastery=5, revision=1, task_id=task_id
    )
    await service._write_spark_outbox_event(
        user_id=user_id, node_id=node_id, new_mastery=9, revision=2, task_id=task_id
    )
    metadatas = (
        (await sqlite_session.execute(text("SELECT metadata FROM event_outbox ORDER BY sequence_number")))
        .scalars()
        .all()
    )
    ids = [read_event_metadata(m).event_id for m in metadatas]
    # different sequence numbers -> different deterministic ids; both stable-format
    assert len(set(ids)) == 2
    assert all(i and i.startswith("evt_") for i in ids)


async def test_galaxy_service_mastery_outbox_row_carries_envelope(sqlite_session):
    from app.services.galaxy_service import GalaxyService

    user_id, node_id = uuid4(), uuid4()
    service = GalaxyService(sqlite_session)
    await service._write_mastery_outbox_event(
        aggregate_id=str(user_id),  # str for the raw-SQL SQLite harness (asyncpg takes UUID)
        event_type="galaxy.node.mastery_updated",
        payload={
            "user_id": str(user_id),
            "node_id": str(node_id),
            "mastery_score": 42,
            "revision": 3,
            "timestamp": "2026-09-19T00:00:00",
        },
    )

    row = (await sqlite_session.execute(text("SELECT event_type, metadata FROM event_outbox"))).one()
    assert row[0] == "galaxy.node.mastery_updated"
    view = read_event_metadata(row[1])
    assert view.is_v3_envelope
    assert view.user_id == str(user_id)
    assert view.correlation["node_id"] == str(node_id)
    assert view.service == "galaxy_service"


async def test_learning_asset_outbox_requires_user_id(sqlite_session):
    from app.services.learning_asset_service import LearningAssetService

    service = LearningAssetService()
    with pytest.raises(ValueError, match="user_id"):
        await service._write_event_outbox(
            db=sqlite_session,
            aggregate_type="learning_asset",
            aggregate_id=str(uuid4()),  # str for the raw-SQL SQLite harness
            event_type="asset_status_changed",
            payload={"old_status": "ACTIVE", "new_status": "ARCHIVED"},  # no user_id
        )


async def test_learning_asset_outbox_row_carries_envelope(sqlite_session):
    from app.services.learning_asset_service import LearningAssetService

    user_id = uuid4()
    service = LearningAssetService()
    await service._write_event_outbox(
        db=sqlite_session,
        aggregate_type="learning_asset",
        aggregate_id=str(uuid4()),  # str for the raw-SQL SQLite harness
        event_type="asset_created",
        payload={"user_id": str(user_id), "asset_kind": "vocab"},
        user_id=user_id,
    )
    row = (await sqlite_session.execute(text("SELECT metadata FROM event_outbox"))).one()
    view = read_event_metadata(row[0])
    assert view.is_v3_envelope
    assert view.user_id == str(user_id)
    assert view.service == "learning_asset_service"
