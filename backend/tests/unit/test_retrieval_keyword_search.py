import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.galaxy.retrieval_service import KnowledgeRetrievalService


@pytest.mark.asyncio
async def test_keyword_search_returns_list_on_empty_result():
    db = AsyncMock()
    mock_result = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars = MagicMock(return_value=mock_scalars)
    db.execute.return_value = mock_result

    service = KnowledgeRetrievalService(db)
    results = await service.keyword_search(
        user_id=uuid.uuid4(),
        query="test",
        limit=2
    )

    assert results == []
