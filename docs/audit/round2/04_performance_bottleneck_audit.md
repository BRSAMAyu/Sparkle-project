# Round 2 Deep Audit: Performance Bottleneck Quantitative Analysis

**Date**: 2026-05-15
**Auditor**: Claude Agent (Performance Audit)
**Scope**: Serial operation chains, caching, database queries, LLM costs, Redis efficiency

---

## Executive Summary

This audit quantifies performance bottlenecks across five domains. The most critical finding is that **a single `task.completed` event triggers 8-10 serial operations** spanning 8+ independent database sessions, resulting in an estimated **500-1200ms wall-clock latency** in the event processing hot path. The StateAggregatorService has a bounded but poorly documented in-process cache, and the `_build_achievement_summary` method issues 3 queries to the same table where 1 would suffice.

---

## 1. Serial Operation Chain Latency Analysis

### 1.1 TaskEventConsumer._handle_task_completed (8-10 serial operations)

**File**: `backend/app/services/task_event_consumer.py:92-243`

A single `task.completed` event triggers the following serial chain:

| # | Operation | IO Type | Est. Latency (Best/Typical/Worst) | Session |
|---|-----------|---------|-----------------------------------|---------|
| 1 | `BehaviorSignalCollector.handle_task_completed_event` | DB write + Redis read/write | 5/15/50ms | Independent |
| 2 | `MetacognitionService.refresh_snapshot` | DB read+write + Redis | 10/30/80ms | Independent |
| 3 | `CommunitySignalBridge.handle_group_task_completed` | DB read + Redis | 5/10/30ms | Independent |
| 4 | `_record_task_outcome` (OutcomeTracker) | Redis multi-key read+write | 2/5/15ms | Independent |
| 5 | `SpineOrchestrator.on_task_completed` | Redis heavy (8-15 ops) + DB | 20/60/200ms | Independent |
| 6 | `AutoFragmentCollector.collect_from_task_completion` | DB read+write | 5/15/40ms | Independent |
| 7 | `AdaptiveReplanner.on_task_completed` | DB read + Redis + possible LLM | 10/40/500ms* | Independent |
| 8 | Fetch plan_id from Task table (if missing) | DB read | 2/5/10ms | Independent |
| 9 | Goal progress update (read Goal + 2 COUNT queries + write) | DB read+write | 5/15/30ms | Independent |

**Total estimated wall-clock latency**:
- **Best case**: 64ms (all caches hot, no LLM call)
- **Typical case**: 195ms (cold caches, no LLM)
- **Worst case**: 955ms (AdaptiveReplanner triggers LLM + Redis contention)

**Critical finding**: Operations 1-6 are fully independent (each opens its own `AsyncSessionLocal()`), yet they execute **sequentially**. They could be parallelized with `asyncio.gather()`.

**Parallelized estimate**:
- Best: 20ms (limited by slowest operation)
- Typical: 60ms
- Worst: 500ms

**Potential speedup**: 3-5x for the non-LLM path.

### 1.2 SignalAggregator._collect_readings (10 signal sources)

**File**: `backend/app/aurora/signal_aggregator.py:300-329`

**IMPORTANT CORRECTION**: The code at line 308-311 creates coroutines eagerly but **awaits them sequentially** (line 312-313). Despite creating `tasks` list, it does NOT use `asyncio.gather()`. The variable name `tasks` is misleading.

