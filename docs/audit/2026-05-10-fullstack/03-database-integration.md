# Database & Integration Audit Report

**Date**: 2026-05-10
**Auditor**: Claude Agent (Opus)
**Scope**: Full database layer + 7 cross-component integration paths

---

## Executive Summary

| Category | P0-Critical | P1-High | P2-Medium | P3-Low | Total |
|----------|-------------|---------|-----------|--------|-------|
| Schema & Migrations | 1 | 3 | 4 | 2 | 10 |
| PostgreSQL Features | 0 | 1 | 2 | 1 | 4 |
| Redis & Event Bus | 0 | 1 | 2 | 1 | 4 |
| Integration Paths | 1 | 3 | 3 | 2 | 9 |
| Proto Contracts | 0 | 1 | 2 | 0 | 3 |
| **Total** | **2** | **9** | **13** | **6** | **30** |

---

## Part A: Database Layer

### A1. Schema & Migrations

#### DB-A01 [P0] AchievementType Enum Duplicate in schema.sql
- **File**: `backend/gateway/internal/db/schema.sql:130-137`
- **Description**: The `achievementtype` enum in schema.sql contains BOTH lowercase `'planning'` AND uppercase `'PLANNING'` as separate values. Although the Alembic migration `r8_fix_achievementtype_enum_duplicate.py` attempts to fix this, the schema.sql dump still shows both values, meaning the fix was either not applied to the actual database or the dump was taken before the migration ran.
- **Impact**: Duplicate enum values violate PostgreSQL uniqueness constraints. Any `CREATE TYPE` recreation from this dump will fail. Data inconsistency between rows using `'planning'` vs `'PLANNING'`.
- **Fix**: 1) Run `alembic upgrade head` to apply the fix migration. 2) Regenerate schema.sql via `make sync-db` after migration. 3) Verify: `SELECT unnest(enum_range(NULL::achievementtype));`

#### DB-A02 [P1] Circular FK Between goals and plans Without CASCADE
- **File**: `backend/gateway/internal/db/schema.sql` lines ~17598 and ~17662
- **Description**: `goals.plan_id REFERENCES plans(id)` (no ON DELETE) and `plans.goal_id REFERENCES goals(id) ON DELETE SET NULL` create a circular foreign key. Deleting a plan that references a goal that references that same plan back will fail because the goal row still holds a reference. The `goals_user_id_fkey` also lacks `ON DELETE CASCADE` (unlike most other tables).
- **Impact**: Cannot delete users with goals+plans without manual intervention. Application-level cascades may silently fail.
- **Fix**: 1) Add `ON DELETE SET NULL` to `goals.plan_id` FK. 2) Add `ON DELETE CASCADE` to `goals.user_id` FK.

#### DB-A03 [P1] Missing Composite Index: tasks (plan_id, user_id, status)
- **File**: `backend/gateway/internal/db/schema.sql` (index section)
- **Description**: The `task_event_consumer.py` frequently queries `SELECT count(*) FROM tasks WHERE plan_id = ? AND user_id = ?` and `SELECT count(*) FROM tasks WHERE plan_id = ? AND user_id = ? AND status = 'COMPLETED'` for goal progress updates. The existing indexes are single-column (`idx_tasks_plan_id`, `idx_tasks_user_id`) and one composite (`idx_tasks_user_status_created_at`). There is no composite index covering `(plan_id, user_id, status)`.
- **Impact**: Full table scan on the tasks table for every task completion/abandon event when computing goal progress. Performance degrades linearly with task count per plan.
- **Fix**: `CREATE INDEX idx_tasks_plan_user_status ON tasks (plan_id, user_id, status);`

#### DB-A04 [P1] Missing Index: goals.plan_id
- **File**: `backend/gateway/internal/db/schema.sql` (index section)
- **Description**: `goals` table has a `plan_id` column with a foreign key to `plans(id)`, but no index exists on it. The task event consumer queries `SELECT * FROM goals WHERE plan_id = ? AND user_id = ?` for every task completion.
- **Impact**: Sequential scan on goals table for every task completion event.
- **Fix**: `CREATE INDEX idx_goals_plan_id ON goals (plan_id);`

