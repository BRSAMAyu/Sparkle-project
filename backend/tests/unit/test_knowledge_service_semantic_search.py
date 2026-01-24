import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.knowledge_service import KnowledgeService, KnowledgeSearchHit


@pytest.mark.asyncio
async def test_semantic_search_returns_hits():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    node = SimpleNamespace(
        id=uuid.uuid4(),
        name="Test Node",
        description="Test description"
    )
    mock_result.all.return_value = [(node, 0.1)]
    mock_db.execute.return_value = mock_result

    service = KnowledgeService(mock_db)

    with patch(
        "app.services.knowledge_service.embedding_service.get_embedding",
        new_callable=AsyncMock
    ) as mock_embed:
        mock_embed.return_value = [0.1, 0.2]
        hits = await service.semantic_search(query="test query", top_k=3, min_similarity=0.3)

    assert len(hits) == 1
    assert isinstance(hits[0], KnowledgeSearchHit)
    assert hits[0].name == "Test Node"
    assert hits[0].similarity > 0.0
