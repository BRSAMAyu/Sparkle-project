# Backend & Gateway Full-Stack Deep Audit Report

**Date**: 2026-05-10
**Auditor**: Claude Agent (Deep Code Audit)
**Scope**: Python Engine (`backend/app/`) + Go Gateway (`backend/gateway/`)
**Files Reviewed**: 25+ source files across orchestration, agents, services, models, gateway handler, agent client, scripts, tests

---

## Executive Summary

**Total Issues Found**: 35

| Severity | Count |
|----------|-------|
| P0 - Critical | 4 |
| P1 - High | 9 |
| P2 - Medium | 14 |
| P3 - Low | 8 |

**Top Risks**:
1. Fire-and-forget `asyncio.create_task()` calls in `plan_review_service.py` silently swallow exceptions from DB writes and LLM calls.
2. `PlanReviewService` accesses `self.redis` without null guards, causing `AttributeError` when Redis is unavailable.
3. Kill switch `read_mode` silently falls back to permissive mode on Redis failure.
4. Conflicting `ResponseFeedback` import in `models/__init__.py` binds the wrong class.
5. Go WebSocket proxy `closeConnections` panic can bypass recovery.

---

## Part A: Python Engine

### 1. Orchestration Core

#### P0-01: `plan_review_service.py` -- Fire-and-forget tasks with no exception tracking

**File**: `backend/app/orchestration/plan_review_service.py`
**Lines**: 1934, 1942, 2216
**Severity**: P0 -- Critical

Three `asyncio.create_task()` calls are made without storing references or adding done-callbacks. The tasks `_generate_tasks_after_approval`, `_capture_plan_goal_memory`, and `_execute_replan_action` perform DB writes and gRPC calls. If any raises, the exception is silently destroyed by the event loop. The `ChatOrchestrator` already has a `_bg_tasks: set[asyncio.Task]` pattern, but `PlanReviewService` does not.

```python
# Line 1934
asyncio.create_task(
    self._generate_tasks_after_approval(
        plan_id=plan_id, user_id=user_id, ...
    )
)
# Line 1942
asyncio.create_task(
    self._capture_plan_goal_memory(
        plan_id=plan_id, user_id=user_id, ...
    )
)
```

**Suggested Fix**: Store tasks in a `_bg_tasks: set[asyncio.Task]` set, add a done-callback that logs exceptions, and periodically clean up completed tasks.

---

#### P0-02: `plan_review_service.py` -- `self.redis` accessed without null guard

**File**: `backend/app/orchestration/plan_review_service.py`
**Lines**: 2428-2431, 2446, 2469
**Severity**: P0 -- Critical

`track_rejection_count` and `reset_rejection_count` access `self.redis` directly without null checks. If the service is used before `set_redis()` is called, or if Redis disconnects, `self.redis` is `None` and raises `AttributeError`. The method `_trigger_information_collection` has a `if self.redis:` guard but the rejection tracking methods do not.

```python
async def track_rejection_count(self, plan_id: str, user_id: str) -> int:
    key = f"plan_rejection_count:{plan_id}:{user_id}"
    try:
        count = await self.redis.incr(key)  # Crashes if self.redis is None
```

**Suggested Fix**: Add `if not self.redis: return 1` guard at the top of both methods.

---

#### P1-01: `plan_review_service.py` -- Replan timeout too short (10s) for LLM planning

**File**: `backend/app/orchestration/plan_review_service.py`
**Lines**: 2297-2304
**Severity**: P1 -- High

The replan action wraps `planner.plan()` in `asyncio.wait_for(..., timeout=10.0)`. The LLM planning step involves at least one LLM call and possible tool calls, which routinely exceed 10 seconds under load. The fallback plan is generated but loses all LLM-derived context.

**Suggested Fix**: Increase timeout to 30s or make it configurable via settings.

---

#### P1-02: `orchestrator.py` -- OpenTelemetry span may leak on generator abandonment

