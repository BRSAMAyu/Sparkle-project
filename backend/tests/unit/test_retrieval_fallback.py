import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.embedding_service import embedding_service
from app.core.redis_search_client import redis_search_client


@pytest.mark.asyncio
async def test_hybrid_search_fallback_on_timeout(monkeypatch):
    db = AsyncMock()
    service = KnowledgeRetrievalService(db)
    monkeypatch.setattr(settings, "ENABLE_REDIS_HYBRID_FALLBACK", True)
    monkeypatch.setattr(embedding_service, "get_embedding", AsyncMock(return_value=[0.1, 0.2]))

    monkeypatch.setattr(redis_search_client, "hybrid_search", AsyncMock(side_effect=asyncio.TimeoutError()))
    monkeypatch.setattr(redis_search_client, "search", AsyncMock(side_effect=asyncio.TimeoutError()))

    fallback_result = ["fallback"]
    monkeypatch.setattr(service, "_pgvector_fallback", AsyncMock(return_value=fallback_result))

    results = await service._execute_hybrid_search(
        user_id_uuid=uuid.uuid4(),
        query_str="test query",
        limit=2,
        threshold=0.3,
        use_reranker=False,
    )

    assert results == fallback_result


@pytest.mark.asyncio
async def test_pgvector_fallback_uses_keyword_search_when_vectors_empty(monkeypatch):
    db = AsyncMock()
    service = KnowledgeRetrievalService(db)

    monkeypatch.setattr(service, "semantic_search_nodes", AsyncMock(return_value=[]))
    monkeypatch.setattr(service, "keyword_search", AsyncMock(return_value=["keyword-node"]))
    monkeypatch.setattr(service, "_build_results_from_nodes", AsyncMock(return_value=["keyword-result"]))

    results = await service._pgvector_fallback(
        user_id_uuid=uuid.uuid4(),
        query_str="test query",
        subject_id=None,
        limit=2,
        threshold=0.3,
        use_reranker=False,
    )

    assert results == ["keyword-result"]
