"""
Integration test: Error Book -> Galaxy mastery sync pipeline.

Validates the end-to-end flow where error evidence flows from error record
creation through to Galaxy knowledge node mastery updates. Uses an in-memory
SQLite database with real SQLAlchemy models to exercise actual DB queries,
session management, and the service integration layer.

Covers:
  1. Error diagnosis with linked_knowledge_node_ids decreases node mastery.
  2. Error analysis updates related knowledge nodes via mastery sync.
  3. Mastery delta is proportional to error severity / error type.
  4. Multi-node rank-weighted decay is applied correctly.
  5. Review feedback (remembered/fuzzy/forgot) adjusts mastery accordingly.
  6. StudyRecords are persisted for audit trail.
  7. Repeated errors on the same node accumulate correctly (cumulative pressure).
  8. Mastery stays within [0, 100] bounds.
  9. Node mastery updated events are deferred (not published inline).
  10. Combined diagnosis -> review flow round-trips correctly.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.models.base import Base
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.user import User
from app.services.error_book_mastery_sync_service import (
    ERROR_TYPE_IMPACT,
    NODE_RANK_WEIGHTS,
    REVIEW_PERFORMANCE_IMPACT,
    ErrorBookMasterySyncService,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_user(db_session: AsyncSession) -> User:
    user = User(
        username="mastery_sync_test",
        email="mastery_sync_test@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _seed_knowledge_node(
    db_session: AsyncSession,
    user: User,
    *,
    name: str = "Test Node",
    mastery_score: float = 50.0,
    is_unlocked: bool = True,
) -> tuple[KnowledgeNode, UserNodeStatus]:
    """Create a KnowledgeNode + UserNodeStatus pair for testing."""
    node = KnowledgeNode(name=name, description=f"Description for {name}")
    db_session.add(node)
    await db_session.flush()

    status = UserNodeStatus(
        user_id=user.id,
        node_id=node.id,
        mastery_score=mastery_score,
        bkt_mastery_prob=mastery_score / 100.0,
        is_unlocked=is_unlocked,
        study_count=3,
        total_minutes=0,
        total_study_minutes=0,
        revision=0,
    )
    db_session.add(status)
    await db_session.commit()
    await db_session.refresh(node)
    await db_session.refresh(status)
    return node, status


def _make_error_record(
    db_session: AsyncSession,
    user: User,
    *,
    linked_node_ids: list[UUID],
    error_type: str = "concept_confusion",
    subject_code: str = "math",
) -> ErrorRecord:
    """Create a persisted ErrorRecord with linked knowledge nodes.

    Converts UUID objects to strings for linked_knowledge_node_ids because
    SQLite's JSON fallback cannot serialize UUID objects natively.
    The mastery sync service reads linked_knowledge_node_ids and converts
    strings back to UUID internally, so string storage is safe.
    """
    error = ErrorRecord(
        user_id=user.id,
        subject_code=subject_code,
        question_text="What is the derivative of sin(x)?",
        user_answer="cos(x^2)",
        correct_answer="cos(x)",
        linked_knowledge_node_ids=[str(nid) for nid in linked_node_ids],
        latest_analysis={"error_type": error_type, "root_cause": "confused chain rule"},
        mastery_level=0.3,
        review_count=0,
    )
    db_session.add(error)
    return error


def _build_service(db: AsyncSession, node_statuses: dict[UUID, UserNodeStatus]):
    """Build an ErrorBookMasterySyncService with the Galaxy write path mocked.

    The mock simulates GalaxyService.update_node_mastery by directly mutating
    the UserNodeStatus objects in the DB session, mirroring real behavior.
    """
    redis_mock = MagicMock()

    with patch("app.services.error_book_mastery_sync_service.GalaxyStatsService") as MockStatsCls:
        mock_stats_instance = MagicMock()
        mock_stats_instance._calculate_next_review = MagicMock(
            return_value=datetime.now(timezone.utc) + timedelta(days=3)
        )
        MockStatsCls.return_value = mock_stats_instance
        service = ErrorBookMasterySyncService(db, redis_mock)

    # Stub the GalaxyService write path to operate on our in-memory statuses.
    async def _mock_write_node_mastery_via_galaxy(
        *, user_id, node_id, new_mastery, reason, request_id, revision
    ):
        status = node_statuses.get(node_id)
        old_mastery = float(status.mastery_score) if status is not None else 0.0

        if status is not None:
            status.mastery_score = float(new_mastery)
            status.bkt_mastery_prob = round(float(new_mastery) / 100.0, 2)
            status.revision = (status.revision or 0) + 1
            status.updated_at = datetime.now(timezone.utc)
            if not status.is_unlocked and float(new_mastery) > 0:
                status.is_unlocked = True
                status.first_unlock_at = datetime.now(timezone.utc)

        return {
            "success": True,
            "old_mastery": old_mastery,
            "new_mastery": float(new_mastery),
        }

    service._write_node_mastery_via_galaxy = _mock_write_node_mastery_via_galaxy

    # Patch _get_or_create_node_status to use the DB session directly
    async def _mock_get_or_create(user_id, node_id, *, create_if_missing=True):
        result = await db.execute(
            select(UserNodeStatus).where(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == node_id,
            )
        )
        status = result.scalar_one_or_none()
        if status:
            node_statuses[node_id] = status
            return status
        if not create_if_missing:
            return None
        status = UserNodeStatus(
            user_id=user_id,
            node_id=node_id,
            mastery_score=0,
            is_unlocked=False,
            study_count=0,
            bkt_mastery_prob=0.0,
            revision=0,
        )
        db.add(status)
        await db.flush()
        node_statuses[node_id] = status
        return status

    service._get_or_create_node_status = _mock_get_or_create

    # Patch _evaluate_impacted_plans to avoid needing Plan/Task tables
    service._evaluate_impacted_plans = AsyncMock()
    service._count_recent_errors_for_node = AsyncMock(return_value=0)
    service._find_impacted_active_plans = AsyncMock(return_value=set())

    return service


# ===========================================================================
# Test 1: Error diagnosis with linked_knowledge_node_ids decreases mastery
# ===========================================================================


@pytest.mark.asyncio
async def test_diagnosis_decreases_linked_node_mastery(
    db_session: AsyncSession,
    seeded_user: User,
):
    """When an error record has linked_knowledge_node_ids, mastery decreases."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=60.0)
    initial_mastery = status.mastery_score

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
        error_type="concept_confusion",
    )
    await db_session.commit()

    service = _build_service(db_session, {node.id: status})
    results = await service.apply_error_diagnosis(seeded_user.id, error)

    assert len(results) == 1
    assert results[0]["old_mastery"] == 60
    assert results[0]["new_mastery"] == 52  # 60 - 8 for concept_confusion
    assert results[0]["delta"] == -8
    assert results[0]["record_type"] == "error_diagnosis"
    assert results[0]["node_id"] == str(node.id)

    # Verify the UserNodeStatus in DB was mutated
    await db_session.refresh(status)
    assert status.mastery_score == 52.0