| # | Source | Service Key | IO Type | Est. Latency |
|---|--------|------------|---------|-------------|
| 1 | `memory_service` | CORE | DB (3 queries: goals, preferences, episodic) | 5/20/60ms |
| 2 | `focus_service` | CORE | DB (1 query: today_stats) | 2/5/15ms |
| 3 | `companion_state_service` | ENHANCED | DB (2 queries: effective_state, recent_revisions) | 5/15/40ms |
| 4 | `user_strategy_state_service` | ENHANCED | DB (2 queries: effective_state, recent_changes) | 5/15/40ms |
| 5 | `persona_service` | ENHANCED | DB (1 query: snapshot) | 2/10/25ms |
| 6 | `error_book_service` | CORE | DB (2 queries: review_stats, list_errors) | 5/15/40ms |
| 7 | `plan_state_service` | ENHANCED | DB (2 queries: plan_state, active_plans) | 5/15/40ms |
| 8 | `achievement_engine` | OPTIONAL | DB (1-2 queries) | 5/10/30ms |
| 9 | `predictive_service` | OPTIONAL | DB (2 queries: engagement, next_intent) | 5/15/40ms |
| 10 | `analytics_service` | OPTIONAL | DB (1 query: profile_summary) | 2/10/25ms |

**Sequential total**:
- Best: 41ms
- Typical: 130ms
- Worst: 355ms

**If parallelized with `asyncio.gather()`**:
- Best: 5ms
- Typical: 20ms
- Worst: 60ms

**Potential speedup**: 5-6x.

### 1.3 StruggleSignalAggregator._collect_signals (7+ serial DB queries)

**File**: `backend/app/services/struggle_signal_aggregator.py:162-207`

| # | Query Method | Table(s) | Query Complexity | Est. Latency |
|---|-------------|----------|-----------------|-------------|
| 1 | `_task_skip_counts` | tasks | 2x COUNT with OR+AND filters on created_at/updated_at | 3/10/30ms |
| 2 | `_short_session_counts` | focus_sessions (+ join tasks) | 2x COUNT with join | 3/10/25ms |
| 3 | `_error_counts_3d` | error_records | 3x COUNT (loop: days 0,1,2) | 5/15/40ms |
| 4 | `_overdue_task_count` | tasks | COUNT with IN status + date comparison | 2/5/15ms |
| 5 | `_struggle_streak` | plan_states | SELECT facts JSON + parse | 2/5/10ms |
| 6 | `_completion_gap` | tasks | 2-3x queries (recent count, max completed_at, min created_at) | 5/15/35ms |

**Additional queries in `get_struggle_context`** (called separately):
| 7a | `_recent_stuck_concepts` | error_records | SELECT with ORDER BY, LIMIT 5, N+1 attribute access | 3/10/20ms |
| 7b | `_days_behind` | tasks | SELECT due_date with IN filter | 2/5/10ms |
| 7c | `_last_active_text` | focus_sessions + tasks + error_records | 3x MAX() queries | 5/15/30ms |

**Sequential total** (compute_struggle_score):
- Best: 20ms
- Typical: 60ms
- Worst: 155ms

**get_struggle_context total** (includes compute_struggle_score + 3 additional):
- Best: 30ms
- Typical: 90ms
- Worst: 215ms

**Issue**: `_error_counts_3d` loops 3 times for 3 days. This should be a single GROUP BY date query.

### 1.4 StateAggregatorService._build_achievement_summary (3 queries to same table)

**File**: `backend/app/state_aggregator/service.py:759-870`

| # | Query | Filter | Purpose |
|---|-------|--------|---------|
| 1 | Recent unlocks (14d) | `user_id, unlocked_at NOT NULL, unlocked_at >= cutoff` LIMIT 5 | Display recent |
| 2 | In-progress | `user_id, unlocked_at IS NULL, progress > 0.5` LIMIT 5 | Display in-progress |
| 3 | ALL achievements | `user_id` (no limit) | Calculate total score |

**Analysis**: Queries 1 and 2 are subsets of query 3. All three can be replaced by a **single query** that fetches all user achievements, then splits in Python.

**Current latency**: 3 DB round-trips = 6-45ms
**After merge**: 1 DB round-trip = 2-15ms
**Savings**: ~50-70% reduction

**Additional concern**: Query 3 fetches ALL achievements without limit. For users with many achievements (100+), this becomes an unbounded result set loading entire ORM objects.

### 1.5 StateAggregatorService._evaluate_sufficiency (hidden N+1)