#### DB-A05 [P2] Missing Composite Index: notifications (user_id, is_read, created_at)
- **File**: `backend/gateway/internal/db/schema.sql`
- **Description**: The notifications table has individual indexes on `user_id` and `deleted_at` but no composite covering the common query pattern: `SELECT * FROM notifications WHERE user_id = ? AND is_read = false ORDER BY created_at DESC`.
- **Impact**: Suboptimal notification list loading, especially for users with many read notifications.
- **Fix**: `CREATE INDEX idx_notifications_user_read_created ON notifications (user_id, is_read, created_at DESC);`

#### DB-A06 [P2] Missing Composite Index: user_state_snapshots (user_id, snapshot_at DESC)
- **File**: `backend/gateway/internal/db/schema.sql`
- **Description**: Individual indexes exist on `user_id` and `snapshot_at`, but the typical query is `SELECT * FROM user_state_snapshots WHERE user_id = ? ORDER BY snapshot_at DESC LIMIT 1`. A composite index would allow index-only scans.
- **Impact**: State aggregator reads require merging two index results.
- **Fix**: `CREATE INDEX idx_user_state_snapshots_user_snapshot ON user_state_snapshots (user_id, snapshot_at DESC);`

#### DB-A07 [P2] Missing Composite Index: friendships (user_id, status) / (friend_id, status)
- **File**: `backend/gateway/internal/db/schema.sql`
- **Description**: Common queries like "get all accepted friends for user X" need `(user_id, status)` and `(friend_id, status)` composites. Only individual column indexes exist.
- **Impact**: Filter step on status requires re-checking each row from the user_id index.
- **Fix**: `CREATE INDEX idx_friendships_user_status ON friendships (user_id, status); CREATE INDEX idx_friendships_friend_status ON friendships (friend_id, status);`

#### DB-A08 [P2] Missing Composite Index: error_records (user_id, created_at DESC)
- **File**: `backend/gateway/internal/db/schema.sql`
- **Description**: The `error_replan_bridge.py` queries errors by user within time windows (7-day and 30-day lookbacks). No composite index covers `(user_id, created_at DESC)`.
- **Impact**: Error pressure calculations require sorting after index filter.
- **Fix**: `CREATE INDEX idx_error_records_user_created ON error_records (user_id, created_at DESC);`

#### DB-A09 [P3] Duplicate Indexes on friendships Table
- **File**: `backend/gateway/internal/db/schema.sql`
- **Description**: `friendships` has both `idx_friendship_user` and `ix_friendships_user_id` on the same column (`user_id`), and both `idx_friendship_friend` and `ix_friendships_friend_id` on `friend_id`. These are redundant.
- **Impact**: Wasted disk space and slower writes. No correctness issue.
- **Fix**: Remove the older `idx_friendship_*` indexes, keep the `ix_friendships_*` ones.

#### DB-A10 [P3] Mixed Table Owners (postgres vs brsama)
- **File**: `backend/gateway/internal/db/schema.sql` (throughout)
- **Description**: ~70% of tables are owned by `postgres` and ~30% by `brsama`. Newer migrations (accountability, card protocol, Aurora stages) use `brsama`. This is cosmetic in development but can cause permission issues in production if role separation is enforced.
- **Impact**: No functional impact in single-user development. Potential permission errors in production with role-based access.
- **Fix**: Run `ALTER TABLE <table> OWNER TO postgres;` for all `brsama`-owned tables, or standardize on a single owner.

### A2. PostgreSQL Features

#### DB-B01 [P1] HNSW Indexes Missing m and ef_construction Parameters
- **File**: `backend/gateway/internal/db/schema.sql` lines 10000, 10112, 10147, 10588, 11106, 11134
- **Description**: All 6 HNSW vector indexes use default `m` (16) and `ef_construction` (64) parameters. For 1024-dimensional vectors, these defaults may be suboptimal. The indexes also use `vector_cosine_ops` which is correct for similarity search, but the lack of explicit `ef_search` configuration at query time means PostgreSQL defaults are used.
- **Impact**: Suboptimal recall/latency tradeoff for embedding similarity searches. Default parameters may be fine for small datasets but will degrade as data grows.
- **Fix**: 1) Consider setting `m = 32, ef_construction = 128` for production indexes. 2) Set `SET hnsw.ef_search = 100;` at session level for vector queries. 3) Reindex after parameter changes.

