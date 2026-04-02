"""Tests for ErrorBookMasterySyncService — bridges error evidence to node mastery."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.error_book_mastery_sync_service import (
    ERROR_TYPE_IMPACT,
    MAX_SINGLE_ERROR_IMPACT,
    MAX_MASTERY_SCORE,
    MIN_MASTERY_SCORE,
    NODE_RANK_WEIGHTS,
    REVIEW_PERFORMANCE_IMPACT,
    ErrorBookMasterySyncService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_error_record(
    *,
    linked_node_ids: list | None = None,
    error_type: str = "concept_confusion",
    error_id=None,
):
    """Lightweight error record stand-in for unit tests."""
    return SimpleNamespace(
        id=error_id or uuid4(),
        linked_knowledge_node_ids=linked_node_ids or [],
        latest_analysis={"error_type": error_type},
    )


def _make_node_status(*, mastery_score: float = 50.0, study_count: int = 5):
    """Lightweight UserNodeStatus stand-in."""
    status = SimpleNamespace(
        mastery_score=mastery_score,
        study_count=study_count,
        last_study_at=None,
        next_review_at=None,
        is_unlocked=True,
        bkt_mastery_prob=max(0.0, min(float(mastery_score) / 100.0, 1.0)),
        bkt_last_updated_at=None,
        first_unlock_at=None,
    )
    return status


def _make_service(node_statuses: dict | None = None):
    """Create ErrorBookMasterySyncService with mocked DB and event_bus.

    node_statuses: dict mapping node_id (UUID) -> mastery_score (float)
    """
    db = MagicMock()
    redis = MagicMock()

    # Track statuses for mutation
    _statuses = {}

    if node_statuses:
        for nid, score in node_statuses.items():
            _statuses[nid] = _make_node_status(mastery_score=score)

    # Mock db.execute for _get_or_create_node_status
    async def _mock_execute(stmt):
        result_mock = MagicMock()

        # Extract node_id from the where clause (simple approach)
        # We check our tracked statuses
        # The service queries UserNodeStatus by (user_id, node_id)
        # For simplicity, we return based on _statuses dict

        # Mock scalar_one_or_none
        found = None
        # If _statuses has entries, return the first one for simplicity
        # The actual test will validate logic per-node via finer mocking
        result_mock.scalar_one_or_none = MagicMock(return_value=None)
        return result_mock

    db.execute = AsyncMock(side_effect=_mock_execute)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    with patch("app.services.error_book_mastery_sync_service.GalaxyStatsService"):
        service = ErrorBookMasterySyncService(db, redis)

    # Override _get_or_create_node_status for controlled testing
    if node_statuses is not None:
        original_get_or_create = service._get_or_create_node_status

        async def _mock_get_or_create(user_id, node_id, create_if_missing=True):
            if node_id in _statuses:
                return _statuses[node_id]
            if not create_if_missing:
                return None
            # Simulate creating a new status
            new_status = _make_node_status(mastery_score=0)
            new_status.is_unlocked = False
            _statuses[node_id] = new_status
            return new_status

        service._get_or_create_node_status = _mock_get_or_create

    return service, db, _statuses


# ===========================================================================
# 1. No linked nodes → no updates
# ===========================================================================

@pytest.mark.asyncio
async def test_diagnosis_no_linked_nodes_returns_empty():
    service, _, _ = _make_service()
    error = _make_error_record(linked_node_ids=[])

    results = await service.apply_error_diagnosis(uuid4(), error)
    assert results == []


@pytest.mark.asyncio
async def test_diagnosis_none_linked_nodes_returns_empty():
    service, _, _ = _make_service()
    error = _make_error_record(linked_node_ids=None)
    error.linked_knowledge_node_ids = None

    results = await service.apply_error_diagnosis(uuid4(), error)
    assert results == []


@pytest.mark.asyncio
async def test_review_no_linked_nodes_returns_empty():
    service, _, _ = _make_service()
    error = _make_error_record(linked_node_ids=[])

    results = await service.apply_review_feedback(uuid4(), error, "remembered")
    assert results == []


# ===========================================================================
# 2. Single node concept_confusion → mastery decreases by -8
# ===========================================================================

@pytest.mark.asyncio
async def test_diagnosis_single_node_concept_confusion():
    node_id = uuid4()

    service, db, _ = _make_service(node_statuses={node_id: 55.0})
    error = _make_error_record(
        linked_node_ids=[node_id],
        error_type="concept_confusion",
    )

    results = await service.apply_error_diagnosis(uuid4(), error)

    assert len(results) == 1
    assert results[0]["old_mastery"] == 55
    assert results[0]["new_mastery"] == 47  # 55 - 8
    assert results[0]["delta"] == -8
    assert results[0]["record_type"] == "error_diagnosis"
    assert db.add.called  # StudyRecord written


# ===========================================================================
# 3. Multi-node knowledge_gap → decaying weights
# ===========================================================================

@pytest.mark.asyncio
async def test_diagnosis_multi_node_decay():
    n1, n2, n3 = uuid4(), uuid4(), uuid4()

    service, db, _ = _make_service(node_statuses={
        n1: 60.0,
        n2: 50.0,
        n3: 40.0,
    })
    error = _make_error_record(
        linked_node_ids=[n1, n2, n3],
        error_type="knowledge_gap",  # base -10
    )

    results = await service.apply_error_diagnosis(uuid4(), error)

    assert len(results) == 3
    # Node 1: 100% weight → -10 * 1.0 = -10 → 60 → 50
    assert results[0]["delta"] == -10
    assert results[0]["new_mastery"] == 50
    # Node 2: 60% weight → -10 * 0.6 = -6 → 50 → 44
    assert results[1]["delta"] == -6
    assert results[1]["new_mastery"] == 44
    # Node 3: 30% weight → -10 * 0.3 = -3 → 40 → 37
    assert results[2]["delta"] == -3
    assert results[2]["new_mastery"] == 37


@pytest.mark.asyncio
async def test_diagnosis_caps_at_3_nodes():
    """More than 3 linked nodes should only process first 3."""
    nodes = [uuid4() for _ in range(5)]

    statuses = {nid: 50.0 for nid in nodes}
    service, _, _ = _make_service(node_statuses=statuses)
    error = _make_error_record(
        linked_node_ids=nodes,
        error_type="concept_confusion",
    )

    results = await service.apply_error_diagnosis(uuid4(), error)
    assert len(results) == 3


# ===========================================================================
# 4. Review remembered → mastery increases
# ===========================================================================

@pytest.mark.asyncio
async def test_review_remembered_increases_mastery():
    node_id = uuid4()
    service, _, statuses = _make_service(node_statuses={node_id: 47.0})
    error = _make_error_record(linked_node_ids=[node_id])

    results = await service.apply_review_feedback(uuid4(), error, "remembered")

    assert len(results) == 1
    assert results[0]["delta"] == 4
    assert results[0]["new_mastery"] == 51
    assert results[0]["record_type"] == "error_review"


# ===========================================================================
# 5. Review fuzzy → mastery slight increase
# ===========================================================================

@pytest.mark.asyncio
async def test_review_fuzzy_slight_increase():
    node_id = uuid4()
    service, _, _ = _make_service(node_statuses={node_id: 47.0})
    error = _make_error_record(linked_node_ids=[node_id])

    results = await service.apply_review_feedback(uuid4(), error, "fuzzy")

    assert len(results) == 1
    assert results[0]["delta"] == 1
    assert results[0]["new_mastery"] == 48


# ===========================================================================
# 6. Review forgot → mastery decreases
# ===========================================================================

@pytest.mark.asyncio
async def test_review_forgot_decreases_mastery():
    node_id = uuid4()
    service, _, _ = _make_service(node_statuses={node_id: 47.0})
    error = _make_error_record(linked_node_ids=[node_id])

    results = await service.apply_review_feedback(uuid4(), error, "forgot")

    assert len(results) == 1
    assert results[0]["delta"] == -2
    assert results[0]["new_mastery"] == 45


@pytest.mark.asyncio
async def test_review_unknown_performance_returns_empty():
    node_id = uuid4()
    service, _, _ = _make_service(node_statuses={node_id: 50.0})
    error = _make_error_record(linked_node_ids=[node_id])

    results = await service.apply_review_feedback(uuid4(), error, "unknown_perf")
    assert results == []


# ===========================================================================
# 7. Mastery floor at 0
# ===========================================================================

@pytest.mark.asyncio
async def test_mastery_does_not_go_below_zero():
    node_id = uuid4()
    service, _, _ = _make_service(node_statuses={node_id: 2.0})
    error = _make_error_record(
        linked_node_ids=[node_id],
        error_type="knowledge_gap",  # -10
    )

    results = await service.apply_error_diagnosis(uuid4(), error)

    assert len(results) == 1
    assert results[0]["new_mastery"] == 0  # Clamped from -8


@pytest.mark.asyncio
async def test_mastery_already_zero_diagnosis_no_result():
    """If mastery is 0 and delta is negative, clamped result equals 0 → no update."""
    node_id = uuid4()
    service, _, _ = _make_service(node_statuses={node_id: 0.0})
    error = _make_error_record(
        linked_node_ids=[node_id],
        error_type="calculation_error",  # -3
    )

    results = await service.apply_error_diagnosis(uuid4(), error)
    assert results == []


# ===========================================================================
# 8. Mastery ceiling at 100
# ===========================================================================

@pytest.mark.asyncio
async def test_mastery_does_not_exceed_100():
    node_id = uuid4()
    service, _, _ = _make_service(node_statuses={node_id: 98.0})
    error = _make_error_record(linked_node_ids=[node_id])

    results = await service.apply_review_feedback(uuid4(), error, "remembered")

    assert len(results) == 1
    assert results[0]["new_mastery"] == 100  # Clamped from 102


# ===========================================================================
# 9. Event publishing
# ===========================================================================

@pytest.mark.asyncio
async def test_diagnosis_defers_node_mastery_updated_event():
    """Events are deferred via _pending_event, not published inline (fix #1)."""
    node_id = uuid4()
    service, _, _ = _make_service(node_statuses={node_id: 50.0})
    error = _make_error_record(
        linked_node_ids=[node_id],
        error_type="concept_confusion",
    )

    results = await service.apply_error_diagnosis(uuid4(), error)

    assert len(results) == 1
    assert "_pending_event" in results[0]
    assert results[0]["_pending_event"]["topic"] == "node_mastery_updated"
    payload = results[0]["_pending_event"]["payload"]
    assert payload["old_mastery"] == 50
    assert payload["new_mastery"] == 42


@pytest.mark.asyncio
async def test_review_defers_node_mastery_updated_event():
    """Events are deferred via _pending_event, not published inline (fix #1)."""
    node_id = uuid4()
    service, _, _ = _make_service(node_statuses={node_id: 47.0})
    error = _make_error_record(linked_node_ids=[node_id])

    results = await service.apply_review_feedback(uuid4(), error, "remembered")

    assert len(results) == 1
    assert "_pending_event" in results[0]
    assert results[0]["_pending_event"]["topic"] == "node_mastery_updated"


@pytest.mark.asyncio
async def test_deferred_event_survives_publish_failure():
    """With deferred events, the sync itself never crashes even if publish later fails."""
    node_id = uuid4()
    service, _, _ = _make_service(node_statuses={node_id: 50.0})
    error = _make_error_record(linked_node_ids=[node_id])

    # Event is deferred, not published inline — so Redis failure is irrelevant here
    results = await service.apply_review_feedback(uuid4(), error, "remembered")
    assert len(results) == 1
    assert "_pending_event" in results[0]

    # Simulating later publish failure at the caller side would not affect this result
    # The caller catches the exception when flushing pending events


# ===========================================================================
# 10. StudyRecord written
# ===========================================================================

@pytest.mark.asyncio
async def test_diagnosis_writes_study_record():
    node_id = uuid4()
    service, db, _ = _make_service(node_statuses={node_id: 55.0})
    error = _make_error_record(
        linked_node_ids=[node_id],
        error_type="concept_confusion",
    )

    await service.apply_error_diagnosis(uuid4(), error)

    # db.add should have been called with a StudyRecord-like object
    assert db.add.called
    added_obj = db.add.call_args[0][0]
    # Verify it's a StudyRecord by checking attributes
    assert hasattr(added_obj, "record_type")
    assert added_obj.record_type == "error_diagnosis"
    assert added_obj.mastery_delta == -8.0
    assert added_obj.initial_mastery == 55.0


@pytest.mark.asyncio
async def test_review_writes_study_record():
    node_id = uuid4()
    service, db, _ = _make_service(node_statuses={node_id: 47.0})
    error = _make_error_record(linked_node_ids=[node_id])

    await service.apply_review_feedback(uuid4(), error, "remembered")

    assert db.add.called
    added_obj = db.add.call_args[0][0]
    assert added_obj.record_type == "error_review"
    assert added_obj.mastery_delta == 4.0


# ===========================================================================
# 11. study_count increments
# ===========================================================================

@pytest.mark.asyncio
async def test_diagnosis_increments_study_count():
    node_id = uuid4()
    service, _, statuses = _make_service(node_statuses={node_id: 50.0})
    error = _make_error_record(
        linked_node_ids=[node_id],
        error_type="concept_confusion",
    )

    await service.apply_error_diagnosis(uuid4(), error)

    assert statuses[node_id].study_count == 6  # Started at 5, +1


# ===========================================================================
# 12. get_or_create for new node
# ===========================================================================

@pytest.mark.asyncio
async def test_diagnosis_creates_status_for_new_node():
    node_id = uuid4()
    service, _, statuses = _make_service(node_statuses={})  # No existing statuses
    error = _make_error_record(
        linked_node_ids=[node_id],
        error_type="concept_confusion",
    )

    results = await service.apply_error_diagnosis(uuid4(), error)

    # New node starts at 0, -8 clamped to 0 → no change → no result
    # This is correct behavior: you can't go below 0
    assert results == []
    assert node_id not in statuses  # no zero-evidence node should be materialized


@pytest.mark.asyncio
async def test_diagnosis_creates_status_positive_node():
    """If a new node is created and the delta is negative, it stays at 0 (no update).
    But if the delta were somehow positive (review), it would work."""
    node_id = uuid4()
    service, _, _ = _make_service(node_statuses={})
    error = _make_error_record(linked_node_ids=[node_id])

    # Review with "remembered" on a new node (starts at 0) → 0 + 4 = 4
    results = await service.apply_review_feedback(uuid4(), error, "remembered")

    assert len(results) == 1
    assert results[0]["old_mastery"] == 0
    assert results[0]["new_mastery"] == 4


@pytest.mark.asyncio
async def test_mastery_update_refreshes_bkt_and_review_fields():
    node_id = uuid4()
    service, _, statuses = _make_service(node_statuses={node_id: 47.0})
    error = _make_error_record(linked_node_ids=[node_id], error_type="concept_confusion")

    results = await service.apply_error_diagnosis(uuid4(), error)

    assert len(results) == 1
    status = statuses[node_id]
    assert status.bkt_mastery_prob == pytest.approx(0.39)
    assert status.bkt_last_updated_at is not None
    assert status.next_review_at is not None
    assert status.last_study_at is not None


@pytest.mark.asyncio
async def test_positive_new_node_unlocks_on_first_real_evidence():
    node_id = uuid4()
    service, _, statuses = _make_service(node_statuses={})
    error = _make_error_record(linked_node_ids=[node_id])

    await service.apply_review_feedback(uuid4(), error, "remembered")

    assert statuses[node_id].is_unlocked is True
    assert statuses[node_id].first_unlock_at is not None


# ===========================================================================
# 13. Combined diagnosis → review flow
# ===========================================================================

@pytest.mark.asyncio
async def test_combined_diagnosis_then_review_flow():
    """Full flow: diagnosis reduces mastery, then review recovers it."""
    node_id = uuid4()
    user_id = uuid4()

    service, _, statuses = _make_service(node_statuses={node_id: 55.0})
    error = _make_error_record(
        linked_node_ids=[node_id],
        error_type="concept_confusion",
    )

    # Step 1: Diagnosis → -8
    diag_results = await service.apply_error_diagnosis(user_id, error)
    assert len(diag_results) == 1
    assert diag_results[0]["new_mastery"] == 47

    # Step 2: Review (remembered) → +4
    review_results = await service.apply_review_feedback(user_id, error, "remembered")
    assert len(review_results) == 1
    assert review_results[0]["old_mastery"] == 47
    assert review_results[0]["new_mastery"] == 51


# ===========================================================================
# 14. All error types produce correct deltas
# ===========================================================================

@pytest.mark.asyncio
async def test_all_error_type_deltas():
    """Verify each error_type produces the expected delta on a single node."""
    expected = {
        "concept_confusion": -8,
        "knowledge_gap": -10,
        "method_wrong": -6,
        "logic_error": -5,
        "calculation_error": -3,
        "reading_careless": -2,
        "other": -3,
    }

    for error_type, expected_delta in expected.items():
        node_id = uuid4()
        service, _, _ = _make_service(node_statuses={node_id: 50.0})
        error = _make_error_record(
            linked_node_ids=[node_id],
            error_type=error_type,
        )

        results = await service.apply_error_diagnosis(uuid4(), error)
        assert len(results) == 1, f"Failed for {error_type}"
        assert results[0]["delta"] == expected_delta, (
            f"{error_type}: expected {expected_delta}, got {results[0]['delta']}"
        )


# ===========================================================================
# 15. _extract_error_type edge cases
# ===========================================================================

@pytest.mark.asyncio
async def test_extract_error_type_fallback_to_other():
    service, _, _ = _make_service()

    # No latest_analysis
    error = SimpleNamespace(id=uuid4(), linked_knowledge_node_ids=[], latest_analysis=None)
    assert service._extract_error_type(error) == "other"

    # latest_analysis is not a dict
    error2 = SimpleNamespace(id=uuid4(), linked_knowledge_node_ids=[], latest_analysis="string")
    assert service._extract_error_type(error2) == "other"

    # latest_analysis missing error_type key
    error3 = SimpleNamespace(id=uuid4(), linked_knowledge_node_ids=[], latest_analysis={})
    assert service._extract_error_type(error3) == "other"


# ===========================================================================
# 16. Clamp functions
# ===========================================================================

def test_clamp_impact_within_range():
    assert ErrorBookMasterySyncService._clamp_impact(-5) == -5
    assert ErrorBookMasterySyncService._clamp_impact(5) == 5


def test_clamp_impact_at_boundary():
    assert ErrorBookMasterySyncService._clamp_impact(-10) == -10
    assert ErrorBookMasterySyncService._clamp_impact(10) == 10


def test_clamp_impact_exceeds():
    assert ErrorBookMasterySyncService._clamp_impact(-15) == -10
    assert ErrorBookMasterySyncService._clamp_impact(15) == 10


def test_clamp_mastery():
    assert ErrorBookMasterySyncService._clamp_mastery(50) == 50
    assert ErrorBookMasterySyncService._clamp_mastery(-1) == 0
    assert ErrorBookMasterySyncService._clamp_mastery(101) == 100


# ===========================================================================
# 17. _get_or_create_node_status failure handling
# ===========================================================================

@pytest.mark.asyncio
async def test_get_or_create_failure_returns_empty_results():
    """If _get_or_create_node_status fails, no results returned."""
    node_id = uuid4()
    service, _, _ = _make_service(node_statuses={node_id: 50.0})

    # Override to simulate failure
    service._get_or_create_node_status = AsyncMock(return_value=None)

    error = _make_error_record(linked_node_ids=[node_id])
    results = await service.apply_error_diagnosis(uuid4(), error)
    assert results == []


# ===========================================================================
# 18. Constants match implementation doc
# ===========================================================================

def test_error_type_impact_matches_spec():
    """Verify constants match the implementation doc §5.2."""
    assert ERROR_TYPE_IMPACT == {
        "concept_confusion": -8,
        "knowledge_gap": -10,
        "method_wrong": -6,
        "logic_error": -5,
        "calculation_error": -3,
        "reading_careless": -2,
        "other": -3,
    }


def test_review_performance_impact_matches_spec():
    """Verify review constants match the implementation doc §5.4."""
    assert REVIEW_PERFORMANCE_IMPACT == {
        "remembered": 4,
        "fuzzy": 1,
        "forgot": -2,
    }


def test_node_rank_weights_match_spec():
    """Verify decay weights match the implementation doc §5.3."""
    assert NODE_RANK_WEIGHTS == [1.0, 0.6, 0.3]


def test_safety_limits():
    assert MAX_SINGLE_ERROR_IMPACT == 10
    assert MIN_MASTERY_SCORE == 0
    assert MAX_MASTERY_SCORE == 100