**File**: `backend/app/orchestration/orchestrator.py`
**Line**: ~2013
**Severity**: P1 -- High

The `span = tracer.start_span(...)` is ended in a `finally` block. If the async generator is abandoned mid-yield by the gRPC caller (client disconnect), the generator finalizer may not run the `finally` block immediately, leaving the span open indefinitely.

**Suggested Fix**: Add `span.end()` inside a `try/finally` wrapper around each `yield` and in the generator's `aclose` path.

---

#### P1-03: `orchestrator.py` -- Lock acquisition exception leaves ambiguous state

**File**: `backend/app/orchestration/orchestrator.py`
**Lines**: ~2053-2083
**Severity**: P1 -- High

`lock_renewal_task` and `lock_renewal_stop` are initialized to `None`. If `_acquire_session_lock` raises (rather than returning False), `lock_acquired` stays `False` while the lock may have been partially acquired in Redis. The `finally` block skips release because `lock_acquired` is `False`.

**Suggested Fix**: Make `_acquire_session_lock` atomic (SETNX + short TTL in a single Redis call) and ensure `lock_acquired` is only set True after confirmed ownership.

---

#### P2-01: `orchestrator.py` -- `locals()` fallback in error handler is fragile

**File**: `backend/app/orchestration/orchestrator.py`
**Lines**: ~3617-3625
**Severity**: P2 -- Medium

The `except` block uses `locals()` to check for `user_message`, `request_extra_context`, etc. If the exception occurs before those variables are assigned, `locals()` returns `None` for all of them, producing empty error context.

**Suggested Fix**: Initialize all context variables at the top of `process_stream` with default values.

---

#### P2-02: `orchestrator.py` -- `datetime.now()` vs UTC inconsistency

**File**: `backend/app/orchestration/orchestrator.py`
**Lines**: ~1262, 2068
**Severity**: P2 -- Medium

`int(datetime.now().timestamp())` is used for `created_at` fields. `datetime.now()` returns local time which may not match UTC timestamps used elsewhere (`_utcnow()` helper). In production across timezones, this creates inconsistency.

**Suggested Fix**: Replace all `datetime.now()` with `datetime.now(UTC)` or use the `_utcnow()` helper consistently.

---

### Dual-Core Router

#### P2-03: `dual_core_router.py` -- Monolithic `route()` method

**File**: `backend/app/orchestration/dual_core_router.py`
**Lines**: 205-863
**Severity**: P2 -- Medium

The `route()` method is ~660 lines with deeply nested conditionals, making individual decision paths difficult to unit test. All three return paths (`execution_first`, `cognitive_first`, `balanced`) are embedded inline.

**Suggested Fix**: Extract signal scoring, cognitive adjustments, and execution constraints into separate methods.

---

### Plan Review Service (continued)

#### P2-04: `plan_review_service.py` -- Hardcoded "liberal_arts" detection

**File**: `backend/app/orchestration/plan_review_service.py`
**Lines**: 942-959
**Severity**: P2 -- Medium

The feasibility check explicitly checks `user_background == "liberal_arts"` and hardcodes specific technical keywords ("爬虫", "web开发"). This is brittle and culturally narrow. Line 898 calls `params.get("type")` but discards the result.

**Suggested Fix**: Use a configurable mapping of backgrounds to risk multipliers.

---

#### P2-05: `plan_review_service.py` -- `get_stored_plan` always returns None

**File**: `backend/app/orchestration/plan_review_service.py`
**Lines**: 1871-1885
**Severity**: P2 -- Medium

The method always returns `None`. Callers from the API layer silently fail to retrieve plans after approval.

**Suggested Fix**: Implement the method to query the plan from database, or remove it and update callers.

---

### 2. Agent System

#### P1-04: `collaboration.py` -- Missing null-check on `stream_cb`

**File**: `backend/app/agents/graph/nodes/collaboration.py`
**Lines**: 827-828
**Severity**: P1 -- High

