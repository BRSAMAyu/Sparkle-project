# Knowledge Galaxy Python Backend Audit Report

**Date**: 2026-05-10
**Auditor**: Automated Code Review
**Scope**: Galaxy services, RAG pipeline, event consumers, data models, API routes, gRPC service

---

## Executive Summary

The audit reviewed 25+ files across the Galaxy Python backend. **41 issues** were identified across 10 categories: 2 P0 (data loss/security), 8 P1 (broken features), 16 P2 (degraded performance/reliability), 15 P3 (minor).

**Critical findings**: SQL injection vector in keyword search, duplicate mastery updates causing phantom score inflation, and unbounded BFS in gRPC learning path that enables DoS.

---

## 1. Security Issues

### 1.1 P0 -- SQL Injection in keyword_search via user-controlled ILIKE pattern

**File**: `backend/app/services/galaxy/retrieval_service.py`, lines 587-596
**Issue**: The `query` parameter is interpolated directly into ILIKE patterns and `jsonb_path_exists` without parameterization. An attacker controlling the query string can inject arbitrary SQL.

```python
stmt = (
    select(KnowledgeNode)
    .where(
        or_(
            KnowledgeNode.name.ilike(f"%{query}%"),           # INJECTION
            KnowledgeNode.description.ilike(f"%{query}%"),     # INJECTION
            KnowledgeNode.keywords.contains([query]),
            func.jsonb_path_exists(
                KnowledgeNode.keywords,
                f'$[*] ? (@ like_regex "{query}" flag "i")'     # INJECTION
            )
        )
    )
)
```

**Fix**: Use parameterized `bindparam` for ILIKE patterns and sanitize the regex input:
```python
KnowledgeNode.name.ilike(f"%:query%", {"query": query})
# Or: use text() with bind parameters for the regex expression
```

### 1.2 P1 -- No authorization check on galaxy graph endpoint

**File**: `backend/app/api/v1/galaxy.py`, lines 182-200
**Issue**: `get_galaxy_graph` accepts `user_id` from `get_current_user_id` which returns a string from the JWT. However, other endpoints like `get_node_detail` also accept the same pattern. The issue is that `user_id` is treated as a string from auth but never validated as a real user. If auth is bypassed at the gateway, any string is accepted. The endpoint does not validate the UUID format before passing to service layer.

**Fix**: Add UUID validation at the route level for all user-facing endpoints.

---

## 2. Logic Bugs

### 2.1 P0 -- Duplicate mastery updates from spark_node and feedback_service

**File**: `backend/app/services/galaxy/stats_service.py` (spark_node, line 56) and `backend/app/services/galaxy/feedback_service.py` (lines 254-256)
**Issue**: Both `spark_node` and `GalaxyFeedbackService._update_mastery_from_feedback` can update the same node's mastery for the same event (e.g., task_completed). The `batch_update_from_task` method in `feedback_service.py` (line 330-342) calls `stats_service.spark_node` for each node, which already updates mastery. But `collect_implicit_feedback` with `type=task_completed` also calls `_update_mastery_from_feedback` with +0.8 score. This causes **double mastery increases** for task completion events.

```python
# feedback_service.py line 334
from app.services.galaxy.stats_service import GalaxyStatsService
stats_service = GalaxyStatsService(self.db)
spark_result = await stats_service.spark_node(...)  # Already updates mastery!
```

Meanwhile, `FEEDBACK_SCORES[TASK_COMPLETED] = 0.8` means implicit feedback also adds 0.8*10 = 8 points.

**Fix**: Add a guard flag or deduplication key to prevent both paths from updating mastery for the same task completion event.

### 2.2 P1 -- `_get_or_create_status` race condition in spark_node

**File**: `backend/app/services/galaxy/stats_service.py`, lines 454-469
**Issue**: `_get_or_create_status` does a read-then-write without any locking. Under concurrent requests for the same user+node (e.g., from parallel event consumers), two sessions can both see `status is None` and each create a `UserNodeStatus` row. With a composite PK this causes an IntegrityError, but the error is not caught, crashing the spark operation.

