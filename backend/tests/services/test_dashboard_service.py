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
    assert summary["description"] == "desc"
    assert summary["solution_text"] == "fix"
    assert summary["status"] == "new"
    assert len(seen_queries) == 2
    assert "is_archived is false" in seen_queries[0]
    assert "is_archived is false" in seen_queries[1]


@pytest.mark.asyncio
async def test_get_cognitive_summary_localizes_known_patterns():
    db = AsyncMock()
    service = DashboardService(db)

    pattern = BehaviorPattern(
        id=uuid4(),
        user_id=uuid4(),
        pattern_name="The Night-Time Energy Mismatch Loop",
        pattern_type="cognitive",
        description="This is an English description that should not leak to users.",
        solution_text="Move hard work earlier in the day.",
        confidence_score=0.93,
        frequency=3,
    )

    first_result = MagicMock()
    first_result.scalar_one_or_none.return_value = pattern
    second_result = MagicMock()
    second_result.scalar.return_value = 0
    db.execute.side_effect = [first_result, second_result]

    summary = await service._get_cognitive_summary(pattern.user_id)

    assert summary["weekly_pattern"] == "夜间能量错配循环"
    assert "精力明显下滑" in summary["description"]
    assert "前移到你最清醒的两个小时" in summary["solution_text"]
    assert summary["status"] == "active"