`stream_cb = get_stream_callback(config)` may return `None`. The code passes `stream_cb` to `_emit_initial_agent_states`, `_execute_agents_parallel`, etc., which call `await emit_agent_activity(stream_cb, ...)`. If `stream_cb` is `None`, this may raise `TypeError`.

**Suggested Fix**: Add a guard: `if stream_cb is None: stream_cb = lambda *a, **k: asyncio.sleep(0)` or check inside `emit_agent_activity`.

---

#### P2-06: `collaboration.py` -- Unguarded LLM call in parallel merge

**File**: `backend/app/agents/graph/nodes/collaboration.py`
**Lines**: 615-641
**Severity**: P2 -- Medium

When parallel results succeed, the code invokes `LLMFactory.get_llm("aggregator")` to merge outputs. This is an untracked LLM call with no token budget check, no timeout, and no fallback. If the aggregator LLM fails, the entire parallel collaboration returns without merged output.

**Suggested Fix**: Wrap the LLM call in try/except with a fallback that concatenates agent outputs without merging.

---

#### P2-07: `collaboration.py` -- No timeouts on debate LLM calls

**File**: `backend/app/agents/graph/nodes/collaboration.py`
**Lines**: 657-658, 717-718
**Severity**: P2 -- Medium

The debate flow makes 2 + N LLM calls (N for round 1, N for review, 1 judge) with no individual timeout. A single slow LLM call blocks the entire debate pipeline.

**Suggested Fix**: Add `asyncio.wait_for` timeouts (60s) on each LLM invocation.

---

#### P2-08: `workflow.py` -- Planning graph singleton not thread-safe

**File**: `backend/app/agents/graph/workflow.py`
**Lines**: 327-340
**Severity**: P2 -- Medium

`_planning_graph` is a module-level global initialized lazily by `get_planning_graph()`. Two concurrent coroutines may both see `None` and create two graphs simultaneously.

**Suggested Fix**: Use `functools.lru_cache(maxsize=1)` or a threading lock to ensure single initialization.

---

#### P2-09: `workflow.py` -- `route_after_agent` accesses `state["messages"][-1]` without empty-check

**File**: `backend/app/agents/graph/workflow.py`
**Lines**: 51-52
**Severity**: P2 -- Medium

`last_message = state["messages"][-1]` will raise `IndexError` if `messages` is empty. A malformed state could trigger this.

**Suggested Fix**: Add a guard: `if not state.get("messages"): return END`.

---

### 3. Services

#### P0-03: `llm_service.py` -- Demo mode fuzzy match returns irrelevant responses for short messages

**File**: `backend/app/services/llm_service.py`
**Lines**: 494-496
**Severity**: P0 -- Critical

The fuzzy matching logic `if key in user_content or user_content in key` matches trivially short strings. If a user sends "我", it matches "我今天要学什么" because `"我" in "我今天要学什么"`. Short messages get completely irrelevant preset responses.

**Suggested Fix**: Require a minimum overlap ratio (e.g., `len(match) / max(len(user_content), 1) > 0.5`) or remove the fuzzy match entirely.

---

#### P1-05: `llm_service.py` -- `build_prompt_with_seed_examples` leaks database session

**File**: `backend/app/services/llm_service.py`
**Lines**: 1627-1659
**Severity**: P1 -- High

When `db is None`, a new database session is acquired via `get_db()` async generator (`db = await db_gen.__anext__()`). The `finally` block contains `pass` with a comment "db is from get_db(), don't close". The session is never closed or returned to the pool, causing connection pool exhaustion over time.

```python
if db is None:
    db_gen = get_db()
    db = await db_gen.__anext__()
# ... use db ...
finally:
    pass  # LEAK: session never closed
```

**Suggested Fix**: Use `async with get_db() as db:` context manager, or call `await db_gen.aclose()` in the finally block.

---