# ===========================================================================
# Test 2: Error analysis updates related knowledge nodes via mastery sync
# ===========================================================================


@pytest.mark.asyncio
async def test_analysis_updates_multiple_related_nodes(
    db_session: AsyncSession,
    seeded_user: User,
):
    """When analysis identifies multiple related nodes, all get mastery updates."""
    node_a, status_a = await _seed_knowledge_node(
        db_session, seeded_user, name="Node A", mastery_score=70.0
    )
    node_b, status_b = await _seed_knowledge_node(
        db_session, seeded_user, name="Node B", mastery_score=55.0
    )

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node_a.id, node_b.id],
        error_type="knowledge_gap",  # base -10
    )
    await db_session.commit()

    service = _build_service(db_session, {node_a.id: status_a, node_b.id: status_b})
    results = await service.apply_error_diagnosis(seeded_user.id, error)

    assert len(results) == 2

    # Primary node (rank 0): full weight -10
    assert results[0]["node_id"] == str(node_a.id)
    assert results[0]["delta"] == -10
    assert results[0]["new_mastery"] == 60

    # Secondary node (rank 1): 60% weight = -6
    assert results[1]["node_id"] == str(node_b.id)
    assert results[1]["delta"] == -6
    assert results[1]["new_mastery"] == 49


# ===========================================================================
# Test 3: Mastery delta proportional to error severity
# ===========================================================================


