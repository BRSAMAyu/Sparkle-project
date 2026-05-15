# Execution Trust & Simulation Engine Audit (R7-01)

> Agent: Opus | Scope: execution_service.py, execution_trust.py, simulation_engine.py, dynamic_tool_registry.py, tool_execution flows
> Lines covered: ~5,307 | Date: 2026-05-15

---

## Part 1: Architecture Analysis

### 1.1 Execution Pipeline Architecture

The execution pipeline follows a multi-stage flow:

**Intent Creation** (`create_intent`): A task is classified by the `ExecutionRouter`, which determines `ExecutionMode` (AGENT/HUMAN) and `ExecutionTargetEnv` (BROWSER/SHELL/API/DOCUMENT). Quality strategy is assigned, risk is assessed via `ExecutionRiskAssessor`, user preferences are applied, and an `ExecutionIntent` is persisted to PostgreSQL.

**Dispatch** (`dispatch`): Budget is checked, concurrency limits are enforced (`max_concurrent_runs`). If exceeded, the intent is queued. Otherwise, the intent is dispatched to OpenClaw via HTTP or WebSocket transport. The `IntentTranslator` converts the intent into an OpenClaw request payload. Results are ingested through `ExecutionIngestor`.

**Ingestion** (`ExecutionIngestor.ingest`): Raw OpenClaw responses are parsed by `ResultParser`, validated against a local hybrid gate, evaluated by the `ExecutionTrustEngine`, and persisted as `ExecutionRecord`. If the result requires approval, the intent enters `WAITING_APPROVAL` status.

**Result Application** (`_apply_execution_result`): Based on the `TrustEvaluation`, the system decides whether to update the task status. Only `VALIDATED` or `TRUSTED` results can mark tasks as completed. If the task belongs to a plan, a `PlanExecutionRecord` is created and plan progress is updated.

**Degradation Circuit Breaker**: Consecutive failures within a 30-minute window trigger user-level degradation, forcing all subsequent executions to HUMAN mode. The degradation check is query-based (no in-memory state), and the clear function is a no-op (line 3251-3253), meaning degradation only naturally expires via the time window.

**Batch Execution** (`dispatch_batch`): Supports sequential and parallel strategies. Parallel mode creates isolated `AsyncSession` instances per intent to avoid DB session conflicts.

### 1.2 Trust Engine Design

`ExecutionTrustEngine` (`execution_trust.py`, 219 lines) implements a three-tier trust model:

1. **RAW**: Default level. Remains RAW if: empty result, safety issues detected, schema validation below 50%, success criteria not met, or quality score below 0.3. RAW results cannot update tasks or emit behavior signals.

2. **VALIDATED**: Achieved when schema + criteria pass with quality >= 0.3. Can update tasks and plan records but cannot emit behavior signals.

3. **TRUSTED**: Either explicitly confirmed by the user or auto-promoted based on executor history (min 5 runs, >= 85% success rate, quality >= 0.7). Full write access including behavior signal emission.

Safety checks in `_check_content_safety`:
- Walks entire result tree (dict/list/string) looking for sensitive keys (password, secret, api_key, token, etc.) and injection patterns (`<script`, `javascript:`, `eval(`, `exec(`).
- False positive risk: the sensitive key check uses substring matching on string values, so a legitimate string containing "token" (e.g., "sentence tokenization") would be flagged.

Quality scoring (0-1.0):
- 40% schema validation ratio
- 30% criteria met
- 30% output richness (dict field count / 5, or string length / 200)

### 1.3 Simulation Engine Architecture

`SimulationEngine` (`simulation/simulation_engine.py`, 1785 lines) runs multi-agent learning simulations:

**Session Lifecycle**: `stream()` creates a session, generates participants via LLM, then iterates rounds until `planned_round_count` or moderator signals end. Each round involves:
1. `_moderate_next_turn` - LLM call to decide who speaks next, whether to pause for user input, and whether to end
2. `_generate_agent_round` - LLM call to generate the actual agent speech
3. `_build_user_interaction_point` - LLM call to create diagnostic questions