#### P1-06: `llm_service.py` -- `_parse_json_payload` returns `None` after successful LLM call

**File**: `backend/app/services/llm_service.py`
**Lines**: 870-881, 897-916
**Severity**: P1 -- High

`reason_json` and `chat_json` call their respective methods then parse JSON. If the LLM returns valid text that is not JSON, `_parse_json_payload` returns `None`. Callers like `_llm_review` check `if not result or not isinstance(result, dict)` but retry as generic exceptions, wasting LLM calls.

**Suggested Fix**: Return a structured error dict instead of `None` from `_parse_json_payload`, or raise a specific exception type.

---

#### P2-10: `llm_service.py` -- Token tracking silently fails on Redis errors

**File**: `backend/app/services/llm_service.py`
**Lines**: 176-193
**Severity**: P2 -- Medium

All Redis errors in `_track_daily_user_tokens` are caught by a bare `except Exception` with only a debug log. If Redis is down, token tracking silently fails, and users may exceed their daily quota without detection.

**Suggested Fix**: Increment a Prometheus counter when Redis tracking fails so operators are alerted.

---

#### P2-11: `agent_grpc_service.py` -- DB commit after generator exhaustion

**File**: `backend/app/services/agent_grpc_service.py`
**Lines**: ~329-333
**Severity**: P2 -- Medium

`await db_session.commit()` runs after the `async for response in self.orchestrator.process_stream(...)` generator is fully exhausted. If the commit fails, the client has already received all responses, creating inconsistency.

**Suggested Fix**: Consider committing per-response for critical mutations, or at least logging commit failures as errors.

---

### 4. Models & Schemas

#### P0-04: `models/__init__.py` -- Conflicting `ResponseFeedback` import

**File**: `backend/app/models/__init__.py`
**Lines**: 197, 251, 579
**Severity**: P0 -- Critical

`ResponseFeedback` is imported from both `app.models.response_feedback` (line 197) and `app.models.workflow_conversation` (line 251, inside try block). The second import silently overwrites the first. Code that does `from app.models import ResponseFeedback` gets the wrong class depending on whether the workflow_conversation module is available.

**Suggested Fix**: Alias one of them (e.g., `WorkflowResponseFeedback`) or remove the duplicate.

---

#### P2-12: `models/__init__.py` -- Swallowed ImportErrors hide real issues

**File**: `backend/app/models/__init__.py`
**Lines**: 225-228, 237-257
**Severity**: P2 -- Medium

Two import blocks use try/except ImportError to handle missing modules, silently hiding circular imports or missing dependencies during development.

**Suggested Fix**: At minimum, log a warning when these imports fail.

---

#### P2-13: `models/cognitive.py` -- No check constraint on severity range

**File**: `backend/app/models/cognitive.py`
**Line**: 69
**Severity**: P2 -- Medium

`severity = Column(Integer, default=1, nullable=False)` comment says "1-5" but no `CheckConstraint` enforces this. Values outside 1-5 can be inserted.

**Suggested Fix**: Add `CheckConstraint('severity >= 1 AND severity <= 5', name='ck_cognitive_fragment_severity_range')` to `__table_args__`.

---

#### P2-14: `models/error_book.py` -- Uses `Base` instead of `BaseModel`

**File**: `backend/app/models/error_book.py`
**Line**: 19
**Severity**: P2 -- Medium

`ErrorRecord` inherits from `Base` (from `app.db.session`) instead of `BaseModel` (from `app.models.base`). `BaseModel` provides `id`, `created_at`, `updated_at` columns automatically. If `BaseModel` adds common functionality, `ErrorRecord` will miss it.

**Suggested Fix**: Verify this is intentional; if so, add a comment explaining why.

---

#### P3-01: `models/error_book.py` -- `next_review_at` defaults to now

**File**: `backend/app/models/error_book.py`
**Line**: 46
**Severity**: P3 -- Low

