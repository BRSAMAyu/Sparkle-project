from datetime import timezone, datetime

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


from app.config import settings
from app.orchestration.graph_rag import RetrievalTrace
from app.services.graphrag_trace_store import _serialize_trace


def test_trace_store_redacts_query_when_pii_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_GRAPHRAG_TRACE_PII", False)

    trace = RetrievalTrace(
        trace_id="trace-1",
        query="Contact me at test@example.com or +1 555-123-4567",
        timestamp=_utcnow(),
        nodes_retrieved=[],
        node_sources={},
        relationships=[],
        vector_search_results=[],
        graph_search_results=[],
        user_interest_nodes=[],
        timing={},
    )

    payload = _serialize_trace(trace)

    assert "query" not in payload
    assert "query_redacted" in payload
    assert "test@example.com" not in payload["query_redacted"]
    assert "555" not in payload["query_redacted"]
    assert payload["query_hash"]