```python
async def _get_or_create_status(self, user_id: UUID, node_id: UUID) -> UserNodeStatus:
    # No SELECT FOR UPDATE or try/except for IntegrityError
    result = await self.db.execute(query)
    status = result.scalar_one_or_none()
    if not status:
        status = UserNodeStatus(...)  # Can race with another concurrent insert
```

**Fix**: Wrap in try/except for IntegrityError and re-select, or use `INSERT ... ON CONFLICT DO NOTHING`.

### 2.3 P1 -- Mastery calculation uses int() truncation causing incorrect scores

**File**: `backend/app/services/galaxy/feedback_service.py`, line 256
**Issue**: `int(old_mastery + score * 10)` truncates toward zero. For example, if `old_mastery=49` and `score=0.8`, the result is `int(49 + 8) = 57`. But if `score=-0.3`, the result is `int(49 + (-3)) = 46`. However, `score * 10` for `QUIZ_PASSED` gives `1.0 * 10 = 10`, and for `QUIZ_FAILED` gives `-0.5 * 10 = -5`. This means the feedback scores are effectively `+/- 10/5/8/3/2` mastery points, which may not be the intended granularity. More critically, this is inconsistent with `spark_node` which uses a different formula entirely.

**Fix**: Use `round()` instead of `int()` for consistent behavior, or standardize the mastery delta calculation across all services.

### 2.4 P1 -- Perfectionist achievement fires twice in spark_node

**File**: `backend/app/services/galaxy/stats_service.py`, lines 187-194
**Issue**: When `mastery_score >= 100`, both the `NODE_MASTERED` event (line 178-184) and a second `NODE_MASTERED` event (line 187-193) are fired. The code has:
```python
if status.mastery_score >= 80:
    await achievement_engine.process_event(..., event_type=AchievementEvent.NODE_MASTERED, ...)
if status.mastery_score >= 100:
    await achievement_engine.process_event(..., event_type=AchievementEvent.NODE_MASTERED, ...)  # DUPLICATE
```
The second block should use `AchievementEvent.HIDDEN_TRIGGER` with code `"PERFECTIONIST"` instead of `NODE_MASTERED`. The `achievement_event_consumer.py` correctly uses `HIDDEN_TRIGGER` for the perfectionist (line 300-306), so `spark_node` is out of sync.

**Fix**: Change line 190 to use `AchievementEvent.HIDDEN_TRIGGER` with `hidden_trigger_code="PERFECTIONIST"`.

### 2.5 P2 -- predict_next_node only follows source->target edges, missing reverse

**File**: `backend/app/services/galaxy/stats_service.py`, lines 304-310
**Issue**: `predict_next_node` only queries `NodeRelation.source_node_id == last_status.node_id`, meaning it only follows outgoing edges. If the user last studied node B which has a relation A->B, the algorithm will not discover A as a candidate. The `get_node_neighbors` in structure_service correctly does undirected lookup, but predict_next_node does not.

```python
relations_query = (
    select(NodeRelation)
    .where(NodeRelation.source_node_id == last_status.node_id)  # Only outgoing!
    .order_by(NodeRelation.strength.desc())
)
```

**Fix**: Use `or_(NodeRelation.source_node_id == ..., NodeRelation.target_node_id == ...)` like `get_node_neighbors`.

### 2.6 P2 -- Heatmap intensity calculation has no upper bound on overdue items

**File**: `backend/app/services/galaxy/stats_service.py`, lines 380-386
**Issue**: Overdue items always get `intensity = 1.0` regardless of how overdue they are. This means a node overdue by 1 day and one overdue by 30 days have the same visual intensity. The `delta` calculation on line 388 is computed but never used for graduated intensity.

```python
if now >= next_review:
    intensity = 1.0  # Always 1.0, no graduation
```

**Fix**: Scale intensity by overdue duration, e.g., `min(1.0, 0.5 + min(days_overdue, 14) / 28)`.