`next_review_at = Column(DateTime(timezone=True), server_default=func.now())` means newly created error records are immediately due for review. For spaced repetition, the first review should typically be in the future.

**Suggested Fix**: Remove server_default and set explicitly in the service layer.

---

### 5. State Aggregation & Aurora

#### P1-07: `kill_switch.py` -- `read_mode` falls back to settings on Redis failure without logging

**File**: `backend/app/core/kill_switch.py`
**Lines**: 94-112
**Severity**: P1 -- High (Security)

If `redis_client.get()` raises an exception (e.g., connection error), it is not caught at line 103. Callers that do not wrap `read_mode` in try/except will crash. If they do handle it, the kill switch silently falls back to the settings-based mode, which may be "live" for a feature that should be "off".

**Suggested Fix**: Wrap the Redis call in `read_mode` with try/except, log a warning on failure, and fall back to the most restrictive mode ("off").

---

#### P1-08: `kill_switch.py` -- `write_mode` mutates in-memory settings when Redis is None

**File**: `backend/app/core/kill_switch.py`
**Lines**: 128-132
**Severity**: P1 -- High

When `redis_client is None`, `write_mode` calls `setattr(settings, ...)` to modify the global settings object in-memory. This is not thread-safe and mutates global state visible to all concurrent requests.

**Suggested Fix**: Remove the in-memory settings mutation path. Kill switch writes should fail with a clear error if Redis is unavailable.

---

#### P2-15: `state_aggregator/service.py` -- In-memory cache has no eviction

**File**: `backend/app/state_aggregator/service.py`
**Lines**: 110-113
**Severity**: P2 -- Medium

`self._cache` stores field envelopes with timestamps but old entries are never removed. Over time with many users, this cache grows without bound.

**Suggested Fix**: Add periodic cleanup of expired entries or use an LRU cache with max size.

---

### 6. Scripts

#### P3-02: `local_signoff_preflight.py` -- No gRPC server health check

**File**: `backend/scripts/local_signoff_preflight.py`
**Lines**: ~217
**Severity**: P3 -- Low

The preflight checks backend health at port 8000 and gateway at 8080, but does not check the Python gRPC server at 50051. A common failure mode is gRPC server down while FastAPI is up.

**Suggested Fix**: Add a TCP socket check on port 50051.

---

### 7. Tests

#### P1-09: `test_accountability_system_api.py` -- `_FakeRedis` missing critical methods

**File**: `backend/tests/api/test_accountability_system_api.py`
**Lines**: 66-81
**Severity**: P1 -- High

`_FakeRedis` only implements `get`, `setex`, and `set`. Missing: `incr`, `expire`, `delete`, `ttl`, `publish`, `incrby`. If tested code calls any of these, it raises `AttributeError`. Tests pass only because these code paths are not exercised.

**Suggested Fix**: Add stub implementations for all used Redis methods, or use `fakeredis`.

---

#### P3-03: `test_accountability_system_api.py` -- Uses deprecated `datetime.utcnow()`

**File**: `backend/tests/api/test_accountability_system_api.py`
**Lines**: 227, 229, 230, 424+
**Severity**: P3 -- Low

`datetime.utcnow()` is deprecated since Python 3.12. The main codebase uses `_utcnow()` helper but tests do not.

**Suggested Fix**: Replace with `datetime.now(UTC)`.

---

#### P2-16: `test_accountability_system_api.py` -- No test for concurrent partnership race

**File**: `backend/tests/api/test_accountability_system_api.py`
**Severity**: P2 -- Medium

Tests cover sequential flows but not race conditions like two users requesting partnership with the same user simultaneously.

**Suggested Fix**: Add a concurrent request test verifying only one succeeds.

---

## Part B: Go Gateway

### 1. WebSocket Handler

#### P0-05: `websocket_proxy.go` -- Panic in `closeConnections` bypasses recovery