@pytest.mark.asyncio
async def test_mastery_delta_proportional_to_error_type(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Different error types produce different deltas (severity proportional)."""
    error_types_and_deltas = [
        ("knowledge_gap", -10),
        ("concept_confusion", -8),
        ("method_wrong", -6),
        ("logic_error", -5),
        ("calculation_error", -3),
        ("reading_careless", -2),
    ]

    for error_type, expected_delta in error_types_and_deltas:
        node, status = await _seed_knowledge_node(
            db_session, seeded_user, name=f"Node-{error_type}", mastery_score=50.0
        )

        error = _make_error_record(
            db_session,
            seeded_user,
            linked_node_ids=[node.id],
            error_type=error_type,
        )
        await db_session.commit()

        service = _build_service(db_session, {node.id: status})
        results = await service.apply_error_diagnosis(seeded_user.id, error)

        assert len(results) == 1, f"No results for error_type={error_type}"
        assert results[0]["delta"] == expected_delta, (
            f"error_type={error_type}: expected delta={expected_delta}, got {results[0]['delta']}"
        )
        assert results[0]["new_mastery"] == 50 + expected_delta


# ===========================================================================
# Test 4: Repeated errors on same node accumulate (cumulative pressure)
# ===========================================================================


@pytest.mark.asyncio
async def test_repeated_errors_accumulate_mastery_decrease(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Multiple errors on the same node accumulate mastery decreases."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=80.0)

    service = _build_service(db_session, {node.id: status})

    # First error: concept_confusion -> -8
    error1 = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
        error_type="concept_confusion",
    )
    await db_session.commit()
    results1 = await service.apply_error_diagnosis(seeded_user.id, error1)
    assert results1[0]["new_mastery"] == 72

    await db_session.refresh(status)

    # Second error: knowledge_gap -> -10
    error2 = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
        error_type="knowledge_gap",
    )
    await db_session.commit()
    results2 = await service.apply_error_diagnosis(seeded_user.id, error2)
    assert results2[0]["old_mastery"] == 72
    assert results2[0]["new_mastery"] == 62  # 72 - 10

    await db_session.refresh(status)

    # Third error: method_wrong -> -6
    error3 = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
        error_type="method_wrong",
    )
    await db_session.commit()
    results3 = await service.apply_error_diagnosis(seeded_user.id, error3)
    assert results3[0]["old_mastery"] == 62
    assert results3[0]["new_mastery"] == 56  # 62 - 6

    # Total accumulated decrease: 80 -> 56 = -24
    await db_session.refresh(status)
    assert status.mastery_score == 56.0


# ===========================================================================
# Test 5: Review feedback adjusts mastery correctly
# ===========================================================================


@pytest.mark.asyncio
async def test_review_remembered_recovers_mastery(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Review with 'remembered' performance recovers node mastery by +4."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=45.0)

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
    )
    await db_session.commit()

    service = _build_service(db_session, {node.id: status})
    results = await service.apply_review_feedback(seeded_user.id, error, "remembered")

    assert len(results) == 1
    assert results[0]["delta"] == 4
    assert results[0]["new_mastery"] == 49
    assert results[0]["record_type"] == "error_review"

    await db_session.refresh(status)
    assert status.mastery_score == 49.0


@pytest.mark.asyncio
async def test_review_forgot_further_decreases_mastery(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Review with 'forgot' performance further decreases node mastery by -2."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=30.0)

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
    )
    await db_session.commit()

    service = _build_service(db_session, {node.id: status})
    results = await service.apply_review_feedback(seeded_user.id, error, "forgot")

    assert len(results) == 1
    assert results[0]["delta"] == -2
    assert results[0]["new_mastery"] == 28


@pytest.mark.asyncio
async def test_review_fuzzy_slight_increase(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Review with 'fuzzy' performance slightly increases mastery by +1."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=40.0)

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
    )
    await db_session.commit()

    service = _build_service(db_session, {node.id: status})
    results = await service.apply_review_feedback(seeded_user.id, error, "fuzzy")

    assert len(results) == 1
    assert results[0]["delta"] == 1
    assert results[0]["new_mastery"] == 41


# ===========================================================================
# Test 6: StudyRecords are persisted in DB
# ===========================================================================


@pytest.mark.asyncio
async def test_diagnosis_persists_study_record(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Error diagnosis writes a StudyRecord with correct fields."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=55.0)

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
        error_type="concept_confusion",
    )
    await db_session.commit()

    service = _build_service(db_session, {node.id: status})
    await service.apply_error_diagnosis(seeded_user.id, error)
    await db_session.commit()

    # Query StudyRecords for this user + node
    result = await db_session.execute(
        select(StudyRecord).where(
            StudyRecord.user_id == seeded_user.id,
            StudyRecord.node_id == node.id,
        )
    )
    records = result.scalars().all()

    assert len(records) == 1
    record = records[0]
    assert record.record_type == "error_diagnosis"
    assert record.mastery_delta == -8.0
    assert record.initial_mastery == 55.0
    assert record.study_minutes == 0


@pytest.mark.asyncio
async def test_review_persists_study_record(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Review feedback writes a StudyRecord with correct fields."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=47.0)

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
    )
    await db_session.commit()

    service = _build_service(db_session, {node.id: status})
    await service.apply_review_feedback(seeded_user.id, error, "remembered")
    await db_session.commit()

    result = await db_session.execute(
        select(StudyRecord).where(
            StudyRecord.user_id == seeded_user.id,
            StudyRecord.node_id == node.id,
        )
    )
    records = result.scalars().all()

    assert len(records) == 1
    record = records[0]
    assert record.record_type == "error_review"
    assert record.mastery_delta == 4.0
    assert record.initial_mastery == 47.0


# ===========================================================================
# Test 7: Mastery bounds enforced [0, 100]
# ===========================================================================


@pytest.mark.asyncio
async def test_mastery_does_not_drop_below_zero(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Mastery clamps to 0 even with large negative delta."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=3.0)

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
        error_type="knowledge_gap",  # -10
    )
    await db_session.commit()

    service = _build_service(db_session, {node.id: status})
    results = await service.apply_error_diagnosis(seeded_user.id, error)

    assert len(results) == 1
    assert results[0]["new_mastery"] == 0  # Clamped from -7


@pytest.mark.asyncio
async def test_mastery_does_not_exceed_100(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Mastery clamps to 100 on review recovery."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=98.0)

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
    )
    await db_session.commit()

    service = _build_service(db_session, {node.id: status})
    results = await service.apply_review_feedback(seeded_user.id, error, "remembered")

    assert len(results) == 1
    assert results[0]["new_mastery"] == 100  # Clamped from 102


# ===========================================================================
# Test 8: Node mastery updated events are deferred
# ===========================================================================


@pytest.mark.asyncio
async def test_diagnosis_defers_node_mastery_updated_event(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Events are returned in _pending_event, not published inline."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=50.0)

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
        error_type="concept_confusion",
    )
    await db_session.commit()

    service = _build_service(db_session, {node.id: status})
    results = await service.apply_error_diagnosis(seeded_user.id, error)

    assert len(results) == 1
    assert "_pending_event" in results[0]
    event = results[0]["_pending_event"]
    assert event["topic"] == "node_mastery_updated"
    payload = event["payload"]
    assert payload["old_mastery"] == 50
    assert payload["new_mastery"] == 42
    assert payload["node_id"] == str(node.id)
    assert payload["user_id"] == str(seeded_user.id)


# ===========================================================================
# Test 9: Combined diagnosis -> review round-trip
# ===========================================================================


@pytest.mark.asyncio
async def test_combined_diagnosis_then_review_flow(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Full pipeline: diagnosis reduces mastery, then review recovers it."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=65.0)

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
        error_type="concept_confusion",
    )
    await db_session.commit()

    service = _build_service(db_session, {node.id: status})

    # Step 1: Diagnosis -> -8
    diag_results = await service.apply_error_diagnosis(seeded_user.id, error)
    assert len(diag_results) == 1
    assert diag_results[0]["new_mastery"] == 57
    assert diag_results[0]["record_type"] == "error_diagnosis"

    await db_session.refresh(status)

    # Step 2: Review (remembered) -> +4
    review_results = await service.apply_review_feedback(
        seeded_user.id, error, "remembered"
    )
    assert len(review_results) == 1
    assert review_results[0]["old_mastery"] == 57
    assert review_results[0]["new_mastery"] == 61
    assert review_results[0]["record_type"] == "error_review"

    # Verify final state in DB
    await db_session.refresh(status)
    assert status.mastery_score == 61.0

    # Verify both StudyRecords exist
    result = await db_session.execute(
        select(StudyRecord).where(
            StudyRecord.user_id == seeded_user.id,
            StudyRecord.node_id == node.id,
        ).order_by(StudyRecord.created_at)
    )
    records = result.scalars().all()
    assert len(records) == 2
    assert records[0].record_type == "error_diagnosis"
    assert records[0].mastery_delta == -8.0
    assert records[1].record_type == "error_review"
    assert records[1].mastery_delta == 4.0


# ===========================================================================
# Test 10: No linked nodes -> no updates
# ===========================================================================


@pytest.mark.asyncio
async def test_no_linked_nodes_returns_empty(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Error without linked nodes produces no mastery changes."""
    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[],
        error_type="concept_confusion",
    )
    error.linked_knowledge_node_ids = []
    await db_session.commit()

    service = _build_service(db_session, {})
    results = await service.apply_error_diagnosis(seeded_user.id, error)

    assert results == []
    assert error.latest_analysis["linking_hint"]["code"] == "missing_knowledge_links"