### 2.7 P2 -- `_sprint_pack_candidate_keys` produces overly aggressive fuzzy matching

**File**: `backend/app/services/galaxy_service.py`, lines 229-252
**Issue**: The `_pack_node_match_key` method strips all non-alphanumeric characters and lowercases. Then `_match_sprint_pack_node_id` does substring matching (`candidate in key or key in candidate`). This can cause false positive matches. For example, a node named "TCP" (key="tcp") would match any key containing "tcp" like "tcpprotocol" or "tcpflowcontrol".

```python
if candidate in key or key in candidate:
    return node_id  # substring match causes false positives
```

**Fix**: Require exact match or increase the minimum length threshold (currently 4) for substring matching.

---

## 3. Error Handling Issues

### 3.1 P1 -- spark_node swallows all exceptions silently, masking real failures

**File**: `backend/app/services/galaxy/stats_service.py`, lines 81-128, 163-196, 198-233
**Issue**: Multiple try/except blocks in `spark_node` catch `Exception` and only log warnings. This means:
- Mastery audit log failure (line 100-101): Silently swallowed
- Outbox event failure (line 111-112): Silently swallowed
- Event bus failure (line 127-128): Silently swallowed
- Achievement failure (line 194-195): Silently swallowed
- WebSocket streaming failure (line 232-233): Silently swallowed

While graceful degradation is good, none of these failures are tracked in metrics or alerts. A persistent failure in audit logging or event publishing would go completely unnoticed.

**Fix**: Add Prometheus counters for each failure path and alert on sustained failures.

### 3.2 P2 -- semantic_cache_service get_with_lock has unreliable error detection

**File**: `backend/app/services/semantic_cache_service.py`, lines 357-367
**Issue**: Lock acquisition failure is detected by string matching on the exception type name:
```python
if "LockError" in str(type(e)):
```
This is fragile -- it depends on the string representation of the exception class. If the Redis client library changes the exception class name, this check will silently fail and fall through to the generic error handler.

**Fix**: Use `isinstance(e, redis.exceptions.LockError)` or `type(e).__name__ == "LockError"`.

### 3.3 P2 -- _record_feedback catches all exceptions and rolls back, but caller still returns None

**File**: `backend/app/services/galaxy/feedback_service.py`, lines 202-204
**Issue**: When `_record_feedback` fails, it rolls back the transaction. But the caller `_update_mastery_from_feedback` (line 279-281) also catches exceptions and rolls back. This means a double rollback can occur if the inner rollback succeeds but the outer try/except is still reached. With SQLAlchemy async, double rollback should be safe, but the error handling path is needlessly complex.

**Fix**: Remove the rollback from `_record_feedback` and let the caller handle it, or use savepoints.

---

## 4. Race Conditions

### 4.1 P1 -- Module-level `_PGVECTOR_RUNTIME_ENABLED` flag is not thread-safe

**File**: `backend/app/services/galaxy/retrieval_service.py`, lines 39, 58-62
**Issue**: `_PGVECTOR_RUNTIME_ENABLED` is a module-level global boolean that is read and written without any synchronization. In an async context with multiple coroutines, if one coroutine disables pgvector and another reads the flag, the visibility is not guaranteed. Python's GIL provides some protection for simple boolean reads/writes, but the pattern is fragile.

```python
_PGVECTOR_RUNTIME_ENABLED = True

@staticmethod
def _disable_vector_runtime(reason: str) -> None:
    global _PGVECTOR_RUNTIME_ENABLED
    if _PGVECTOR_RUNTIME_ENABLED:
        logger.warning(...)
    _PGVECTOR_RUNTIME_ENABLED = False
```

**Fix**: Use `asyncio.Lock` or `threading.Event` for proper synchronization, or make the check per-session.

### 4.2 P2 -- `_active_collaborative_sessions` dict has no concurrency protection