**File**: `backend/gateway/internal/handler/websocket_proxy.go`
**Lines**: 335-358
**Severity**: P0 -- Critical

`closeConnections` uses `closeOnce.Do` for cleanup. If a panic occurs inside `writeMessage` within `closeConnections`, it bypasses `recoverProxyGoroutine` because `closeConnections` is called from within the recovery handler itself. This could crash the proxy goroutine without proper cleanup.

**Suggested Fix**: Add `defer func() { if r := recover(); r != nil { ... } }()` inside `closeConnections`.

---

#### P1-10: `websocket_proxy.go` -- Backend connection opened before client upgrade

**File**: `backend/gateway/internal/handler/websocket_proxy.go`
**Lines**: 226-241
**Severity**: P1 -- High

The proxy dials the backend first, then upgrades the client. If the client upgrade fails, the backend connection is already established but only cleaned up by defer. Under high load, failed client upgrades create unnecessary backend connections.

**Suggested Fix**: Consider upgrading the client first, then dialing the backend. This saves backend resources on failed upgrades.

---

#### P1-11: `websocket_proxy.go` -- `reconnectTrackers` grows unboundedly

**File**: `backend/gateway/internal/handler/websocket_proxy.go`
**Line**: 103 (cleanup goroutine)
**Severity**: P1 -- High

`startReconnectTrackerCleanup()` runs every 300s and only removes trackers where `blockedUntil` has passed. Trackers for users who connected successfully and never reconnected (no `blockedUntil`) are never cleaned up. Over time, `reconnectTrackers` grows without bound.

**Suggested Fix**: Also remove trackers where `lastAttempt` is older than a threshold (e.g., 24 hours).

---

#### P2-17: `websocket_proxy.go` -- No URL validation in `toWebSocketURL`

**File**: `backend/gateway/internal/handler/websocket_proxy.go`
**Lines**: 562-579
**Severity**: P2 -- Medium

The function accepts any URL including those with user:pass, query parameters, and fragments. No validation is performed on the host or port.

**Suggested Fix**: Add validation to reject URLs with unexpected schemes or missing host.

---

#### P2-18: `websocket_proxy.go` -- Oversized message check redundant with `SetReadLimit`

**File**: `backend/gateway/internal/handler/websocket_proxy.go`
**Lines**: 379-385
**Severity**: P2 -- Medium (code clarity)

Manual `if len(data) > int(readLimit)` check after `ReadMessage()` is redundant with `clientConn.SetReadLimit(readLimit)` at line 292, which already causes ReadMessage to return an error for oversized messages. The backend-side check (line 444) is valid.

**Suggested Fix**: Remove the redundant client-side check or add a comment explaining it's defense-in-depth.

---

#### P3-04: `websocket_proxy.go` -- `Close()` silently abandons in-flight connections

**File**: `backend/gateway/internal/handler/websocket_proxy.go`
**Lines**: 643-656
**Severity**: P3 -- Low

The `Close()` method waits up to 5 seconds then returns `nil` even if goroutines are still running. No logging indicates connections were forcefully abandoned.

**Suggested Fix**: Log a warning when the timeout fires. Make the timeout configurable.

---

### 2. Agent Client

#### P2-19: `client.go` -- Mutex held during `time.Sleep`

**File**: `backend/gateway/internal/agent/client.go`
**Lines**: 189-199
**Severity**: P2 -- Medium

`reconnectMu` is held during `time.Sleep(minGap - elapsed)`. This blocks all other reconnect attempts for the entire sleep duration.

**Suggested Fix**: Use `time.After` or `select` with a context channel. Acquire the mutex only for the state check and update.

---

#### P2-20: `client.go` -- Double retry (gRPC service config + manual reconnect)

**File**: `backend/gateway/internal/agent/client.go`
**Lines**: 349-366
**Severity**: P2 -- Medium

`StreamChat` attempts reconnection once on failure, combined with the gRPC retry policy (MaxAttempts: 4). This can result in up to 8 total attempts for streaming RPCs, which may be excessive.