#### DB-B02 [P2] No GIN Index on JSONB metadata Columns
- **File**: `backend/gateway/internal/db/schema.sql`
- **Description**: Multiple tables store JSONB `metadata`, `tags`, `source_metadata`, and `preferences` columns. Only `error_records.cognitive_tags` has a GIN index. Tables like `tasks.tags`, `plans.source_metadata`, `goals.metadata`, and `cards.metadata` lack GIN indexes despite being queried for tag/filter operations.
- **Impact**: JSONB containment queries (`@>`) and key existence (`?`) require sequential scans.
- **Fix**: Add GIN indexes on frequently queried JSONB columns: `CREATE INDEX idx_tasks_tags ON tasks USING gin (tags); CREATE INDEX idx_plans_source_metadata ON plans USING gin (source_metadata);`

#### DB-B03 [P2] Apache AGE Graph Schema - No Index Verification
- **File**: `backend/gateway/internal/db/schema.sql` (sparkle_galaxy schema)
- **Description**: The AGE graph has vertex labels (`KnowledgeNode`, `User`) and edge labels (`PREREQUISITE`, `RELATED`, `MASTERED`, `STUDIED`, `STUDIES`, `APPLIES_TO`, `INTERESTED_IN`, `APPLICATION`). AGE internally uses `ag_catalog.agtype` for properties. There are no explicit indexes on graph properties like `mastery` or `name` within vertex labels.
- **Impact**: Graph traversal queries filtering on properties may be slow without property indexes.
- **Fix**: Use `CREATE INDEX ... FOR (label_name) ON (property_name)` syntax for AGE if supported, or ensure application-level caching covers hot graph queries.

#### DB-B04 [P3] Connection Pool NullPool for SQLite Development Mode
- **File**: `backend/app/db/session.py:49-51`
- **Description**: SQLite uses `NullPool` which creates a new connection for every request. This is correct for SQLite but the code path is determined by URL prefix. If `DATABASE_URL` is accidentally set to a SQLite URL in a non-dev environment, connection management will be problematic.
- **Impact**: No issue in normal operation. Only affects misconfigured deployments.
- **Fix**: Add a startup warning when SQLite is detected in non-DEBUG mode.

### A3. Redis & Event Bus

#### DB-C01 [P1] GalaxyEventConsumer Uses Timestamp-Based Consumer Name
- **File**: `backend/app/services/galaxy_event_consumer.py:49`
- **Description**: The consumer name is generated using `f"galaxy-{_utcnow().timestamp()}"`. Every time the consumer restarts, it creates a new consumer name, leaving the old consumer's pending messages unclaimed. While `xautoclaim` in the event bus handles stale messages, the constantly rotating consumer names create orphaned consumers in the consumer group.
- **Impact**: Redis consumer group bloat over time. Pending messages may experience processing delays during restarts until the idle timeout triggers autoclaim.
- **Fix**: Use a stable consumer name like `f"galaxy-{os.getpid()}"` (matching the pattern in `TaskEventConsumer`).

#### DB-C02 [P2] Event Bus Single Stream Architecture
- **File**: `backend/app/core/event_bus.py`
- **Description**: All events flow through a single `sparkle_events` Redis Stream. With 15+ event types and 5+ consumer groups (task_event_consumer, achievement_event_consumer, galaxy_event_consumer, preference_event_consumer, community consumer), all consumers read from the same stream. High-volume event types (e.g., `task.completed`) can cause backpressure on unrelated consumers.
- **Impact**: A burst of task completion events can delay galaxy mastery updates or achievement processing. No functional data loss (events are persisted), but latency increases.
- **Fix**: Consider partitioning high-volume event types into separate streams (e.g., `sparkle_tasks`, `sparkle_galaxy`) while keeping low-volume events in the shared stream.