**File**: `backend/app/services/galaxy_grpc_service.py`, lines 36, 43-54, 57-64, 67-73
**Issue**: The `_active_collaborative_sessions` OrderedDict is accessed from multiple async coroutines without locking. While Python's GIL prevents true data corruption for simple dict operations, the prune/store pattern is not atomic:
```python
def _store_active_collaborative_session(galaxy_id, service):
    _active_collaborative_sessions[galaxy_id] = ...
    _active_collaborative_sessions.move_to_end(galaxy_id)
    _prune_inactive_collaborative_sessions()  # Can evict the entry just stored
```

The `_prune_inactive_collaborative_sessions` function can evict the session that was just stored if `_COLLABORATIVE_SESSION_TTL` is very small.

**Fix**: Add `asyncio.Lock` for all session dict mutations.

---

## 5. Data Integrity Issues

### 5.1 P1 -- spark_node commits before audit log, causing inconsistent state on audit failure

**File**: `backend/app/services/galaxy/stats_service.py`, lines 79, 82-101
**Issue**: `spark_node` commits the mastery update at line 79, then separately tries to write the audit log (lines 82-101) and outbox event (lines 103-112) with independent commits. If the audit log write succeeds but the outbox event fails, the audit log has one commit while the outbox is missing. This breaks the audit trail integrity.

```python
await self.db.commit()  # Line 79: mastery committed

# 5.1 Audit log -- separate commit
try:
    await self.db.execute(sa_text("INSERT INTO mastery_audit_log ..."))
    await self.db.commit()  # Line 99: separate commit!
except Exception as e:
    logger.warning(...)  # Swallowed!
```

**Fix**: Use a single transaction for mastery update + audit log + outbox event, or use deferred constraint triggers.

### 5.2 P2 -- UserNodeStatus model has redundant time columns with different defaults

**File**: `backend/app/models/galaxy.py`, lines 243-244, 254-255, 265-270
**Issue**: `UserNodeStatus` has both `total_minutes` (line 243) and `total_study_minutes` (line 244) with the same default. `spark_node` in stats_service only updates `total_study_minutes` and `study_count`, never `total_minutes`. This creates data drift -- `total_minutes` is always 0 while `total_study_minutes` tracks actual time.

```python
total_minutes = Column(Integer, default=0, nullable=False)       # Never updated
total_study_minutes = Column(Integer, default=0, nullable=False)  # Updated by spark_node
```

**Fix**: Either deprecate `total_minutes` with a migration or ensure both are updated consistently.

### 5.3 P2 -- GalaxyUserPermission uses `datetime.utcnow` instead of `_utcnow` helper

**File**: `backend/app/models/galaxy.py`, lines 69-70, 88-89
**Issue**: Several models use `datetime.utcnow` as default values, which is deprecated in Python 3.12+ and creates naive datetimes. Other parts of the codebase use `_utcnow()` helper which does `datetime.now(UTC).replace(tzinfo=None)`. While both produce naive UTC datetimes, `datetime.utcnow` is deprecated.

```python
created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # Deprecated
```

**Fix**: Use a lambda or module-level helper: `default=lambda: datetime.now(UTC).replace(tzinfo=None)`.

---

## 6. Performance Issues

### 6.1 P1 -- gRPC GetLearningPath does unbounded BFS with per-node DB queries

**File**: `backend/app/services/galaxy_grpc_service.py`, lines 364-427
**Issue**: The BFS implementation issues a separate DB query for every node visited. With no depth limit or visited-node cap, this is an O(N*Q) operation where N is nodes visited and Q is queries. A malicious or degenerate graph could cause hundreds of queries:

```python
while queue:
    current, path = queue.pop(0)
    # ... for EVERY node in the BFS:
    stmt = select(NodeRelation).where(
        NodeRelation.source_node_id == _UUID(current)
    ).limit(100)
    result = await db.execute(stmt)  # One query per node!
```

**Fix**: Batch-load all edges upfront, or add a max depth/visited limit (e.g., max 20 hops).

### 6.2 P2 -- predict_next_node has N+1 query pattern