**Suggested Fix**: Consider whether manual reconnect is still needed given the gRPC retry policy, or disable service-level retry for streaming.

---

#### P2-21: `client.go` -- `StreamChat` retry uses stale context timeout

**File**: `backend/gateway/internal/agent/client.go`
**Lines**: 362-363
**Severity**: P2 -- Medium

After reconnect, `retryCtx := c.injectMetadata(ctx, req.UserId)` re-injects metadata but uses the original `ctx` which has reduced deadline due to elapsed time during the first attempt and reconnect.

**Suggested Fix**: Create a new context with fresh timeout for the retry: `retryCtx, cancel := context.WithTimeout(ctx, freshTimeout)`.

---

#### P3-05: `client.go` -- No timeout on streaming RPC initiation

**File**: `backend/gateway/internal/agent/client.go`
**Line**: 352
**Severity**: P3 -- Low

`c.currentAPI().StreamChat(outCtx, req)` uses the caller's context without a specific timeout. A hung stream could last indefinitely.

**Suggested Fix**: Add `context.WithTimeout` for the initial StreamChat call.

---

### 3. Auth & Middleware

#### P2-22: `websocket_proxy.go` -- SHA-256 without salt for user ID hashing

**File**: `backend/gateway/internal/handler/websocket_proxy.go`
**Line**: 598
**Severity**: P2 -- Medium

User IDs are hashed with plain SHA-256 for logging. Since user IDs are UUIDs (low entropy), a rainbow table attack could reverse these hashes.

**Suggested Fix**: Use HMAC-SHA256 with a configured secret key, or use truncated hash.

---

### 4. API Endpoints

#### P1-12: `chat_orchestrator.go` -- `chatInput` pool objects may not be returned

**File**: `backend/gateway/internal/handler/chat_orchestrator.go`
**Lines**: 99-117
**Severity**: P1 -- High

The `chatInputPool` sync.Pool has `Get`/`New` and `Reset()` but no visible `Put()` call in the first 200 lines. Recycled objects may never be returned to the pool, defeating the purpose. If future fields are added without updating `Reset()`, data could leak between requests.

**Suggested Fix**: Ensure `chatInput` objects are returned via `chatInputPool.Put(input)` after processing.

---

## Issue Summary Table

