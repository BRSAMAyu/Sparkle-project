"""Regression test for ISSUE-20260504-1801-B2.

Verifies that PUT /experience/goal-detail/{goal_id}/criteria-status
persists the confirmation status to the Goal model.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest


def _goal_mock(goal_id, user_id, criteria):
    g = AsyncMock()
    g.id = goal_id
    g.user_id = user_id
    g.minimum_acceptance_criteria = criteria
    return g


def _db_with_goal(goal):
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = lambda: goal
    db = AsyncMock()

    async def _fake_execute(*args, **kwargs):
        return mock_result

    db.execute = _fake_execute
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_update_criteria_status_confirms():
    """B2 fix: PUT endpoint persists criteria status to Goal model."""
    from app.api.v1.experience.goal_router import update_criteria_status, CriteriaStatusPayload

    goal_id = uuid4()
    user_id = uuid4()

    criteria = {
        "description": "Score 85% on the exam",
        "status": "pending_confirmation",
        "thresholds": [],
    }
    goal = _goal_mock(goal_id, user_id, criteria)
    db = _db_with_goal(goal)

    result = await update_criteria_status(
        payload=CriteriaStatusPayload(status="confirmed"),
        goal_id=goal_id,
        db=db,
        current_user=AsyncMock(id=user_id),
    )

    assert result == {"status": "ok", "criteria_status": "confirmed"}
    assert goal.minimum_acceptance_criteria["status"] == "confirmed"


@pytest.mark.asyncio
async def test_update_criteria_status_undo():
    """B2 fix: PUT endpoint reverts to pending_confirmation."""
    from app.api.v1.experience.goal_router import update_criteria_status, CriteriaStatusPayload

    goal_id = uuid4()
    user_id = uuid4()

    criteria = {
        "description": "Score 85%",
        "status": "confirmed",
        "thresholds": [{"label": "Mock exam"}],
    }
    goal = _goal_mock(goal_id, user_id, criteria)
    db = _db_with_goal(goal)

    result = await update_criteria_status(
        payload=CriteriaStatusPayload(status="pending_confirmation"),
        goal_id=goal_id,
        db=db,
        current_user=AsyncMock(id=user_id),
    )

    assert result["criteria_status"] == "pending_confirmation"
    assert goal.minimum_acceptance_criteria["status"] == "pending_confirmation"


@pytest.mark.asyncio
async def test_update_criteria_status_rejects_invalid():
    """B2 fix: endpoint rejects invalid status values."""
    from app.api.v1.experience.goal_router import update_criteria_status, CriteriaStatusPayload
    from fastapi import HTTPException

    goal_id = uuid4()
    user_id = uuid4()
    goal = _goal_mock(goal_id, user_id, {"status": "pending_confirmation"})
    db = _db_with_goal(goal)

    with pytest.raises(HTTPException) as exc_info:
        await update_criteria_status(
            payload=CriteriaStatusPayload(status="invalid_status"),
            goal_id=goal_id,
            db=db,
            current_user=AsyncMock(id=user_id),
        )
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_update_criteria_status_404_for_missing_goal():
    """B2 fix: endpoint returns 404 when goal does not exist."""
    from app.api.v1.experience.goal_router import update_criteria_status, CriteriaStatusPayload
    from fastapi import HTTPException

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = lambda: None
    db = AsyncMock()

    async def _fake_execute(*args, **kwargs):
        return mock_result

    db.execute = _fake_execute

    with pytest.raises(HTTPException) as exc_info:
        await update_criteria_status(
            payload=CriteriaStatusPayload(status="confirmed"),
            goal_id=uuid4(),
            db=db,
            current_user=AsyncMock(),
        )
    assert exc_info.value.status_code == 404