**File**: `backend/app/state_aggregator/service.py:1064-1097`

When either `task_sufficiency_summary` or `context_sufficiency_summary` is requested, `_evaluate_sufficiency` internally calls:
1. `_build_commitment_summary` (1 DB query)
2. `_build_recent_person_mentions` (1 DB query)
3. `_build_engagement_state` (2 DB queries)
4. `_build_working_memory_snapshot` (1-2 DB queries + Redis)

These are **additional queries beyond what the user already requested**. If the caller already requested these fields, they will be computed twice (the in-process cache helps, but only if within the same `get_user_state` call AND the sufficiency fields come after).

**Hidden cost**: 5-6 additional DB queries per sufficiency evaluation.

---

## 2. Cache System Audit

### 2.1 StateAggregatorService._cache (In-Process)

**File**: `backend/app/state_aggregator/service.py:110-113`

```python
self._cache: dict[
    tuple[UUID, UserStateFieldName, str],
    tuple[StateFieldEnvelope[Any] | None, datetime],
] = {}
```

**Max entry count**: 500 (line 228: eviction triggers at `> 500`)
**Max key space**: `N_users * 20 fields * N_fingerprints`
- With 100 concurrent users and 20 fields: up to 2,000 possible keys
- With fingerprint variations (sufficiency fields): 2,000 * ~10 fingerprints = 20,000
- **Actual cap**: 500 entries, with LRU-like eviction of expired entries only

**Issue**: The cache evicts only expired entries when count exceeds 500. If all entries are fresh (within TTL), no eviction occurs and the cache stays at 500. This is **safe but suboptimal** -- it means under high concurrency the cache hit rate drops because entries are evicted even when fresh.

**Memory per entry**: ~200 bytes (envelope + datetime + key tuple)
**Max memory**: ~100 KB at cap -- **acceptable**.

### 2.2 CacheSystem Overview

| Location | Type | TTL | Max Size | Consistency Risk |
|----------|------|-----|----------|-----------------|
| `StateAggregatorService._cache` | In-process dict | 15s-24h (per field) | 500 entries | **Medium**: no invalidation on DB writes |
| `CacheService._local_cache` | In-process dict | Configurable (default 300s) | 5,000 entries | **Low**: fallback only when Redis down |
| `CacheService.redis` | Redis | Configurable (default 300s) | Unbounded | **Low**: TTL-based expiry |
| `WorkingMemoryService._local_store` | In-process dict (class-level!) | 4h | 40 entries/session | **HIGH**: shared across instances |
| `WorkingMemoryService.redis` | Redis | 4h (IDLE_EXPIRY_SECONDS) | 40 entries/session | **Low**: TTL-based expiry |
| `StruggleSignalAggregator.redis` | Redis | 6h (REDIS_TTL) | 1 key per user/plan | **Medium**: no invalidation on task events |
| `MetacognitionService.redis` | Redis | 60s (AURORA_METACOG_CACHE_TTL) | Per user | **Low**: short TTL |
| `SpineOrchestrator` (various) | Redis | 30d traces, 48h directives, 24h counters | Per user | **Low**: well-structured TTLs |
| `EventBus._idempotency` | Redis | 24h | Per message | **Low**: auto-cleanup |

### 2.3 Cache Consistency Issues

**Issue 1: StateAggregatorService._cache has no write-through invalidation**

When the DB is updated (e.g., a new achievement is unlocked), the in-process cache still serves stale data until TTL expires. With TTLs ranging from 15s to 24h, this means:
- SRL phase: up to 15s stale
- Emotion hint: up to 60s stale
- Learning state: up to 24h stale
- Achievement summary: up to 300s stale

**Impact**: Low for most fields (brief staleness is acceptable). **Medium** for `engagement_state` (60s) and `commitment_summary` (30s) during active sessions where the user just completed a task.

**Issue 2: WorkingMemoryService._local_store is a class variable**

