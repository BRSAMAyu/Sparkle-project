from unittest.mock import AsyncMock

from app.orchestration.graph_rag import GraphRAGRetriever


def test_cache_key_changes_with_knowledge_version():
    retriever = GraphRAGRetriever(AsyncMock())

    key_v1 = retriever._build_cache_key("test query", "user-1", knowledge_version="kv1")
    key_v2 = retriever._build_cache_key("test query", "user-1", knowledge_version="kv2")

    assert key_v1 != key_v2