| ID | Severity | File | Line(s) | Description |
|----|----------|------|---------|-------------|
| P0-01 | Critical | `plan_review_service.py` | 1934,1942,2216 | Fire-and-forget tasks without tracking |
| P0-02 | Critical | `plan_review_service.py` | 2428-2431 | Redis null guard missing |
| P0-03 | Critical | `llm_service.py` | 494-496 | Demo mode fuzzy match on short strings |
| P0-04 | Critical | `models/__init__.py` | 197,251,579 | Conflicting ResponseFeedback import |
| P0-05 | Critical | `websocket_proxy.go` | 335-358 | Panic bypasses recovery in closeConnections |
| P1-01 | High | `orchestrator.py` | ~2013 | OTel span leak on generator abandonment |
| P1-02 | High | `orchestrator.py` | ~2053-2083 | Lock acquisition ambiguous state |
| P1-03 | High | `plan_review_service.py` | ~2297 | 10s timeout too short for LLM planning |
| P1-04 | High | `collaboration.py` | 827-828 | Missing null-check on stream_cb |
| P1-05 | High | `llm_service.py` | 1627-1659 | DB session leak in seed examples |
| P1-06 | High | `llm_service.py` | 870-881 | JSON parse returns None |
| P1-07 | High | `kill_switch.py` | 94-112 | Redis failure falls back to unsafe mode |
| P1-08 | High | `kill_switch.py` | 128-132 | write_mode mutates global settings |
| P1-09 | High | `test_accountability...py` | 66-81 | _FakeRedis missing methods |
| P1-10 | High | `websocket_proxy.go` | 226-241 | Backend connection before client upgrade |
| P1-11 | High | `websocket_proxy.go` | 103 | reconnectTrackers unbounded growth |
| P1-12 | High | `chat_orchestrator.go` | 99-117 | chatInput pool objects not returned |
| P2-01 | Medium | `orchestrator.py` | ~3617 | locals() fallback fragile |
| P2-02 | Medium | `orchestrator.py` | ~1262,2068 | datetime.now() vs UTC |
| P2-03 | Medium | `dual_core_router.py` | 205-863 | Monolithic route() method |
| P2-04 | Medium | `plan_review_service.py` | 942-959 | Hardcoded liberal_arts detection |
| P2-05 | Medium | `plan_review_service.py` | 1871-1885 | get_stored_plan returns None |
| P2-06 | Medium | `collaboration.py` | 615-641 | Unguarded LLM call in merge |
| P2-07 | Medium | `collaboration.py` | 657-718 | No timeouts on debate LLM |
| P2-08 | Medium | `workflow.py` | 327-340 | Singleton not thread-safe |
| P2-09 | Medium | `workflow.py` | 51-52 | Missing empty-check on messages |
| P2-10 | Medium | `llm_service.py` | 176-193 | Token tracking silently fails |
| P2-11 | Medium | `agent_grpc_service.py` | ~329 | DB commit after generator exhaustion |
| P2-12 | Medium | `models/__init__.py` | 225-257 | Swallowed ImportErrors |
| P2-13 | Medium | `cognitive.py` | 69 | No severity check constraint |
| P2-14 | Medium | `error_book.py` | 19 | Uses Base instead of BaseModel |
| P2-15 | Medium | `state_aggregator/service.py` | 110-113 | Cache has no eviction |
| P2-16 | Medium | `test_accountability...py` | -- | No concurrent partnership test |
| P2-17 | Medium | `websocket_proxy.go` | 562-579 | No URL validation |
| P2-18 | Medium | `websocket_proxy.go` | 379-385 | Redundant size check |
| P2-19 | Medium | `client.go` | 189-199 | Mutex held during Sleep |
| P2-20 | Medium | `client.go` | 349-366 | Double retry interaction |
| P2-21 | Medium | `client.go` | 362-363 | Stale context on retry |
| P2-22 | Medium | `websocket_proxy.go` | 598 | SHA-256 without salt |
| P3-01 | Low | `error_book.py` | 46 | next_review_at defaults to now |
| P3-02 | Low | `local_signoff_preflight.py` | ~217 | No gRPC health check |
| P3-03 | Low | `test_accountability...py` | 227+ | Deprecated utcnow() |
| P3-04 | Low | `websocket_proxy.go` | 643-656 | Close silently abandons connections |
| P3-05 | Low | `client.go` | 352 | No timeout on stream init |

---

## Priority Fix Recommendations

1. **P0-02** (1 hour): Add `if not self.redis` guards to `track_rejection_count` and `reset_rejection_count`.
2. **P0-04** (30 min): Alias the duplicate `ResponseFeedback` import in `models/__init__.py`.
3. **P0-01** (2 hours): Add `_bg_tasks` tracking set to `PlanReviewService` with done-callback logging.
4. **P0-05** (1 hour): Add panic recovery inside `closeConnections` in `websocket_proxy.go`.
5. **P0-03** (30 min): Tighten demo mode fuzzy matching with minimum overlap ratio.
6. **P1-07** (1 hour): Add try/except in `kill_switch.read_mode` with restrictive fallback.
7. **P1-05** (2 hours): Fix `build_prompt_with_seed_examples` DB session leak.
8. **P1-11** (1 hour): Add 24-hour eviction to reconnectTracker cleanup.
9. **P1-12** (1 hour): Ensure chatInput pool objects are returned after processing.

---

*Report generated by automated deep audit. All findings should be verified by a human before prioritizing fixes.*