**Checkpointing**: Three-tier: in-memory `OrderedDict` (max 128 entries), Redis cache (6-hour TTL), and PostgreSQL (via Celery task). Loading follows reverse order: Redis -> memory -> DB.

**Behavioral Context**: Integrates with `PredictiveService` for mastery gaps, intent forecast, and dropout risk. This context shapes moderator decisions.

**Insight Persistence**: Completed simulations publish `SimulationGapRevealed` events for knowledge gaps and enqueue system updates via `SystemUpdateService`.

**No Side Effects on Real Data**: The simulation engine is read-only regarding user data. It reads `ErrorRecord` and `KnowledgeNode` for anchoring but only writes simulation checkpoints and events. No task, plan, or user data is mutated.

### 1.4 Tool Registry & Dynamic Tools

`DynamicToolRegistry` (`orchestration/dynamic_tool_registry.py`, 370 lines) is a singleton that auto-discovers tools from `app.tools`:

- Uses `pkgutil.iter_modules` to scan packages
- Thread-safe via `threading.RLock`
- Validates tool classes via `_is_valid_tool_class` (must be concrete subclass of `BaseTool`)
- `validate_all_tools()` checks for missing execute, name, schema, and schema serialization
- Tools are registered once per package path (`ensure_package_registered`)

**Tool Execution Safety**:
- Each tool has `requires_confirmation` flag (checked in executor line 323-332)
- Per-tool `timeout_seconds` with 120s default, enforced via `asyncio.wait_for`
- Pydantic `parameters_schema` validates all arguments before execution
- Error messages are sanitized via `sanitize_exception_message`

**Tool Categories**: TASK, PLAN, KNOWLEDGE, QUERY, FOCUS, GROWTH - no privilege escalation mechanism beyond the category label (categories are informational, not enforced).

### 1.5 Execution Review Flow

`execution_review_node` (imported from `app.agents.graph.nodes.review_nodes.py`):
- Part of the LangGraph FSM workflow
- Reviews tool execution results using `ReviewerAgent`
- Integrates with review history service and model fallback service
- Records model performance metrics

The review happens post-execution within the standard workflow graph. The node evaluates tool results, checks for critical issues, and decides whether to proceed to reflection or final synthesis.

---

## Part 2: Problem Report