**File**: `backend/app/services/galaxy/stats_service.py`, lines 315-347
**Issue**: For each relation, `predict_next_node` calls `_get_user_status` which issues a separate DB query. With 10 relations, this is 10 additional queries.

```python
for rel in relations:
    target_status = await self._get_user_status(user_id, rel.target_node_id)  # N queries
```

**Fix**: Batch-load all target statuses in a single `WHERE node_id IN (...)` query.

### 6.3 P2 -- semantic_cache_service scans all keys on every clear_all

**File**: `backend/app/services/semantic_cache_service.py`, lines 476-477
**Issue**: `clear_all` uses `redis.keys()` which is O(N) and blocks the Redis server. In production with thousands of keys, this causes latency spikes.

```python
keys = await self.redis.keys(f"{self.CACHE_PREFIX}*")
emb_keys = await self.redis.keys(f"{self.EMBED_PREFIX}*")
```

**Fix**: Use `SCAN` instead of `KEYS`, or maintain a Redis SET of active cache keys.

### 6.4 P2 -- `_find_similar_cache_key` loads full embedding payloads for all candidates

**File**: `backend/app/services/semantic_cache_service.py`, lines 196-212
**Issue**: For each candidate key, the service fetches the full embedding JSON payload and computes cosine similarity in Python. With 200 candidates and 1024-dim embeddings, this loads ~200KB of data per cache lookup. Should use Redis vector similarity (available in Redis Stack) instead.

**Fix**: Store embeddings in a Redis vector index and use `FT.SEARCH` with vector similarity.

### 6.5 P2 -- auto_link_nodes does N+1 queries for keyword-to-name matching

**File**: `backend/app/services/expansion_service.py`, lines 1025-1044
**Issue**: For each keyword in `target_node.keywords`, a separate query is issued:
```python
for keyword in target_node.keywords:
    candidates_query = select(KnowledgeNode).where(KnowledgeNode.name == keyword)
    candidates = (await self.db.execute(candidates_query)).scalars().all()
```

**Fix**: Batch all keywords into a single `WHERE name IN (...)` query.

### 6.6 P3 -- `_get_knowledge_version` calls `_compute_knowledge_version` on cache miss without lock

**File**: `backend/app/services/galaxy/retrieval_service.py`, lines 96-108
**Issue**: Multiple concurrent cache misses for `knowledge:version:v1` will all compute the version simultaneously. While not harmful (the result is the same), it wastes DB queries. This is a minor stampede issue.

**Fix**: Use a short-lived lock or single-flight pattern.

---

## 7. Event Handling Issues

### 7.1 P1 -- GalaxyEventConsumer creates status without bkt_mastery_prob initialization

**File**: `backend/app/services/galaxy_event_consumer.py`, lines 115-122
**Issue**: When creating a new `UserNodeStatus` in `_handle_error_created`, the status is created with `bkt_mastery_prob=0.0` explicitly. However, in `_handle_simulation_gap_revealed` (lines 443-454), a new status is created WITHOUT setting `bkt_mastery_prob`:

```python
status = UserNodeStatus(
    user_id=user_uuid,
    node_id=target_node.id,
    mastery_score=0,
    total_minutes=0,
    total_study_minutes=0,
    study_count=0,
    is_unlocked=True,
    learning_path_snapshot=None,
    # Missing: bkt_mastery_prob=0.0
)
```

If the model's default for `bkt_mastery_prob` is ever changed or removed, this would cause a NOT NULL violation.

**Fix**: Always explicitly set `bkt_mastery_prob=0.0` when creating new statuses.

### 7.2 P2 -- AchievementEventConsumer._handle_achievement_unlocked uses fire-and-forget for cognitive fragment

**File**: `backend/app/services/achievement_event_consumer.py`, lines 308-390
**Issue**: The entire `_handle_achievement_unlocked` method is wrapped in a try/except that catches all exceptions (line 389-390). If the cognitive fragment creation fails, the achievement is still considered "processed" and no retry is possible. The `record_achievement_progress_event` on line 453 is also fire-and-forget within a try/except.