```python
class WorkingMemoryService:
    _local_store: dict[str, tuple[str, datetime | None]] = {}
```

This is shared across ALL instances of `WorkingMemoryService`. In a multi-worker deployment, this causes cross-user data leakage in the fallback path (when Redis is unavailable).

**Issue 3: StruggleSignalAggregator 6h TTL with no event-based invalidation**

If a user completes multiple tasks rapidly, the cached `struggle_score` will not reflect the improvement until TTL expires. The score is only recalculated when explicitly requested after TTL expiry.

---

## 3. Database Query Hotspots

### 3.1 pgvector HNSW Configuration

**File**: `backend/alembic/versions/stage38_06_add_vector_hnsw_indexes.py`

All HNSW indexes use **default PostgreSQL parameters** (no explicit `m` or `ef_construction`):

```sql
CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL
```

Default HNSW parameters:
- `m = 16` (connections per layer)
- `ef_construction = 64` (build-time search depth)

**Vector dimensions**: 1024 (from `Vector(1024)` in models)

**Indexed tables**:
1. `cognitive_fragments.embedding` (also has a separate earlier HNSW index)
2. `knowledge_nodes.embedding`
3. `episodic_memories.embedding`
4. `document_chunks.embedding`
5. `scenes.centroid_embedding`

**Performance assessment**:
- For tables with <100K rows: default parameters are fine. Query latency ~5-15ms.
- For tables growing >100K rows: should consider `m = 32, ef_construction = 128` for better recall.
- **Missing**: No `ef_search` runtime parameter is set in queries. The default `ef_search = 40` may be insufficient for high-recall requirements.

**Recommendation**: Monitor recall@10 on knowledge_nodes and episodic_memories. If recall drops below 0.9, increase `ef_search` to 100-200 via `SET hnsw.ef_search = 200` before queries.

### 3.2 CognitiveFragment Embedding Deferred Loading

**File**: `backend/app/models/cognitive.py:74`

```python
embedding = deferred(Column(VectorCompat, nullable=True))
```

**Positive**: `deferred()` prevents loading the 1024-dim vector on every query. Good design.

**Issue**: In `_build_emotion_hint_summary` (StateAggregatorService:509-548), the query explicitly selects `CognitiveFragment.sentiment` only, so the deferred column is NOT loaded. This is correct.

However, in `galaxy_service.py:1367,1486,1497,1511,1526`, we see:
```python
.options(undefer(KnowledgeNode.embedding))
```

These queries **intentionally load the embedding** for similarity comparison. When these queries return multiple rows, the 1024-dim vectors consume significant memory:
- 1 row: ~8 KB
- 10 rows: ~80 KB
- 50 rows: ~400 KB

**Assessment**: Acceptable for individual queries, but the in-memory cosine similarity loop (line 1534-1541) comparing against ALL loaded nodes is O(n). For a user with 200+ knowledge nodes, this becomes 200 * 8KB = 1.6MB loaded + 200 cosine comparisons.

### 3.3 MemoryService SELECT FOR UPDATE Lock Contention

**File**: `backend/app/services/memory_service.py:111-123`

```python
result = await self.db.execute(
    select(MemoryPreference)
    .where(...)
    .order_by(MemoryPreference.version.desc())
    .limit(1)
    .with_for_update()  # Row-level lock until transaction ends
)
```

**Risk analysis**:
- The lock is per `(user_id, pref_key)` row
- Lock held from SELECT until COMMIT (includes the INSERT of new version)
- If two concurrent writes occur for the same user+pref_key, one will block

**Contention scenarios**:
- Single user: extremely unlikely (UI prevents concurrent pref edits)
- High-concurrency API: possible if background services (trait observer, profile updater) write preferences simultaneously

**Lock duration estimate**: 10-50ms (SELECT + INSERT + COMMIT)

**Assessment**: **Low risk** for normal operation. The `with_for_update()` is correct for preventing race conditions. However, if the background event consumers start writing preferences concurrently for the same user, contention will increase.