| ID | Severity | File:Line | Issue | Root Cause | Fix |
|----|----------|-----------|-------|------------|-----|
| ET-01 | **P0** | `execution_service.py:3251-3253` | `_clear_failure_state` is a no-op that never clears degradation | The method body is `del user_id; return None`, which means user degradation is never explicitly cleared on success. Degradation only expires when the 30-minute window passes, even if the user has many consecutive successes. A degraded user who succeeds via manual execution remains degraded for AI execution until the window expires. | Implement actual clearing: track degraded users in Redis with TTL matching `_degradation_window_seconds`, and remove the key on success. Alternatively, re-query recent failures on `_is_user_degraded` with a more recent cutoff. |
| ET-02 | **P0** | `execution_service.py:357-366` | MD5-based classification cache uses mutable shared class dict without thread safety | `_shared_classify_cache` is a class-level dict accessed from instances without locking. In concurrent async contexts, the cache pruning (lines 376-380) rebuilds the entire dict, which can lose entries added by other coroutines between reads. | Use `asyncio.Lock` for cache access or switch to `functools.lru_cache`/`cachetools.TTLCache`. |
| ET-03 | **P1** | `execution_service.py:1319-1331` | Parallel batch execution creates unbounded concurrency via `asyncio.gather` | When strategy is "parallel", all intents are dispatched via `asyncio.gather` with no bound on the number of concurrent dispatches. With a large batch, this could overwhelm OpenClaw connections, exhaust DB connection pool, or hit rate limits. | Add a semaphore bound (e.g., `asyncio.Semaphore(min(len(intents), max_concurrent_runs))`) to limit concurrent parallel dispatches. |
| ET-04 | **P1** | `execution_service.py:1324-1331` | Isolated DB sessions in parallel batch are not properly closed on error | `AsyncSessionLocal()` creates sessions in `_dispatch_isolated`, but if `ExecutionService.__init__` raises during construction (e.g., OpenClaw config issues), the session may leak. The `async with` only covers session creation, not the full service lifecycle. | Wrap the entire `ExecutionService` construction and dispatch in try/finally with explicit session cleanup. |
| ET-05 | **P1** | `execution_trust.py:143-149` | Content safety check has high false positive rate on legitimate content | The walk function checks every string value for substring matches against `sensitive_keys`. A value like `"Use a sentence tokenizer"` would match "token", and `"JavaScript patterns"` would match "javascript:". This blocks legitimate execution results without recourse. | Use word-boundary regex matching instead of substring matching. Add allowlist for common false positives. Log blocked fields at WARNING level for debugging. |
| ET-06 | **P1** | `execution_service.py:2443-2448` | Auto-approval logic is inverted for autonomous mode | When user mode is "autonomous" with low success rate (<0.6), policy is set to `require_for_side_effects` (stricter). But when mode is NOT "cautious" AND trust is high AND risk is low, policy is set to `"deny"` (which means deny approval, not deny execution). The variable name `approval_policy` with value `"deny"` is confusing and the logic for autonomous users falling back to stricter approval seems backward. | Clarify the approval policy semantics: rename `"deny"` to `"auto_approve"` or `"no_approval_required"`. Document the intended behavior for each combination. |
| ET-07 | **P1** | `execution_service.py:1066-1129` | No timeout on the entire dispatch lifecycle, only on OpenClaw client call | The dispatch method performs multiple DB operations (status updates, commits, refreshes) before and after the client call. If the DB becomes slow, the total wall time can far exceed `intent.timeout_seconds` with no enforcement. | Wrap the entire dispatch method in an `asyncio.wait_for` with a generous but bounded timeout (e.g., `intent.timeout_seconds + 60`). |
| ET-08 | **P1** | `execution_service.py:2995-2999` | Token usage is only recorded for TRUSTED results | `record_token_usage` is called unconditionally after `_upsert_execution_record`, but the record is only created when `_upsert_execution_record` is called from the ingestion path. Failed executions that bypass ingestion (e.g., timeout) do not have token usage tracked, leading to incomplete cost tracking. | Ensure token usage is recorded in the failure paths (e.g., in `_mark_intent_failure`) by extracting token counts from the OpenClaw error response when available. |
| ET-09 | **P2** | `execution_service.py:70-71` | `_utcnow()` strips timezone info | `datetime.now(UTC).replace(tzinfo=None)` creates a naive datetime that assumes UTC. While this is consistent throughout the codebase, it can cause confusion when comparing with timezone-aware datetimes from other sources. | Use timezone-aware datetimes consistently, or add a comment explaining the convention. |
| ET-10 | **P2** | `dynamic_tool_registry.py:36-38` | Class-level mutable defaults for `_tools`, `_tool_info`, `_registered_packages` | These are set as class attributes (shared across all instances). While `__new__` re-initializes them, the initial class-level defaults are `{}` and `set()`, which could cause issues if `__new__` is somehow bypassed or if the class is subclassed. | Move initialization entirely into `__new__` and use `None` as class-level defaults to make the singleton pattern more robust. |
| ET-11 | **P2** | `execution_service.py:2400` | `_session_key_for_intent` builds keys using `translator.build_session_key` but chat control builds keys independently | `_chat_control_session_key` (line 2703) builds session keys differently from `_session_key_for_intent`. If the same intent is accessed through both paths, different session keys could be generated, leading to inconsistent OpenClaw session management. | Unify session key construction through a single method. |
| ET-12 | **P2** | `execution_service.py:2043-2064` | Hidden chat control tasks use soft-delete (`deleted_at`) immediately after creation | The task is created with `task.deleted_at = _utcnow()` (line 2061), making it invisible to normal queries. However, the execution service still queries these tasks via `_get_user_task` which checks `deleted_at is not None`, so this works. The pattern is fragile - if anyone adds a `with_deleted()` scope, these hidden tasks would become visible. | Add a `is_hidden` boolean column instead of overloading `deleted_at`, or add a specific query method for chat control tasks. |
| ET-13 | **P2** | `simulation_engine.py:1602-1605` | In-memory checkpoint eviction is LRU but unbounded before pruning | `_local_checkpoints` is pruned only after writes. Under rapid simulation creation (e.g., load testing), memory could spike before pruning kicks in. The limit of 128 is reasonable for production but has no monitoring. | Add a metric gauge for checkpoint count and consider using `OrderedDict` with a fixed-size wrapper that prunes proactively. |
| ET-14 | **P2** | `simulation_engine.py:497-503` | Concept anchor search uses `ilike` with user input without sanitization | `KnowledgeNode.name.ilike(f"%{topic_lower}%")` embeds the topic directly into the LIKE pattern. While SQLAlchemy parameterizes the value, the `%` and `_` wildcards in the topic could alter the search pattern. | Escape LIKE wildcards in the topic: `topic_lower.replace('%', '\\%').replace('_', '\\_')`. |
| ET-15 | **P2** | `execution_service.py:2700` | Chat control idempotency key includes `time.time()` making it non-deterministic | When `request_id` is not provided, the idempotency key is `md5(f"{session_id}|{message}|{time.time()}")`. This means retrying the same chat control message creates a new intent every time, defeating idempotency. | Use a deterministic key based on `session_id + message` hash without the timestamp. |
| ET-16 | **P2** | `executor.py:763` | DAG layer concurrency bound is a module-level constant | `_DAG_LAYER_MAX_CONCURRENCY` is not configurable per-plan or per-user. For plans with many lightweight tools, this may be unnecessarily restrictive; for plans with expensive tools, it may be too permissive. | Make the concurrency bound configurable via the `ExecutablePlan` or execution policy. |
| ET-17 | **P2** | `execution_trust.py:196-203` | Quality score richness metric favors quantity over accuracy | The richness component (`min(len(output) / 5.0, 1.0) * 0.3` for dicts, `min(len(output.strip()) / 200.0, 1.0) * 0.3` for strings) rewards larger outputs regardless of content quality. A 5-field dict of garbage scores higher than a 3-field dict of precise results. | Consider weighting richness by relevance or removing it from the trust score and using it only as an informational metric. |
| ET-18 | **P2** | `execution_service.py:2816-2842` | `_recent_similar_failure_count` loads up to 12 recent intents with no time bound | The query in `_recent_similar_failure_count` filters by user but has no time constraint. Very old failures from months ago could still count, making the "similar failure" metric unreliable for current error recovery decisions. | Add a time constraint (e.g., last 24 hours) to the query. |

---

## Summary
- **P0**: 2 issues (degradation never clears; classification cache is thread-unsafe)
- **P1**: 6 issues (unbounded parallel batch; session leak risk; false-positive safety check; inverted approval logic; no overall dispatch timeout; incomplete cost tracking)
- **P2**: 10 issues (naive datetimes; mutable class defaults; session key inconsistency; hidden task pattern; checkpoint eviction; LIKE injection; non-deterministic idempotency; hardcoded DAG concurrency; quantity-over-quality scoring; unbounded failure lookback)
- **Overall Assessment**: The execution pipeline is architecturally sound with strong trust gating, comprehensive audit logging, and well-designed degradation circuit breaking. The two P0 issues -- the no-op `_clear_failure_state` that prevents degradation recovery, and the thread-unsafe shared cache -- should be fixed before production. The P1 issues around batch concurrency and dispatch timeout represent real operational risk under load. The simulation engine is cleanly isolated with no side effects on real data, and the tool registry has proper safety guards via Pydantic validation and per-tool timeouts.