#### DB-C03 [P2] No Event Ordering Guarantee Across Consumer Groups
- **File**: `backend/app/core/event_bus.py`, `backend/app/services/task_event_consumer.py`
- **Description**: Redis Streams provide ordering within a single consumer group, but there is no cross-consumer ordering. If `task.completed` triggers both the achievement consumer and the galaxy consumer, the galaxy mastery update may complete before the achievement trigger. For goal progress, the `_handle_task_completed` method computes progress inline, which is correct, but the adaptive replanner call happens after multiple async operations.
- **Impact**: Users may see achievement notifications before galaxy updates reflect in the UI. No data corruption, but inconsistent UI states.
- **Fix**: Document the expected ordering semantics. For critical ordering dependencies, use in-process chaining (call B from within A's handler) rather than relying on event bus ordering.

#### DB-C04 [P3] Cache Service Default TTL Inconsistency
- **File**: `backend/app/core/cache.py:31`
- **Description**: `CacheService.default_ttl = 300` (5 minutes) is hardcoded. Some callers use explicit TTLs while others rely on the default. There is no TTL validation (e.g., ensuring user session caches have longer TTLs than search result caches).
- **Impact**: No correctness issue. Potential stale data if callers forget to set explicit TTLs.
- **Fix**: Define TTL constants per cache category (e.g., `SESSION_TTL=3600`, `SEARCH_TTL=60`, `PROFILE_TTL=300`) and use them consistently.

---

## Part B: Cross-Component Integration Paths

### Path 1: Chat Flow (End-to-End)

```
Flutter websocket_chat_service_v2.dart -> Go websocket_proxy.go -> chat_orchestrator.go
-> agent/client.go (gRPC) -> Python agent_grpc_service.py -> orchestrator.py -> llm_service.py
```

#### INT-D01 [P0] StreamChat Missing Context Timeout Propagation
- **File**: `backend/gateway/internal/agent/client.go:349-365`
- **Description**: `StreamChat()` calls `c.currentAPI().StreamChat(outCtx, req)` using the context from the HTTP handler. For streaming responses, this context governs the entire stream lifetime. If the Go-side HTTP handler times out (default 30s configured via `GRPCTimeoutSeconds`), the gRPC stream is cancelled mid-flight, but the Python-side LLM call continues generating until it hits the LLM provider's max_tokens limit. The `retryCtx` on line 362 creates a fresh context but does NOT set a new timeout, meaning the retry inherits the potentially already-expired parent context.
- **Impact**: 1) Wasted LLM tokens when stream is cancelled. 2) Python-side resources (DB sessions, memory) held open after client disconnects. 3) Retry after reconnection may immediately fail due to expired context.
- **Fix**: 1) Create `retryCtx` with a fresh timeout: `retryCtx, cancel := context.WithTimeout(context.Background(), 120*time.Second)`. 2) Python-side should use `asyncio.wait_for()` with a deadline derived from gRPC context metadata. 3) Add `grpc-max-incoming-message-size` configuration.

#### INT-D02 [P1] WebSocket Proxy No Backpressure on Client Disconnect
- **File**: `backend/gateway/internal/handler/websocket_proxy.go`
- **Description**: The `WebSocketProxy` uses a `draining` atomic flag for graceful shutdown, but during normal operation, if the Flutter client disconnects while Python is streaming, the Go-side continues reading from the gRPC stream and attempting to write to a closed WebSocket. The `chat_orchestrator.go` has error checking on WebSocket writes, but the proxy layer between Go WebSocket and Python gRPC does not propagate client disconnect signals back to Python.
- **Impact**: Python gRPC server continues LLM generation for 30-60s after client disconnect. Wasted API costs and server resources.
- **Fix**: 1) Use `context.WithCancel` in Go to detect WebSocket close and cancel the gRPC context. 2) Python's `StreamChat` should respect gRPC context cancellation via `context.cancel()`.