**Second occurrence** (line 465): Same pattern for goal-related memory writes. Same risk assessment.

### 3.4 Query Hotspot: Achievement Summary Full Table Scan

**File**: `backend/app/state_aggregator/service.py:795-801`

```python
score_rows = (
    await self.db.execute(
        select(UserAchievement, Achievement)
        .join(Achievement, Achievement.id == UserAchievement.achievement_id)
        .where(UserAchievement.user_id == user_id)
    )
).all()
```

This query has **no LIMIT**. For a user with 50 achievements, it loads 50 ORM tuples (UserAchievement + Achievement each). With `joinedload` of Achievement, this is a single query, but the result set grows linearly with user progress.

**With 500 DAU and 30s TTL**: Up to 500 * 2 = 1000 queries/hour in worst case, but cache mitigates this to ~60/hour.

---

## 4. LLM Call Cost Analysis

### 4.1 Decision Loop Prompt Size

**File**: `backend/app/orchestration/prompts.py:884+` (function `build_system_prompt`)

The system prompt is composed from multiple sections:
1. Base prompt (`AGENT_SYSTEM_PROMPT` or `MODE_SYSTEM_PROMPTS[chat_mode]`)
2. Agent persona section
3. Aurora language contract
4. User context (formatted)
5. Past session memory section
6. Capsule preference section
7. Preference instructions
8. Dual-core instruction
9. Intent instruction
10. Session feedback instruction
11. Context focus
12. Context briefing note
13. Aurora planning sidecar prompt
14. Understanding depth hint
15. Spine response directive
16. Spine chronicle summary
17. Spine fatigue context
18. Collaboration narrative
19. LLM profile

**Estimated prompt size**:
- Base system prompt: ~800-1200 tokens (from 4589-line prompts.py, base templates)
- User context: ~200-500 tokens
- Conversation history: ~500-2000 tokens (pruned)
- Additional sections: ~300-800 tokens

**Total per chat turn**: **1,800 - 4,500 tokens input** (typical: ~3,000 tokens)

**Output**: ~200-800 tokens per response

**Cost per turn (Claude 3.5 Sonnet pricing)**:
- Input: 3,000 tokens * $3/MTok = $0.009
- Output: 500 tokens * $15/MTok = $0.0075
- **Total per turn**: ~$0.017

### 4.2 Aurora L2 Decision Loop Call Frequency

**File**: `backend/app/aurora/runtime_v1.py` (AuroraRuntimeV1Service)

The decision loop runs:
- On every chat turn (generation path)
- Via `dual_core_router.py` for routing decisions
- Via `AdaptiveReplanner.evaluate_plan_health_now` (triggered from TaskEventConsumer)

**Average calls per user session**:
- Standard chat: 1 LLM call per turn (generation)
- Plan review: 1 additional LLM call
- Adaptive replan: 1 additional LLM call (conditional)

**Typical session (5 turns)**: 5-7 LLM calls
**Worst case (10 turns + plan + replan)**: 12 LLM calls

### 4.3 SignalAggregator 4000 Token Budget

**File**: `backend/app/aurora/signal_aggregator.py:234`

```python
budget_limit: int = 4000
```

**Assessment**:
- 10 signal sources, each producing ~200-600 tokens of JSON
- Total raw tokens: ~2,000-6,000
- After `_compact_payload` (max_depth=2, max_items=6, max_text=180): ~1,500-3,000 tokens
- After `_enforce_budget` trimming: capped at 4,000

**Budget is adequate** for the compacted payloads. The trimming logic (lines 341-396) drops OPTIONAL tier first, then ENHANCED, then CORE.

**Concern**: The budget is for the **signal snapshot**, not the full prompt. The signal snapshot is ONE component of the larger prompt. If the signal snapshot takes 4,000 tokens, plus 3,000 tokens base prompt, that's 7,000 tokens of system prompt alone -- consuming a significant portion of the context window.

---

## 5. Redis Resource Assessment

