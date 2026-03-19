from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.cognitive import BehaviorPattern
from app.services.dashboard_service import DashboardService


@pytest.mark.asyncio
async def test_get_cognitive_summary_filters_archived_patterns():
    db = AsyncMock()
    service = DashboardService(db)

    pattern = BehaviorPattern(
        id=uuid4(),
        user_id=uuid4(),
        pattern_name="Perfectionism Loop",
        pattern_type="cognitive",
        description="desc",
        solution_text="fix",
        confidence_score=0.91,
        frequency=2,
    )

    first_result = MagicMock()
    first_result.scalar_one_or_none.return_value = pattern
    second_result = MagicMock()
    second_result.scalar.return_value = 1

    seen_queries: list[str] = []

    async def execute_side_effect(query):
        seen_queries.append(str(query).lower())
        return [first_result, second_result][len(seen_queries) - 1]

    db.execute.side_effect = execute_side_effect

    summary = await service._get_cognitive_summary(pattern.user_id)

    assert summary["weekly_pattern"] == "Perfectionism Loop"
    assert summary["status"] == "new"
    assert len(seen_queries) == 2
    assert "is_archived is false" in seen_queries[0]
    assert "is_archived is false" in seen_queries[1]