**Fix**: Use a DLQ or retry mechanism for failed achievement processing.

### 7.3 P2 -- ErrorBookMasterySyncService pending events may not be published

**File**: `backend/app/services/error_book_mastery_sync_service.py`, lines 321-341
**Issue**: The `_update_node_mastery` method returns a `_pending_event` dict but does not publish it itself. The docstring says "caller commits then flushes pending events." However, `apply_error_diagnosis` (the caller at line 95-160) never publishes these pending events. It just collects results:

```python
results.append(node_result)  # Contains _pending_event but never published!
```

The pending events are created but never actually emitted to the event bus, meaning downstream consumers like `GalaxyEventConsumer._handle_mastery_updated` are never triggered for error-driven mastery changes.

**Fix**: After the commit in `apply_error_diagnosis`, iterate over results and publish pending events.

---

## 8. Mastery Calculation Issues

### 8.1 P2 -- ReviewUrgencyService score calculation can exceed 1.0 before clamping

**File**: `backend/app/services/galaxy/review_urgency_service.py`, lines 76-79
**Issue**: The raw score before clamping can theoretically exceed 1.0:
```python
score = cls._clamp(
    0.55 * mastery_pressure + 0.35 * time_pressure + error_pressure,
    0.0, 1.0,
)
```
With `mastery_pressure` up to 1.0 (mastery=0), `time_pressure` up to 1.0 (very old), and `error_pressure` up to 0.18 (3 errors): `0.55 + 0.35 + 0.18 = 1.08`. This is correctly clamped, but the next_review_at bonus (line 84) adds 0.08 to an already-clamped score. If the score was clamped to 1.0 and then 0.08 is added, the result is 1.08 before the second clamp. While the second clamp handles this, it means the overdue bonus can never actually increase urgency beyond 1.0 -- the clamping happens before the bonus.

**Fix**: Apply the overdue bonus before clamping, or restructure to compute a single raw score and clamp once.

### 8.2 P2 -- ReviewUrgencyService always returns `is_recommended=False` for individual scores

**File**: `backend/app/services/galaxy/review_urgency_service.py`, line 88
**Issue**: `score_status` always sets `is_recommended=False`. Only `score_graph_nodes` sets it to `True` for top candidates. If `score_status` is called directly (which it is from the decay service), the `is_recommended` flag is always False even if the score is very high.

**Fix**: Either document this as intentional or compute recommendation threshold in `score_status` too.

### 8.3 P3 -- ReviewUrgencyService._days_since returns 30.0 for missing last_updated

**File**: `backend/app/services/galaxy/review_urgency_service.py`, lines 150-154
**Issue**: When `last_updated` is None, the function returns 30.0 days. This is a reasonable default but means a newly unlocked node with no study history gets a `days_since=30` which inflates urgency. Combined with `mastery_score=0`, these nodes will always be recommended.

**Fix**: Return 0.0 for nodes with no history, or add a separate "newness" signal.

---

## 9. RAG Pipeline Issues

### 9.1 P1 -- RerankService.reciprocal_rank_fusion uses string IDs for dedup, causing item loss

**File**: `backend/app/services/rerank_service.py`, lines 47-71
**Issue**: RRF deduplication uses `str(item.id)` or `str(item.get("id"))`. If items from different sources (vector vs keyword) have different ID types or representations, the same document may be counted twice. Additionally, if an item has no `id` attribute or key, it will raise an `AttributeError` or `KeyError`.

```python
item_id = str(item.get("id")) if isinstance(item, dict) else str(item.id)
```

**Fix**: Add fallback for missing IDs and handle duplicate content detection.

### 9.2 P2 -- Semantic cache similarity threshold defaults to 1.0 (exact match) in get_with_lock

**File**: `backend/app/services/semantic_cache_service.py`, line 322
**Issue**: When `similarity_threshold` is `None`, it defaults to `1.0` which means exact match only. This effectively disables semantic similarity caching through the `get_with_lock` path:

