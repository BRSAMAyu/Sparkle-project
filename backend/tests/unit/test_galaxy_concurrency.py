"""
Test Galaxy Service concurrent mastery update (C1 fix verification)
Tests atomic UPDATE with optimistic locking prevents race conditions
"""
import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from app.db.session import AsyncSessionLocal, engine
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.user import User
from app.services.galaxy_service import GalaxyService


async def _seed_user_node_status(db, *, user_id: UUID, node_id: UUID, mastery_score: float, revision: int) -> None:
    user = User(
        id=user_id,
        username=f"concurrency_{user_id.hex[:12]}",
        email=f"{user_id.hex[:12]}@example.com",
        hashed_password="hashed",
    )
    node = KnowledgeNode(
        id=node_id,
        name=f"并发测试节点-{node_id.hex[:8]}",
        description="用于验证知识星图掌握度并发更新。",
        importance_level=1,
        source_type="user_created",
        dominant_sector_code="VOID",
        sector_classification_status="pending",
    )
    status = UserNodeStatus(
        user_id=user_id,
        node_id=node_id,
        mastery_score=mastery_score,
        bkt_mastery_prob=max(0.0, min(float(mastery_score) / 100.0, 1.0)),
        revision=revision,
        is_unlocked=True,
    )
    db.add_all([user, node, status])
    await db.commit()


@pytest.mark.asyncio
async def test_concurrent_mastery_update_with_revision():
    """
    C1 Fix Verification: Concurrent updates with same revision should result in only one success.
    This tests the atomic UPDATE with WHERE revision = expected_revision.
    """
    user_id = uuid4()
    node_id = uuid4()
    await engine.dispose()

    # Create initial node status
    async with AsyncSessionLocal() as db:
        await _seed_user_node_status(db, user_id=user_id, node_id=node_id, mastery_score=50, revision=1)

    # Simulate two concurrent updates with the same expected revision (1)
    async def update_mastery(new_score: int):
        async with AsyncSessionLocal() as db:
            service = GalaxyService(db)
            return await service.update_node_mastery(
                user_id=user_id,
                node_id=node_id,
                new_mastery=new_score,
                reason="test",
                revision=1  # Both expect revision=1
            )

    # Run both updates concurrently
    results = await asyncio.gather(
        update_mastery(60),
        update_mastery(70),
        return_exceptions=True
    )

    # Analyze results
    success_count = 0
    conflict_count = 0
    for r in results:
        if isinstance(r, dict):
            if r.get("success"):
                success_count += 1
            elif r.get("reason") == "conflict":
                conflict_count += 1

    # Assertions
    assert success_count == 1, f"Expected exactly 1 success, got {success_count}"
    assert conflict_count == 1, f"Expected exactly 1 conflict, got {conflict_count}"

    # Verify final state in database
    async with AsyncSessionLocal() as db:
        verify_query = text("""
            SELECT mastery_score, revision FROM user_node_status
            WHERE user_id = :user_id AND node_id = :node_id
        """)
        result = await db.execute(verify_query, {"user_id": user_id, "node_id": node_id})
        row = result.fetchone()

        assert row is not None, "Record should exist"
        mastery, revision = row
        # One of the two values (60 or 70) should have won
        assert mastery in (60, 70), f"Expected mastery to be 60 or 70, got {mastery}"
        # Revision should have incremented once
        assert revision == 2, f"Expected revision to be 2, got {revision}"


@pytest.mark.asyncio
async def test_sequential_mastery_update_with_revision():
    """
    C1 Fix Verification: Sequential updates with incrementing revisions should all succeed.
    """
    user_id = uuid4()
    node_id = uuid4()
    await engine.dispose()

    async with AsyncSessionLocal() as db:
        await _seed_user_node_status(db, user_id=user_id, node_id=node_id, mastery_score=40, revision=1)

    # Sequential updates with correct revision numbers
    for expected_rev, new_score in [(1, 50), (2, 60), (3, 70)]:
        async with AsyncSessionLocal() as db:
            service = GalaxyService(db)
            result = await service.update_node_mastery(
                user_id=user_id,
                node_id=node_id,
                new_mastery=new_score,
                reason="test",
                revision=expected_rev
            )
            assert result.get("success"), f"Update with revision {expected_rev} should succeed"

    # Verify final state
    async with AsyncSessionLocal() as db:
        verify_query = text("""
            SELECT mastery_score, revision FROM user_node_status
            WHERE user_id = :user_id AND node_id = :node_id
        """)
        result = await db.execute(verify_query, {"user_id": user_id, "node_id": node_id})
        row = result.fetchone()

        assert row is not None, "Record should exist"
        mastery, revision = row
        assert mastery == 70, f"Expected mastery to be 70, got {mastery}"
        assert revision == 4, f"Expected revision to be 4, got {revision}"


@pytest.mark.asyncio
async def test_stale_revision_rejected():
    """
    C1 Fix Verification: Update with stale revision should be rejected.
    """
    user_id = uuid4()
    node_id = uuid4()
    await engine.dispose()

    async with AsyncSessionLocal() as db:
        await _seed_user_node_status(db, user_id=user_id, node_id=node_id, mastery_score=80, revision=5)

    # Try to update with stale revision=3
    async with AsyncSessionLocal() as db:
        service = GalaxyService(db)
        result = await service.update_node_mastery(
            user_id=user_id,
            node_id=node_id,
            new_mastery=90,
            reason="test",
            revision=3  # Stale revision
        )

    assert result.get("success") is False, "Stale update should fail"
    assert result.get("reason") == "conflict", "Should return conflict reason"
    assert result.get("current_revision") == 5, "Should return current revision"

    # Verify record was not modified
    async with AsyncSessionLocal() as db:
        verify_query = text("""
            SELECT mastery_score, revision FROM user_node_status
            WHERE user_id = :user_id AND node_id = :node_id
        """)
        result = await db.execute(verify_query, {"user_id": user_id, "node_id": node_id})
        row = result.fetchone()

        assert row is not None
        mastery, revision = row
        assert mastery == 80, "Mastery should not change"
        assert revision == 5, "Revision should not change"