# ===========================================================================
# Test 11: Multi-node rank-weighted decay across 3 nodes
# ===========================================================================


@pytest.mark.asyncio
async def test_three_node_rank_weighted_decay(
    db_session: AsyncSession,
    seeded_user: User,
):
    """3 linked nodes receive decaying impacts: 1.0, 0.6, 0.3."""
    node_a, status_a = await _seed_knowledge_node(
        db_session, seeded_user, name="Primary", mastery_score=70.0
    )
    node_b, status_b = await _seed_knowledge_node(
        db_session, seeded_user, name="Secondary", mastery_score=60.0
    )
    node_c, status_c = await _seed_knowledge_node(
        db_session, seeded_user, name="Tertiary", mastery_score=50.0
    )

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node_a.id, node_b.id, node_c.id],
        error_type="concept_confusion",  # base -8
    )
    await db_session.commit()

    service = _build_service(
        db_session,
        {node_a.id: status_a, node_b.id: status_b, node_c.id: status_c},
    )
    results = await service.apply_error_diagnosis(seeded_user.id, error)

    assert len(results) == 3

    # Node A (rank 0): -8 * 1.0 = -8 -> 70 - 8 = 62
    assert results[0]["delta"] == -8
    assert results[0]["new_mastery"] == 62

    # Node B (rank 1): -8 * 0.6 = -4.8 -> round(-4.8) = -5 -> 60 - 5 = 55
    assert results[1]["delta"] == -5
    assert results[1]["new_mastery"] == 55

    # Node C (rank 2): -8 * 0.3 = -2.4 -> round(-2.4) = -2 -> 50 - 2 = 48
    assert results[2]["delta"] == -2
    assert results[2]["new_mastery"] == 48