```python
effective_threshold = similarity_threshold if similarity_threshold is not None else 1.0
```

The caller in `retrieval_service.py` (line 153) passes `settings.SEMANTIC_CACHE_SIM_THRESHOLD`, but if this setting is not configured or is None, the cache degrades to exact match.

**Fix**: Default to `0.92` instead of `1.0` for the `get_with_lock` path.

### 9.3 P2 -- DocumentService has duplicate method definitions

**File**: `backend/app/services/document_service.py`, lines 505-512 and 1264-1285
**Issue**: `_generate_quick_summary` is defined twice: once as a simple method (line 505) and once at module level after `_resolve_allowed_path` (line 1264). The second definition uses LLM, while the first uses a simple heuristic. Due to Python class definition order, the **first definition wins** (the class method at line 505). The LLM-based version at line 1264 is dead code (defined at module level, not as a method).

```python
# Line 505: Class method (used)
async def _generate_quick_summary(self, text: str) -> str:
    stripped = (text or "").strip()
    ...

# Line 1264: Module-level function (DEAD CODE)
async def _generate_quick_summary(self, text: str) -> str:
    """Single-shot summary for small files."""
    try:
        from langchain_core.prompts import ChatPromptTemplate
        ...
```

Same issue with `_run_map_reduce` (line 514 vs 1287) and `_extract_section_summary` (line 529 vs 1310).

**Fix**: Remove the dead code at lines 1264-1385 or refactor to use the LLM version.

---

## 10. API Contract Issues

### 10.1 P2 -- gRPC GetGalaxyStats computes incorrect average_mastery

**File**: `backend/app/services/galaxy_grpc_service.py`, lines 478
**Issue**: Average mastery is computed as `mastered_count / total_nodes * 100`. This is the percentage of mastered nodes, not the average mastery. If a user has 10 nodes with varying mastery scores (e.g., 30, 50, 70, 80, 90), the average mastery should be 64, but this formula returns `count(>=80) / 10 * 100 = 10` (if only 1 node is >= 80).

```python
avg_mastery = (stats.mastered_count / stats.total_nodes * 100.0) if stats.total_nodes > 0 else 0.0
```

**Fix**: Compute the actual average: `sum(all_mastery_scores) / total_nodes`.

### 10.2 P2 -- gRPC GetNodeDetail accesses non-existent `tags` attribute

**File**: `backend/app/services/galaxy_grpc_service.py`, line 320
**Issue**: The `KnowledgeNode` model uses `keywords` (JSONB), not `tags`. The code tries:
```python
tags=node.tags or [] if node else [],
```
This will always return `[]` because `KnowledgeNode` has no `tags` attribute. It should be `node.keywords`.

**Fix**: Change `node.tags` to `node.keywords`.

### 10.3 P3 -- gRPC SearchNodes returns mastery=0 for all results

**File**: `backend/app/services/galaxy_grpc_service.py`, line 347
**Issue**: The `mastery` field is hardcoded to `0` for all search results:
```python
mastery=0,
```
This should look up the user's mastery for each node.

**Fix**: Join with `UserNodeStatus` and return actual mastery.

### 10.4 P3 -- Multiple endpoints have duplicate route registrations

**File**: `backend/app/api/v1/galaxy.py`
**Issue**: Multiple endpoints register both `/node/{id}/...` and `/nodes/{id}/...` paths (singular and plural). While this works, it doubles the number of routes FastAPI needs to match and complicates API documentation:
- Lines 379-380: `spark_node`
- Lines 401-402: `get_node_history`
- Lines 444-445: `get_node_source_chunks`
- Lines 467-468: `get_node_detail`
- Lines 106-107: `update_node_mastery`

**Fix**: Standardize on `/nodes/{id}/...` (plural) and add redirects for the singular form, or use API versioning.

---

## 11. Dead Code

### 11.1 P3 -- CollaborativeGalaxyService is imported but never used in production flow

