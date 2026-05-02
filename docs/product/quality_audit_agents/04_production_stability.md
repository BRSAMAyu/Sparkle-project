# Quality Audit Agent Report: 04_production_stability

Agent ID: a09e7c9a014aee68e

I'll conduct a thorough audit of Sparkle's production stability and resilience across the three dimensions. Let me start by exploring the codebase structure and reading the critical files in parallel.

---

Now let me read the orchestrator in sections and explore the remaining critical files.

---

Now let me read the remaining critical files: the orchestrator's process_stream, the context pruner, the gRPC client with fallback, and the circuit breaker.

---

Now let me read the gRPC client's StreamChatWithFallback method and the orchestrator's process_stream method.

---

Now let me read the process_stream method and the _track_task/background task management.

---

Now let me look at the remaining monitoring files and the LLM fallback mechanism.

---

I now have comprehensive data for all seven audit items. Here is my report.

---

# Sparkle Production Stability & Resilience Audit Report

## DIMENSION 1: Error Recovery Quality

### 1. WebSocket Reconnection Resilience

**Rating: GOOD**

**Evidence:**

The Go gateway's WebSocket handling in `chat_orchestrator.go` is well-structured but fundamentally per-message-stateless: each incoming WS message triggers an independent `handleChatMessage` call, which opens a new gRPC stream, processes it to completion, and returns. This is a sound architectural choice.

**When the Python gRPC backend crashes mid-stream:**
- The gRPC client at `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/agent/client.go` line 310-320 (`StreamChat`) attempts an automatic reconnect on `UNAVAILABLE` or `DEADLINE_EXCEEDED` errors. On failure, it does one reconnect attempt and retries the RPC.
- The gateway's gRPC retry policy (line 111-123 of `client.go`) is configured with automatic retries: MaxAttempts=4, InitialBackoff=0.5s, MaxBackoff=10s, BackoffMultiplier=2.0, retryable on `UNAVAILABLE` and `RESOURCE_EXHAUSTED`.
- The `StreamChatWithFallback` method (line 278-292) checks a Go-side circuit breaker before attempting the call, returning `ErrCircuitOpen` immediately if the circuit is open.

**What happens to the WebSocket connection:**
- The WS connection stays alive. The stream recv error at line 599 of `chat_orchestrator_chatflow.go` triggers `respondStreamRecvError`, which sends a structured error payload to the client with an `error_code` and `retryable` flag.
- In-flight messages: Partial text already streamed to the client is preserved (already sent). The unsent portion is lost. There is no queue/replay mechanism.
- The WS connection itself does NOT reconnect -- the client must re-send the message.

**Weaknesses:**
- No automatic retry with backoff at the WS message level. If the backend crashes mid-stream, the user sees an error and must manually re-send.
- No client-visible "reconnecting..." state -- the error is binary (success or error payload).
- The `readWSMessages` goroutine in `chat_orchestrator_connections.go` properly exits on error or `connDone`, preventing goroutine leaks on stream failure.

**Backend gRPC-level health checking:**
- `health_checker.go` implements a full three-state circuit breaker (Closed/Open/Half-Open) with configurable thresholds, periodic health checking, and state transition callbacks. This is production-quality.

---

### 2. gRPC Stream Failure Handling

**Rating: GOOD**

**Evidence (from `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/agent_grpc_service.py` lines 228-390):**

**When the LLM API call fails mid-stream:**
- The `StreamChat` method (line 295) iterates over `self.orchestrator.process_stream()` responses and yields each one. If the LLM call fails mid-stream, already-yielded deltas have already been sent to the gateway.
- The `except Exception` handler at line 369 catches the failure and calls `build_safe_chat_error(e)` (from `/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/safe_error_messages.py`), which maps `TimeoutError` -> "系统处理超时", `ConnectionError/OSError` -> "服务暂时不可用", everything else -> "系统暂时不可用". All errors are marked `retryable=True`.
- A final error response is yielded (line 374-390) with `finish_reason=ERROR`, `error_code`, and `retryable` flag. The gRPC status code is set appropriately via `_grpc_status_for_chat_error`.
- If no text content was streamed at all (line 331-349), a fallback response is yielded: "(System) No valid response generated. Please try again later."