# ===========================================================================
# Test 12: Caps at 3 nodes max
# ===========================================================================


@pytest.mark.asyncio
async def test_more_than_3_linked_nodes_caps_at_3(
    db_session: AsyncSession,
    seeded_user: User,
):
    """More than 3 linked nodes only processes the first 3."""
    nodes_and_statuses = []
    for i in range(5):
        n, s = await _seed_knowledge_node(
            db_session, seeded_user, name=f"Node-{i}", mastery_score=50.0
        )
        nodes_and_statuses.append((n, s))

    node_ids = [n.id for n, _ in nodes_and_statuses]
    status_map = {n.id: s for n, s in nodes_and_statuses}

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=node_ids,
        error_type="concept_confusion",
    )
    await db_session.commit()

    service = _build_service(db_session, status_map)
    results = await service.apply_error_diagnosis(seeded_user.id, error)

    assert len(results) == 3


# ===========================================================================
# Test 13: Error with no existing UserNodeStatus creates one
# ===========================================================================


@pytest.mark.asyncio
async def test_diagnosis_creates_status_for_new_node_on_positive_review(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Review on a node with no prior status creates one and applies delta."""
    node = KnowledgeNode(name="Fresh Node", description="no status yet")
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
    )
    await db_session.commit()

    service = _build_service(db_session, {})
    results = await service.apply_review_feedback(seeded_user.id, error, "remembered")

    # New node at 0 + 4 = 4
    assert len(results) == 1
    assert results[0]["old_mastery"] == 0
    assert results[0]["new_mastery"] == 4


# ===========================================================================
# Test 14: study_count increments after diagnosis
# ===========================================================================


@pytest.mark.asyncio
async def test_diagnosis_increments_study_count(
    db_session: AsyncSession,
    seeded_user: User,
):
    """After diagnosis, the UserNodeStatus.study_count increments by 1."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=50.0)
    initial_study_count = status.study_count

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
        error_type="concept_confusion",
    )
    await db_session.commit()

    service = _build_service(db_session, {node.id: status})
    await service.apply_error_diagnosis(seeded_user.id, error)
    await db_session.commit()

    # Re-query to get the latest state from DB
    result = await db_session.execute(
        select(UserNodeStatus).where(
            UserNodeStatus.user_id == seeded_user.id,
            UserNodeStatus.node_id == node.id,
        )
    )
    refreshed = result.scalar_one()
    assert refreshed.study_count == initial_study_count + 1