### 5.1 Event Bus: Single Stream, 18 Consumer Groups

**Stream**: `sparkle_events`
**Consumer groups** (from code audit):

| # | Consumer Group | Events Handled |
|---|---------------|---------------|
| 1 | `achievement_event_consumer` | task.completed, achievement.* |
| 2 | `capsule_event_consumer` | capsule.* |
| 3 | `cognitive_consumer_group` | behavior.*, capsule.* |
| 4 | `document_feedback_event_consumer` | document.citation.feedback |
| 5 | `execution_event_consumer` | task.started, task.completed, task.abandoned |
| 6 | `galaxy_event_consumer` | knowledge_node_updated, error_created |
| 7 | `galaxy_execution_consumer` | node_mastery_updated |
| 8 | `group_file_event_consumer` | group.file.* |
| 9 | `idiographic_association` | trait_observed, profile.preference.* |
| 10 | `intervention_event_consumer` | intervention_record.created |
| 11 | `main_chain_artifact_consumer` | task.completed, plan.created |
| 12 | `nudge_consumer_group` | focus.session.completed, task.* |
| 13 | `plan_health_event_consumer` | plan.created, task.* |
| 14 | `python_preference_consumer` | profile.preference.* |
| 15 | `profile_event_consumer` | profile.preference.* |
| 16 | `social_signal_event_consumer` | social.* |
| 17 | `srl_phase_tracker` | srl.phase.transition |
| 18 | `task_event_consumer` | task.*, plan.*, reflection.*, behavior.* |

**Performance impact**: Redis Streams with 18 consumer groups means:
- Each XREADGROUP call checks the pending list for that group
- `XADD` with `MAXLEN ~50000` triggers periodic trimming
- Each consumer group maintains its own PEL (Pending Entry List)

**Estimated memory per stream entry**: ~500 bytes
**At 50K max entries**: ~25 MB for the stream itself
**With 18 consumer group pending entries**: minimal additional overhead (acknowledged entries are not duplicated)

**Bottleneck risk**: **Low** at current scale. Redis Streams handle thousands of consumer groups efficiently. The concern is the **processing time per event** -- if one consumer group falls behind (e.g., `task_event_consumer` processing 8-10 serial operations), its PEL grows, but other groups are unaffected.

### 5.2 Spine Redis Keys: TTL and Memory

**File**: `backend/app/signals/causal_trace_store.py:31-33`

| Key Pattern | TTL | Per-User Count | Est. Size/Key |
|------------|-----|---------------|---------------|
| `spine:trace:{trace_id}` | 30 days | ~5-20 traces/month | 2-5 KB |
| `spine:user_traces:{user_id}` | 30 days | 1 | 1-3 KB (list of trace IDs) |
| `spine:user_traces_compact:{user_id}` | 90 days | 1 | 5-10 KB |
| `spine:directive:{user_id}` | 48 hours | 1 | 1-2 KB |
| `spine:directive_by_id:{id}` | 30 days | ~5-20/month | 1-2 KB |
| `spine:policy:{id}` | 30 days | ~10-30/month | 0.5-1 KB |
| `spine:audit_by_id:{id}` | 30 days | ~10-30/month | 0.5-1 KB |
| `spine:agenda:{session_id}` | Session | 1/session | 0.5-1 KB |
| `spine:agendas:{user_id}` | Session | 1 | 0.2-0.5 KB |
| `spine:interaction_count:{user_id}:24h` | 24 hours | 1 | ~50 bytes |
| `spine:pipeline_lock:{user_id}` | 30 seconds | 1 | ~20 bytes |
| `spine:absence_cooldown:{user_id}:{level}` | Hours | 0-3 | ~50 bytes |
| `spine:deep_learning_*` | Variable | 0-3 | 1-5 KB |
| `spine:achievement_events:{user_id}` | TTL? | 1 | 1-5 KB |
| `spine:aurora_wake_pending:{user_id}` | 1 hour | 0-1 | 0.5 KB |