**LLM fallback mechanism (from `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/llm/fallback.py`):**
- `LLMModelFallbackManager` implements multi-attempt fallback with up to 3 attempts. It classifies errors into `FallbackReason` enum values (RATE_LIMIT, TIMEOUT, CONTEXT_TOO_LONG, SERVER_ERROR, CONNECTION_ERROR).
- `ModelHealthTracker` tracks per-model failure counts with configurable thresholds and recovery timeouts.
- `_get_fallback_candidates` selects alternative models within the same or lower tier.
- Streaming fallback is supported via `execute_stream_with_fallback` which attempts fallback on stream connection failures.
- Backoff is exponential: `base_delay * (2^attempt) + jitter`.

**Weaknesses:**
- Partial responses that were already yielded to the client are NOT preserved server-side for retry. If a user re-sends, the full LLM call is re-executed.
- The fallback manager retries at the model tier level, but there is no cached response fallback (e.g., returning a stale cached answer when all LLM calls fail).

---

### 3. Redis Unavailability

**Rating: GOOD**

**Evidence:**

**Rate limiting:**
- The `DistributedRateLimiter` in `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/middleware/distributed_rate_limiter.go` returns an error when Redis fails (line 199-208). It increments a `sparkle_rate_limiter_redis_fallback_total` counter. However, it does NOT fall back to a local rate limiter in the `Allow` method itself -- it returns `(false, 0, err)`, meaning Redis failure causes rate-limit rejection.
- A `HybridRateLimitMiddlewareSimple` exists (line 288-303) that sets up both Redis and local rate limiters, suggesting the infrastructure for fallback exists.

**Event Bus:**
- The `EventBus` class in `/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/event_bus.py` handles Redis unavailability reasonably well. Publish has retry with exponential backoff (line 1004-1024, configurable `max_retries=3`). Failed publishes go to a Dead Letter Queue (line 1027-1041). The consumer loop (line 1156-1210) catches connection errors and attempts reconnection (line 1204-1209).
- DLQ is persisted to database (`_persist_dlq_entry`, line 740-780), so events are not lost even if Redis is down.

**Circuit breaker for Redis:**
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/signals/redis_resilience.py` implements a dedicated Redis circuit breaker with three named breakers: `spine_pipeline`, `state_register`, `chronicle`. The `resilient_redis_call` wrapper (line 76-115) provides automatic retry (2 attempts), exponential backoff (0.1s * attempt), and fallback return values.

**Python orchestrator:**
- `ChatOrchestrator.__init__` at line 323 raises `ValueError` if `redis_client is None`. Redis is a hard dependency for the orchestrator. However, individual Redis operations are wrapped with try/except and treated as non-fatal (e.g., session state updates, cache operations).
- The `ContextPruner` (line 274-289) catches all Redis errors and returns empty history, allowing the system to degrade to "no history context" rather than crashing.

**Weaknesses:**
- Rate limiter does not gracefully degrade on Redis failure -- requests are rejected rather than falling back to local limiting in the primary code path.
- The orchestrator cannot initialize without Redis, meaning a Redis outage during application startup prevents the service from starting.

---

## DIMENSION 2: Resource & Concurrency Safety

### 4. Goroutine Leak Analysis

**Rating: GOOD**

**Evidence from `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/handler/chat_orchestrator.go` and `chat_orchestrator_connections.go`:**

Three goroutine sources per WebSocket connection:

1. **Ping ticker goroutine** (line 258-270): Started with `go func()`. Exits via `pingDone` channel (closed by `defer close(pingDone)` at line 271). Guaranteed exit.

2. **Read goroutine** (line 13-34 in `chat_orchestrator_connections.go`): Started inside `readWSMessages`. Exits when `connDone` is signaled (closed by `defer close(connDone)` at line 277) or when `conn.ReadMessage()` returns an error. Guaranteed exit.

3. **Semantic cache update goroutine** (line 807-815 in `chat_orchestrator_chatflow.go`): Uses `go func()` with `context.WithTimeout(context.WithoutCancel(ctx), 5*time.Second)`. This has a bounded timeout but is NOT tracked in a WaitGroup or channel. If Redis is slow, this goroutine lives up to 5 seconds after the WS handler returns. This is acceptable but worth noting.

**Timer cleanup:**
- `idleTimer` has `defer idleTimer.Stop()` at line 275.
- `pingTicker` is stopped inside its own goroutine via `defer pingTicker.Stop()`.

**Admission control (stream semaphore):**
- Line 159: `streamSem` is a buffered channel (default 200, configurable). Each `handleChatMessage` acquires a slot at line 242 and releases it via `defer` at line 243. This caps concurrent gRPC streams.

**Maximum goroutines per WS connection:** 3 (ping, read, occasional cache update). This is well-bounded.

**Weaknesses:**
- The background cache update goroutine (line 807) is fire-and-forget. Under extreme load with many concurrent WS connections, these could accumulate briefly, but the 5-second timeout bounds the issue.

---

### 5. Memory Pressure in Long Sessions

**Rating: GOOD**

**Evidence from `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/orchestrator.py` and `context_pruner.py`:**

The `ContextPruner` at `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/context_pruner.py` implements a three-tier context management strategy:

- **Tier 1 (<= 10 messages):** Full retention. No compression.
- **Tier 2 (<= 30 messages):** Rule-based compression. Low-signal messages are truncated. High-importance messages (containing "计划", "任务", "目标" etc.) are preserved. The recent 6 messages are always kept.
- **Tier 3 (> 30 messages):** LLM-based summarization using a FAST model. The recent 4 messages are always preserved. Anchor messages (tool calls, plan milestones) are kept. Earlier messages are summarized into a 100-character summary cached in Redis with 1-hour TTL.

The orchestrator also uses `TokenTracker` (line 353) to track token consumption per session.

The gateway side also caps history at 20 messages when loading for gRPC context (line 399 of `chat_orchestrator_chatflow.go`).

**For 50+ turn conversations:**
- History is loaded via Redis `LRANGE` (bounded). The context pruner compresses before sending to the LLM. Summary caches prevent repeated summarization costs.
- Gateway fetches at most 20 messages for gRPC history (line 399).
- The `max_history_messages=10` default means only 10 messages are passed uncompressed.

**Weaknesses:**
- The ContextPruner is a module-level singleton (`context_pruner_instance`). If Redis is slow, the `_summarize_sync` call blocks the orchestrator event loop. The fallback (line 142) returns compressed messages without a summary, which is safe.
- The `importance_threshold` is hardcoded to `max(summary_threshold, 30)`. Very long conversations (>100 turns) will always hit the summarization path, adding LLM latency.

---

### 6. Python Async Safety

**Rating: GOOD**

**Evidence from `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/orchestrator.py` lines 2059-2090:**

The orchestrator uses a **distributed lock** for session-level concurrency control:

```python
lock_acquired = await self._acquire_session_lock(session_id, request_id)
if not lock_acquired:
    yield ... error response "会话正在处理另一个请求，请稍候"
    return