# ===========================================================================
# Test 15: BKT probability updates with mastery
# ===========================================================================


@pytest.mark.asyncio
async def test_bkt_probability_updates_with_mastery(
    db_session: AsyncSession,
    seeded_user: User,
):
    """After mastery update, bkt_mastery_prob reflects new mastery."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=80.0)

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
        error_type="knowledge_gap",  # -10
    )
    await db_session.commit()

    service = _build_service(db_session, {node.id: status})
    await service.apply_error_diagnosis(seeded_user.id, error)

    await db_session.refresh(status)
    assert status.mastery_score == 70.0
    assert status.bkt_mastery_prob == pytest.approx(0.7, abs=0.01)


# ===========================================================================
# Test 16: Revision increments on mastery update
# ===========================================================================


@pytest.mark.asyncio
async def test_revision_increments_on_mastery_update(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Each mastery update increments the revision counter."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=50.0)
    assert status.revision == 0

    error = _make_error_record(
        db_session,
        seeded_user,
        linked_node_ids=[node.id],
        error_type="concept_confusion",
    )
    await db_session.commit()

    service = _build_service(db_session, {node.id: status})
    await service.apply_error_diagnosis(seeded_user.id, error)

    await db_session.refresh(status)
    assert status.revision == 1


# ===========================================================================
# Test 17: Full pipeline stress - multiple errors + review on same node
# ===========================================================================


@pytest.mark.asyncio
async def test_stress_multiple_errors_and_reviews_on_same_node(
    db_session: AsyncSession,
    seeded_user: User,
):
    """Stress test: 3 errors + 2 reviews on the same node, verify final state."""
    node, status = await _seed_knowledge_node(db_session, seeded_user, mastery_score=90.0)

    service = _build_service(db_session, {node.id: status})

    # Error 1: concept_confusion -> -8  => 90 -> 82
    error1 = _make_error_record(
        db_session, seeded_user, linked_node_ids=[node.id], error_type="concept_confusion"
    )
    await db_session.commit()
    r1 = await service.apply_error_diagnosis(seeded_user.id, error1)
    assert r1[0]["new_mastery"] == 82
    await db_session.refresh(status)

    # Error 2: method_wrong -> -6  => 82 -> 76
    error2 = _make_error_record(
        db_session, seeded_user, linked_node_ids=[node.id], error_type="method_wrong"
    )
    await db_session.commit()
    r2 = await service.apply_error_diagnosis(seeded_user.id, error2)
    assert r2[0]["new_mastery"] == 76
    await db_session.refresh(status)

    # Review 1: remembered -> +4  => 76 -> 80
    rv1 = await service.apply_review_feedback(seeded_user.id, error1, "remembered")
    assert rv1[0]["new_mastery"] == 80
    await db_session.refresh(status)

    # Error 3: calculation_error -> -3  => 80 -> 77
    error3 = _make_error_record(
        db_session, seeded_user, linked_node_ids=[node.id], error_type="calculation_error"
    )
    await db_session.commit()
    r3 = await service.apply_error_diagnosis(seeded_user.id, error3)
    assert r3[0]["new_mastery"] == 77
    await db_session.refresh(status)

    # Review 2: fuzzy -> +1  => 77 -> 78
    rv2 = await service.apply_review_feedback(seeded_user.id, error2, "fuzzy")
    assert rv2[0]["new_mastery"] == 78

    # Final state: 90 - 8 - 6 + 4 - 3 + 1 = 78
    await db_session.refresh(status)
    assert status.mastery_score == 78.0

    # Should have 5 StudyRecords (3 diagnoses + 2 reviews)
    result = await db_session.execute(
        select(StudyRecord).where(
            StudyRecord.user_id == seeded_user.id,
            StudyRecord.node_id == node.id,
        )
    )
    records = result.scalars().all()
    assert len(records) == 5

    diagnosis_records = [r for r in records if r.record_type == "error_diagnosis"]
    review_records = [r for r in records if r.record_type == "error_review"]
    assert len(diagnosis_records) == 3
    assert len(review_records) == 2
