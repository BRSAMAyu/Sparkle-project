from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.persona_service import ProfileSnapshotService


@pytest.mark.asyncio
async def test_collect_tags_ignores_archived_patterns_in_query():
    db = AsyncMock()
    service = ProfileSnapshotService(db)
    user_id = uuid4()

    pattern_result = MagicMock()
    pattern_result.all.return_value = [("Perfectionism Loop",)]
    fragment_result = MagicMock()
    fragment_result.all.return_value = [(["deep_work", "reflection"],)]

    seen_queries: list[str] = []

    async def execute_side_effect(query):
        seen_queries.append(str(query).lower())
        return [pattern_result, fragment_result][len(seen_queries) - 1]

    db.execute.side_effect = execute_side_effect

    tags = await service._collect_tags(user_id)

    assert tags[:3] == ["Perfectionism Loop", "deep_work", "reflection"]
    assert "is_archived is false" in seen_queries[0]