```

This is a Redis-based distributed lock (via `SessionStateManager`) that prevents concurrent requests for the same session from corrupting FSM state. A lock renewal task (line 2088-2089) keeps the lock alive during long operations with a 10-second interval.

Background tasks are tracked in `self._bg_tasks` (a set) with automatic cleanup via `add_done_callback(self._bg_tasks.discard)` (line 1567-1568). The `shutdown()` method cancels all tracked tasks.

**State machine safety:**
- `SessionStateManager` uses Redis for state persistence. The lock ensures only one request mutates state at a time.
- The FSM states are well-defined: `INIT -> THINKING -> GENERATING -> TOOL_CALLING -> DONE/FAILED`.

**Weaknesses:**
- The distributed lock acquisition is fire-and-forget on failure -- it immediately returns an error to the user. There is no queueing or automatic retry at the orchestrator level. The user must re-send.
- The lock renewal task could theoretically fail silently if Redis becomes unavailable during a long stream, allowing a stale lock to expire while the stream is still active.

---

## DIMENSION 3: Monitoring & Observability Quality

### 7. Alert Coverage Evaluation

**Rating: GOOD**

**Evidence from monitoring YAML files:**

**Infrastructure & service health (`sparkle_slo_alerts.yml`):**
- `SparkleGatewayDown` / `SparkleBackendDown`: P1 critical, 2-minute threshold. Covers service reachability.
- `SparkleBackendHigh5xxRate`: 5xx ratio > 2% for 10m. Catches backend errors.
- `SparkleBackendP95LatencyHigh`: P95 > 1.5s for 10m. Catches latency degradation.
- `SparkleEventStreamLagHigh`: Lag > 120s. Catches event bus backlog.
- `SparkleSpineDegradation`: Signal pipeline degradation. Catches spine failures.
- `SparkleEventBusDLQGrowing`: DLQ receiving events. Catches consumer failures.
- `SparkleEventBusConsumerLagHigh`: Lag > 300s. Catches stalled consumers.

**AI-specific performance (`sparkle_production_baseline_alerts.yml`):**
- `SparkleAIFirstTokenLatencyHigh`: P95 > 4s for 15m. Catches slow LLM responses.
- `SparkleAITotalDurationHigh`: P95 > 25s for 15m. Catches long-running AI calls.
- `SparklePredictionRulesFallbackSpike`: Fallback > 20 in 15m. Catches prediction pipeline degradation.
- `SparkleBackendMemoryHigh`: Memory > 1.5GB for 10m. Catches memory leaks.
- `SparkleGatewayGoroutinesHigh`: Goroutines > 3000 for 10m. Catches goroutine leaks.

**SLO-targeted alerts (`sparkle_t6_slo_alerts.yml`):**
- `SparkleSLOChatFirstTokenSlow`: P95 > 2s for 10m. Directly measures Aurora slowness.
- `SparkleSLOTaskGenerationSlow`: P95 > 5s for 10m. Catches planning delays.
- `SparkleSLORetrievalSlow`: P95 > 1s for 10m. Catches RAG latency.
- `SparkleSLOGalaxySlow`: P95 > 3s for 10m. Catches Galaxy service issues.
- `SparkleSLOAuroraL3Slow`: P95 > 15s for 10m. Catches Aurora tier-3 latency.

**28-day SLO recording rules (`sparkle_recording_rules.yml`):**
- Pre-computed 28-day rolling compliance for chat first token and RAG retrieval SLOs.

**Behavioral/Aurora alerts (`sqam_alerts.yml`):**
- SRL phase oscillation, JITAI burden, PersDyn drift, predictive CTR drops.

**What IS covered well:**
- Latency SLOs at multiple service layers.
- Error rates and 5xx monitoring.
- Resource pressure (memory, goroutines).
- Event bus health (DLQ, consumer lag).
- AI response latency.

**What is MISSING or weak:**
- **No alert for correction loop failures** specifically. The `SparkleSpineDegradation` alert catches spine degradation broadly, but there is no alert specifically for correction loop failures (e.g., `aurora_correction_failed_total`).
- **No WebSocket-specific error rate alert.** While `WSConnectionError` and `WSConnectionSuccess` metrics are emitted (line 299, 306 of `chat_orchestrator.go`), there is no alert for WS connection failure rate spikes.
- **No per-user latency SLO.** Alerts are system-wide P95, which would not catch cases where specific users experience persistent slowness.
- **No circuit breaker open alert.** While the Go-side circuit breaker transitions are logged, there is no Prometheus alert when the circuit breaker opens.

---

## Summary Ratings

| Area | Rating | Key Strength | Key Gap |
|------|--------|-------------|---------|
| 1. WS Reconnection | GOOD | Per-message statelessness, gRPC auto-retry | No client-visible reconnect state |
| 2. gRPC Stream Failure | GOOD | Safe error messages, model fallback chain | No cached response fallback |
| 3. Redis Unavailability | GOOD | Circuit breakers, DLQ, retry with backoff | Rate limiter rejects on Redis failure |
| 4. Goroutine Leaks | GOOD | Bounded goroutines, proper cleanup | Fire-and-forget cache goroutine |
| 5. Memory Pressure | GOOD | Three-tier context pruning, summarization | Summarization blocks event loop |
| 6. Python Async Safety | GOOD | Distributed session locking, task tracking | No lock acquisition retry |
| 7. Monitoring Coverage | GOOD | Comprehensive SLO alerts, DLQ monitoring | Missing correction loop and circuit breaker alerts |

**Key files examined:**
- `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/handler/chat_orchestrator.go`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/handler/chat_orchestrator_connections.go`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/handler/chat_orchestrator_chatflow.go`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/agent/client.go`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/agent/health_checker.go`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/agent_grpc_service.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/orchestrator.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/context_pruner.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/circuit_breaker.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/event_bus.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/safe_error_messages.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/signals/redis_resilience.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/llm/fallback.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/middleware/distributed_rate_limiter.go`
- `/Users/brsama/code/GitHub/Sparkle-project/monitoring/sparkle_slo_alerts.yml`
- `/Users/brsama/code/GitHub/Sparkle-project/monitoring/sparkle_production_baseline_alerts.yml`
- `/Users/brsama/code/GitHub/Sparkle-project/monitoring/sparkle_t6_slo_alerts.yml`
- `/Users/brsama/code/GitHub/Sparkle-project/monitoring/sparkle_recording_rules.yml`
- `/Users/brsama/code/GitHub/Sparkle-project/monitoring/sqam_alerts.yml`

**Overall assessment:** The Sparkle system demonstrates strong production resilience engineering across all three dimensions. The most significant gaps are: (1) the rate limiter's hard-failure-on-Redis-error behavior, (2) missing alerting for circuit breaker state transitions, and (3) no correction-loop-specific failure alerting. None of these are critical -- the system degrades safely in all analyzed failure modes.