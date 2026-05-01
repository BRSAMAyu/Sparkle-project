from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.orchestration.graph_rag import GraphRAGRetriever


def test_bm25_query_uses_or_terms_and_fuzzy_matching():
    retriever = GraphRAGRetriever(AsyncMock())

    query = retriever._build_bm25_query("Dijkstra shortest path")

    assert "@content:" in query
    assert "dijkstra|%dijkstra%" in query
    assert "shortest|%shortest%" in query
    assert "path|%path%" in query


def test_rrf_fusion_merges_dense_and_bm25_sources():
    retriever = GraphRAGRetriever(AsyncMock())

    fused = retriever._rrf_fuse(
        [
            [{"id": "chunk-1", "retrieval_sources": ["dense"], "description": "semantic hit"}],
            [{"id": "chunk-1", "retrieval_sources": ["bm25"], "description": "lexical hit"}],
        ],
        top_k=1,
    )

    assert len(fused) == 1
    assert fused[0]["id"] == "chunk-1"
    assert fused[0]["retrieval_sources"] == ["bm25", "dense"]
    assert fused[0]["rrf_score"] > 0
    assert 0.0 < fused[0]["similarity"] <= 1.0


def test_group_document_requires_matching_group_scope():
    retriever = GraphRAGRetriever(AsyncMock())
    doc = SimpleNamespace(source_type="document_chunk", group_id="group-1", user_id="owner-1")

    assert retriever._redis_doc_matches_user(doc, "member-1", {"group-1"}) is True
    assert retriever._redis_doc_matches_user(doc, "member-1", {"group-2"}) is False


@pytest.mark.asyncio
async def test_vector_search_returns_bm25_hits_when_embedding_fails(monkeypatch):
    retriever = GraphRAGRetriever(AsyncMock())
    retriever.knowledge_service.semantic_search = AsyncMock(return_value=[])

    doc = SimpleNamespace(
        id="sparkle:chunk:node-1:0",
        parent_id="node-1",
        parent_name="Shortest Path Algorithms",
        content="The SSSP algorithm by Dijkstra relaxes edges greedily.",
    )

    monkeypatch.setattr(
        "app.orchestration.graph_rag.embedding_service.get_embedding",
        AsyncMock(side_effect=RuntimeError("embedding provider down")),
    )
    monkeypatch.setattr(
        "app.orchestration.graph_rag.redis_search_client.search",
        AsyncMock(return_value=SimpleNamespace(docs=[doc])),
    )

    results = await retriever.vector_search("Dijkstra shortest path", top_k=1)

    assert len(results) == 1
    assert results[0]["id"] == "sparkle:chunk:node-1:0"
    assert results[0]["parent_id"] == "node-1"
    assert results[0]["retrieval_sources"] == ["bm25"]
    assert "Dijkstra" in results[0]["description"]
    retriever.knowledge_service.semantic_search.assert_not_called()