**Per-user Spine memory estimate**: ~50-150 KB (active user with regular task completions)

**At 1000 DAU**: 50-150 MB total for Spine keys. **Manageable**.

### 5.3 WorkingMemory 4h TTL Assessment

**File**: `backend/app/working_memory/service.py:21`

```python
IDLE_EXPIRY_SECONDS = 60 * 60 * 4  # 4 hours
```

**Assessment**:
- 4h is reasonable for active sessions (typical study session: 1-3 hours)
- After session end, entries get reduced TTL of 10 minutes (`SESSION_END_GRACE_SECONDS`)
- Maximum 40 entries per session (`MAX_ENTRIES_PER_SESSION`)

**Concern**: If a user has a 6-hour study session, entries created in the first hour expire while the session is still active. The `_touch_session` call on each upsert extends the session meta TTL, but **individual entry TTLs are not refreshed**.

**Impact**: Entries created >4h ago silently disappear. For long sessions, early context is lost.

**Recommendation**: Consider refreshing entry TTLs when `mention_count` is incremented (via `_save_entry` in `upsert_entry`). This already happens because `upsert_entry` calls `_save_entry` with `ttl_seconds=self.IDLE_EXPIRY_SECONDS` for both new and updated entries. **So this concern is actually mitigated** for entries that get updated. Only entries that are never mentioned again will expire after 4h, which is correct behavior.

---

## 6. Repair Priority Matrix

| # | Issue | Effort | Impact | Priority |
|---|-------|--------|--------|----------|
| P1 | Parallelize TaskEventConsumer operations 1-6 with `asyncio.gather()` | 2h | 3-5x latency reduction on task.completed | **HIGH** |
| P2 | Parallelize SignalAggregator._collect_readings with `asyncio.gather()` | 1h | 5-6x latency reduction on signal assembly | **HIGH** |
| P3 | Merge _build_achievement_summary 3 queries into 1 | 1h | 50-70% reduction in achievement query time | **MEDIUM** |
| P4 | Rewrite _error_counts_3d as single GROUP BY query | 30min | 66% reduction (3 queries -> 1) | **MEDIUM** |
| P5 | Add ef_search=200 to vector similarity queries | 30min | Improved recall at marginal cost | **LOW** |
| P6 | Fix WorkingMemoryService._local_store class-level shared dict | 1h | Prevent cross-user data leakage in fallback | **MEDIUM** |
| P7 | Add signal-based cache invalidation for StateAggregator | 4h | Better consistency for active sessions | **LOW** |
| P8 | Add LIMIT to achievement score_rows query | 15min | Prevent unbounded result sets | **LOW** |
| P9 | Deduplicate _evaluate_sufficiency sub-queries with already-fetched fields | 2h | Eliminate 5-6 redundant queries per sufficiency check | **MEDIUM** |
| P10 | Monitor and alert on Event Bus consumer group lag | 2h | Operational visibility | **LOW** |

---

## 7. Key Findings Summary

1. **Highest ROI fix**: Parallelize TaskEventConsumer operations (P1). A single `task.completed` event currently takes 200ms+ in serial operations that are independent and could run concurrently.

2. **SignalAggregator is NOT parallelized** despite appearances. The `tasks` variable name is misleading -- coroutines are awaited sequentially.

3. **Achievement summary queries** are the most obvious N+1 pattern: 3 queries to the same `user_achievements` table where 1 suffices.

4. **Cache system is generally well-designed** with proper TTLs and bounded in-process caches. The main risk is the class-level `_local_store` in WorkingMemoryService.

5. **Redis Event Bus with 18 consumer groups** is fine at current scale. The bottleneck is per-group processing time, not Redis infrastructure.

6. **LLM cost per chat turn** is approximately $0.017 (input + output), with the system prompt consuming 60-70% of input tokens.

7. **pgvector HNSW indexes use default parameters**, which is acceptable at current scale but should be monitored as data grows.
