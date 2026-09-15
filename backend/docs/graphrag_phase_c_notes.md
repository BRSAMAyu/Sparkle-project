# GraphRAG Hardening Notes

## Feature flags
- `ENABLE_GRAPHRAG_FASTPATH=false` enables parallel GraphRAG retrieval + cache.
- `ENABLE_GRAPHRAG_MONITOR_API=false` enables `/monitor/graph` and `/graphrag` trace endpoints.
- `GRAPHRAG_CACHE_TTL_SECONDS=120` GraphRAG cache TTL (seconds).
- `GRAPHRAG_FASTPATH_TIMEOUT_SECONDS=2.5` GraphRAG fastpath timeout (seconds).
- `GRAPHRAG_TRACE_TTL_SECONDS=86400` Trace TTL (seconds).
- `GRAPHRAG_TRACE_MAX_BYTES=20000` Max serialized trace payload (bytes).
- `KNOWLEDGE_VERSION_CACHE_TTL_SECONDS=30` Knowledge version cache TTL (seconds).
- `FEEDBACK_EFFECT_TTL_SECONDS=604800` Feedback-to-effect TTL (seconds).

## Tests
```bash
cd backend
pytest tests/test_graph_rag.py tests/unit/test_knowledge_service_semantic_search.py -q
```

## Consumer outage simulation (self-heal + feedback metrics)
1) Stop `preference_event_consumer` (or block its stream access).
2) Update preferences via normal API (Go write path).
3) Send a chat request and verify:
   - Python logs contain a prefs self-heal entry.
   - The updated preference applies to the response.
4) Send response feedback (thumbs up/down) and confirm:
   - `sparkle_response_feedback_ingested_total` increments.
   - On the next chat request, `sparkle_feedback_to_effect_seconds` records a sample.

## Migration
Apply pgvector HNSW indexes:
```bash
cd backend
alembic upgrade head
```