**File**: `backend/app/services/galaxy/collaborative_service.py`
**Issue**: This service provides Yjs-based CRDT operations for collaborative galaxy editing. However, it is only used by `galaxy_grpc_service.py`'s `SyncCollaborativeGalaxy`, and the CRDT operations are basic (no conflict resolution, no operational transform). The `update_mastery` method stores mastery as a plain dict value without any BKT or decay integration.

### 11.2 P3 -- graph_knowledge_service.py does not exist

**File**: `backend/app/services/galaxy/graph_knowledge_service.py`
**Issue**: Listed in the audit scope but the file does not exist. This suggests the planned service was never implemented or was merged into another file.

### 11.3 P3 -- DocumentService._FEEDBACK_CACHE_VERSION_KEY and related methods are defined but not used in Galaxy flow

**File**: `backend/app/services/document_service.py`
**Issue**: The feedback cache version methods (`_bump_feedback_cache_version`, `register_turn_citations`, `capture_implicit_feedback_from_message`) are not called from any Galaxy service. They appear to be designed for a document retrieval feedback loop that is not yet integrated.

---

## 12. Async Issues

### 12.1 P2 -- EmbeddingService sets dashscope.api_key on every call (shared state mutation)

**File**: `backend/app/services/embedding_service.py`, lines 138-141
**Issue**: `_dashscope_embeddings` sets the global `dashscope.api_key` and `dashscope.base_http_api_url` on every call. If multiple coroutines call this concurrently, they may overwrite each other's API key:

```python
def _call(batch=chunk):
    dashscope.api_key = self.dashscope_api_key  # Global mutation!
    if self.dashscope_base_url:
        dashscope.base_http_api_url = self.dashscope_base_url  # Global mutation!
```

Since `self.dashscope_api_key` is always the same instance value, this is not currently a bug, but if the service is ever configured per-request, it would be a race condition.

**Fix**: Set API key once in `__init__` or use per-call context.

### 12.2 P3 -- ExpansionService.record_feedback uses asyncio.create_task without awaiting

**File**: `backend/app/services/expansion_service.py`, line 665
**Issue**: `asyncio.create_task(_refresh_galaxy_feedback_signals(user_id))` creates a fire-and-forget task. If this task raises an exception, it will be logged as "Task was destroyed but it is pending!" in Python 3.11+ instead of being properly handled.

```python
asyncio.create_task(_refresh_galaxy_feedback_signals(user_id))
```

**Fix**: Use `asyncio.ensure_future` with a done callback, or store the task reference.

---

## Summary Table

| Severity | Count | Key Issues |
|----------|-------|------------|
| P0 | 2 | SQL injection in keyword_search; duplicate mastery updates |
| P1 | 8 | Race condition in status creation; unbounded BFS DoS; module-level flag; audit log inconsistency; missing event publishing; Perfectionist double-fire; missing auth validation; RRF item handling |
| P2 | 16 | N+1 queries (3 instances); cache stampede; wrong avg_mastery; wrong attribute access; semantic cache threshold; duplicate method definitions; BFS single-direction; heatmap intensity; overdue bonus clamping; pending events not published; fire-and-forget patterns |
| P3 | 15 | Dead code (3 instances); duplicate routes; deprecated datetime.utcnow; naive defaults; async create_task; shared state mutation; missing tags/keywords |

## Priority Remediation Order

1. **P0-1**: Fix SQL injection in `retrieval_service.py` keyword_search (parameterize queries)
2. **P0-2**: Fix duplicate mastery updates in `feedback_service.py` / `stats_service.py`
3. **P1-1**: Add IntegrityError handling in `_get_or_create_status`
4. **P1-2**: Add depth/visited limits to gRPC `GetLearningPath` BFS
5. **P1-3**: Fix `apply_error_diagnosis` to publish pending events
6. **P1-4**: Fix Perfectionist achievement to use HIDDEN_TRIGGER
7. **P1-5**: Fix `predict_next_node` to follow bidirectional edges
8. **P2 fixes**: Address N+1 queries, semantic cache defaults, and incorrect attribute access