#### INT-D03 [P2] Flutter WebSocket Reconnect Consumer Name Instability
- **File**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart`
- **Description**: The Flutter WebSocket service handles reconnection, but the Go-side `chat_orchestrator.go` uses `activeByUser` map for connection counting. When a client reconnects, the old connection may not be cleaned up before the new one registers, leading to transient per-user connection count inflation.
- **Impact**: May trigger per-user connection limits during rapid reconnects. Self-healing within seconds.
- **Fix**: Add a small grace period in Go's connection cleanup or use Redis-backed connection tracking for multi-instance deployments.

### Path 2: Plan Review Flow

```
Python plan_review_service.py -> orchestrator.py -> Go websocket_proxy.go
-> Flutter websocket_chat_service_v2.dart -> chat_provider.dart -> plan_review_card.dart
```

#### INT-E01 [P1] Plan Review Result Not Propagated to Active Chat Session
- **File**: `backend/app/orchestration/plan_review_service.py`
- **Description**: The plan review service generates a `PlanReviewResult` with a review payload, but the result is pushed to the Flutter client via the WebSocket as a chat message. The `plan_review_card.dart` then calls `PlanReviewGrpcService.submitReview()` directly via gRPC to `AgentService.SubmitPlanReview()`. However, there is no mechanism to correlate the review result back to the active FSM state in the orchestrator if the user takes action on the review card while a new chat turn is in progress. The `plan_review_service` stores the review in Redis but the orchestrator's FSM does not have a `WAITING_FOR_REVIEW` state that blocks new turns.
- **Impact**: User can send new chat messages while a plan review is pending. The review response may conflict with the new conversation state.
- **Fix**: Add an FSM state `WAITING_FOR_PLAN_REVIEW` that queues incoming messages until the review is resolved. Or add a mutex per session for review-state transitions.

#### INT-E02 [P2] Flutter PlanReviewGrpcService Creates New gRPC Channel Per Instance
- **File**: `mobile/lib/features/chat/data/services/plan_review_grpc_service.dart:58-62`
- **Description**: `PlanReviewGrpcService._getClient()` lazily creates a new `ClientChannel` and `AgentServiceClient`. This channel is separate from the main chat WebSocket channel. Each plan review submission creates its own gRPC call with its own timeout and retry logic, independent of the chat flow.
- **Impact**: No functional issue, but: 1) Extra TCP connection for plan reviews. 2) If gRPC server is temporarily down, plan review submission fails silently (no retry UI). 3) The `submitReview` method has no loading state in the UI.
- **Fix**: Consider reusing the gRPC channel or adding explicit retry/loading UI for plan review submissions.

### Path 3: Task Event Flow

```
Flutter task action -> Go handler -> Python consumer -> Multiple subscribers
(achievement, galaxy, profile, replanner, community)
```

#### INT-F01 [P1] TaskEventConsumer Single AsyncSession for Multiple Operations
- **File**: `backend/app/services/task_event_consumer.py:103-206`
- **Description**: `_handle_task_completed` opens a single `AsyncSessionLocal()` context and performs 6+ database operations within it: BehaviorSignalCollector, MetacognitionService, CommunitySignalBridge, AutoFragmentCollector, AdaptiveReplanner, and Goal progress update. If any of these operations fail with a database error (e.g., connection timeout, constraint violation), the entire transaction is rolled back, losing ALL progress from the other operations.
- **Impact**: A failure in goal progress update (e.g., division by zero edge case on line 200 when `total` is 0) rolls back the behavior signal collection, metacognition refresh, and community bridge updates that already succeeded within the same session.
- **Fix**: Use separate sessions for independent operations, or use savepoints (`await db.begin_nested()`) for operations that should be independently committable.

#### INT-F02 [P2] Goal Progress Division by Zero Guard Incomplete
- **File**: `backend/app/services/task_event_consumer.py:200`
- **Description**: `goal.progress = (completed / total) if total and total > 0 else 0.0` -- this guard is correct, but only for `total=0`. If `total` is `None` (no tasks found for plan), the `if total` check catches it. However, the `completed` count query on line 193 uses `Task.status == "completed"` with a string literal instead of `TaskStatus.COMPLETED.value`, which may not match if the enum storage changes.
- **Impact**: Potential incorrect progress calculation if task status storage format changes.
- **Fix**: Use `Task.status == TaskStatus.COMPLETED.value` or `Task.status == "COMPLETED"` consistently.

### Path 4: Profile Update -> Plan Adaptation

```
Behavioral signal -> CognitiveService -> BehaviorPattern -> AdaptiveReplanner
```

#### INT-G01 [P2] BehaviorPattern Model Lacks Confidence Score Column
- **File**: `backend/app/models/cognitive.py`
- **Description**: The `BehaviorPattern` model stores pattern data but the schema.sql `behavior_patterns` table does not include a confidence score column. The `dual_core_router.py` references behavioral confidence for routing decisions, but this data may not be persisted, relying on in-memory or Redis-only storage.
- **Impact**: Behavioral confidence is lost on service restart. Routing decisions reset to defaults.
- **Fix**: Verify if confidence is stored in Redis only. If so, document the data loss window. If persisted elsewhere, verify the column exists.

### Path 5: Error Creation -> ErrorReplanBridge -> Plan Adjustment

```
ErrorRecord created -> ErrorReplanBridge -> AdaptiveReplanner -> PlanAdjustmentApplier
```

#### INT-H01 [P1] ErrorReplanBridge Ignores Non-TRIGGERING_ERROR_TYPES Silently
- **File**: `backend/app/services/error_replan_bridge.py:82-97`
- **Description**: `TRIGGERING_ERROR_TYPES` is a hardcoded set of 13 error types. Errors with types not in this set (e.g., any new error type added by AI analysis) are silently ignored by the bridge. The `REPLAN_ELIGIBLE_ERROR_TYPES` further narrows this to 11 types (excluding `careless_error` and `reading_careless`). There is no logging or metric for skipped error types.
- **Impact**: New error types introduced by AI analysis improvements will not trigger plan adjustments until manually added to the set. No observability into missed triggers.
- **Fix**: 1) Add a metric counter for non-triggering error types. 2) Log at DEBUG level when an error type is skipped. 3) Consider making this configurable via Redis/database rather than hardcoded.

### Path 6: Community Signal Bridge

```
Community events -> community_signal_bridge.py -> StateAggregator -> DualCoreRouter
```

#### INT-I01 [P2] CommunitySignalBridge Privacy Forbids Nickname in Aurora Context
- **File**: `backend/app/services/community_signal_bridge.py:60-66`
- **Description**: `AURORA_FORBIDDEN_SOCIAL_KEYS` includes `nickname`, which means the bridge strips nickname from social events before passing to Aurora. This is correct for privacy, but it means Aurora's tone adaptation cannot use the user's name for personalization when responding about community interactions. The `sanitize_for_aurora_context` method returns `None` for self-actions (line 99-100), which means users never see their own community contributions reflected in AI responses.
- **Impact**: AI responses about community interactions are generic (no names). This is a privacy-by-design choice, but may feel impersonal.
- **Fix**: Consider allowing anonymized role labels (e.g., "your study partner") instead of complete stripping. This is a product decision, not a bug.

### Path 7: Achievement Flow

```
Task completed -> AchievementEventConsumer -> AchievementEngine -> Notifications
```

#### INT-J01 [P2] AchievementEventConsumer Skips Group-Sourced Tasks
- **File**: `backend/app/services/achievement_event_consumer.py:96-97`
- **Description**: `_handle_task_completed` immediately returns if `source == "group"`, meaning group-completed tasks do not trigger personal achievements. This is intentional to prevent double-counting, but there is no separate handler for group task achievements. The `_handle_group_task_completed` method exists (line 78-79) but only for `community.group_task_completed` events, which is a different event type than `task.completed`.
- **Impact**: Group task completions may not trigger any achievement processing if the event routing uses `task.completed` with `source=group` rather than `community.group_task_completed`.
- **Fix**: Verify that group task completions emit BOTH event types, or adjust the consumer to process `task.completed` with `source=group` through the group-specific handler.

---

## Part C: Proto Contract Verification

#### PROTO-C01 [P1] Community Service Proto Marked Deprecated But Still Referenced
- **File**: `proto/community_service.proto:323-324`
- **Description**: The `CommunityService` is marked `option deprecated = true;` with a comment saying "Sparkle community features are served by REST/gateway CQRS. This proto is retained only as compatibility documentation and must not be used as a live Python gRPC contract." However, the generated Python files may still exist and could be accidentally imported.
- **Impact**: Risk of developers accidentally implementing against the deprecated service definition.
- **Fix**: 1) Verify no Python code imports `community_service_pb2_grpc`. 2) Add a linter rule or CI check to prevent imports of deprecated proto services.

#### PROTO-C02 [P2] Proto Field Number Gaps and Reserved Fields
- **File**: `proto/agent_service.proto`
- **Description**: `ChatResponse` has field 13 reserved with `reserved "timestamp"`, and field 9 maps to `finish_reason`. The field numbers skip 10->15->16->17 for metadata fields. This is correct proto3 practice (reserved fields prevent wire-format incompatibility), but the large gaps suggest significant proto evolution.
- **Impact**: No immediate issue. Proto evolution is well-managed with reserved fields.
- **Fix**: None required. Current practice is correct.

#### PROTO-C03 [P2] WebSocket Proto Imports Agent Proto - Cross-Package Dependency
- **File**: `proto/websocket.proto:7`
- **Description**: `websocket.proto` imports `agent_service.proto` for the `ToolCall` message type used in `ChatMessage.tool_calls`. This creates a cross-package dependency between the `sparkle.ws` and `agent.v1` packages.
- **Impact**: Changes to `agent_service.proto.ToolCall` affect both the agent gRPC service and the WebSocket protocol. Breaking changes propagate across service boundaries.
- **Fix**: Consider extracting shared message types (like `ToolCall`) into a common proto package to reduce coupling.

---

## Appendix: Statistics

- **Total Tables**: 246 (including AGE graph tables in sparkle_galaxy schema)
- **Total Indexes**: 325
- **Total Foreign Keys**: 1071
- **Total Alembic Migrations**: 18 migration files
- **Merge Migrations**: 17 (indicating significant parallel development)
- **HNSW Vector Indexes**: 6 (cognitive_fragments, document_chunks, episodic_memories, knowledge_nodes, scenes, seed_items)
- **Embedding Columns**: 6 (all vector(1024))
- **Proto Files**: 8 (agent_service, community_service, error_book, galaxy_service, stt_service, user_state, websocket, + sparkle/)

### Key Files Examined

| File | Lines Read |
|------|-----------|
| `backend/gateway/internal/db/schema.sql` | 700+ |
| `proto/agent_service.proto` | 783 (full) |
| `proto/websocket.proto` | 108 (full) |
| `proto/galaxy_service.proto` | 194 (full) |
| `proto/community_service.proto` | 422 (full) |
| `proto/error_book.proto` | 216 (full) |
| `proto/stt_service.proto` | 230 (full) |
| `proto/user_state.proto` | 329 (full) |
| `backend/app/core/event_bus.py` | 1495 (full) |
| `backend/app/services/task_event_consumer.py` | 504 (full) |
| `backend/app/services/achievement_event_consumer.py` | 100 |
| `backend/app/services/community_signal_bridge.py` | 100 |
| `backend/app/services/error_replan_bridge.py` | 100 |
| `backend/app/services/agent_grpc_service.py` | 150 |
| `backend/app/db/session.py` | 194 (full) |
| `backend/app/core/cache.py` | 100 |
| `backend/gateway/internal/agent/client.go` | 400 |
| `backend/gateway/internal/handler/websocket_proxy.go` | 100 |
| `backend/gateway/internal/handler/chat_orchestrator.go` | 100 |
| `backend/app/models/__init__.py` | 584 (full) |
| `backend/app/models/goal.py` | 50 |
| `backend/app/models/task.py` | 60 |
| `backend/app/models/plan.py` | 30 |
| `backend/app/models/achievement.py` | 25 |
| `backend/app/orchestration/plan_review_service.py` | 100 |
| `backend/app/orchestration/adaptive_replanner.py` | 80 |
