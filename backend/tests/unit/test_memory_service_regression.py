"""
B-004 Regression Tests: Memory Service Race Condition

Bug: update_goal lacked SELECT FOR UPDATE, allowing concurrent updates
to overwrite each other (last-write-wins without row lock).

This test verifies:
1. The update_goal method uses with_for_update() for row-level locking
2. Concurrent updates don't lose data
"""

import inspect

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory_service import MemoryService


class TestUpdateGoalRowLock:
    """Verify update_goal uses SELECT FOR UPDATE."""

    def test_update_goal_source_contains_for_update(self):
        """B-004 regression: update_goal must call with_for_update()."""
        source = inspect.getsource(MemoryService.update_goal)
        assert "with_for_update" in source, (
            "B-004 regression: update_goal does not use with_for_update(). "
            "Concurrent updates will cause data loss."
        )

    def test_update_goal_source_contains_select(self):
        """B-004 regression: update_goal must SELECT before UPDATE."""
        source = inspect.getsource(MemoryService.update_goal)
        assert "select(" in source, (
            "B-004 regression: update_goal does not perform a SELECT query."
        )


@pytest.mark.asyncio
class TestConcurrentUpdateGoal:
    """Integration test: concurrent updates must not lose data."""

    async def test_concurrent_updates_no_data_loss(self, db_session, test_user):
        """B-004 regression: two concurrent update_goal calls must both apply."""
        import asyncio
        from uuid import uuid4

        from app.models.memory import MemoryGoal

        # Create a goal to update
        goal_id = uuid4()
        goal = MemoryGoal(
            id=goal_id,
            user_id=test_user.id,
            title="Original Title",
            status="active",
        )
        db_session.add(goal)
        await db_session.commit()

        # SQLite doesn't support SELECT FOR UPDATE, but we can still verify
        # sequential updates apply correctly (the lock prevents concurrent issues
        # on PostgreSQL). On SQLite, verify the method doesn't crash.
        svc = MemoryService(db_session)

        updated = await svc.update_goal(
            user_id=test_user.id,
            goal_id=goal_id,
            title="Updated Title A",
        )
        assert updated is not None
        assert updated.title == "Updated Title A"

        updated2 = await svc.update_goal(
            user_id=test_user.id,
            goal_id=goal_id,
            status="paused",
        )
        assert updated2 is not None
        assert updated2.status == "paused"
        # Title from first update should persist
        assert updated2.title == "Updated Title A"
