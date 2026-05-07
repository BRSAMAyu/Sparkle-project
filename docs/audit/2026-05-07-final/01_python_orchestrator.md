# Python Orchestrator & AI Engine Audit

**Auditor**: Agent (Opus)
**Date**: 2026-05-07
**Status**: PASS WITH ISSUES

## Summary

The Python Orchestrator & AI Engine layer is architecturally sound with strong governance controls (kill switches, privacy redaction, circuit breakers, distributed locks). The dual-core routing logic is thorough and well-structured with clear precedence rules. However, two critical import bugs in `orchestrator.py` will cause `NameError` crashes at `ChatOrchestrator` initialization, and there is a missing import of `ModelTaskStatus` in the same file. These must be fixed before launch. Several medium-priority issues around shallow-copy concurrency safety and Redis error handling also warrant attention.

## Critical Issues (P0)

### P0-1: Missing import for `dual_core_router` singleton
**File**: `backend/app/orchestration/orchestrator.py:305`
**Severity**: NameError at runtime — crashes `ChatOrchestrator.__init__()`

```python
self.dual_core_router = dual_core_router  # line 305
```

The bare name `dual_core_router` (the `DualCoreRouter` singleton defined at `dual_core_router.py:1089`) is never imported in `orchestrator.py`. None of the 47 `from app.orchestration.*` imports bring this name into scope. This will raise `NameError: name 'dual_core_router' is not defined` every time `ChatOrchestrator` is instantiated.

**Fix**: Add `from app.orchestration.dual_core_router import dual_core_router` to the import block.

---

### P0-2: Missing import for `MultiAgentWorkflowAdapter`
**File**: `backend/app/orchestration/orchestrator.py:394`
**Severity**: NameError at runtime — crashes `ChatOrchestrator.__init__()`

```python
self.multi_agent_adapter = MultiAgentWorkflowAdapter(self)  # line 394
```

`MultiAgentWorkflowAdapter` is defined in `multi_agent_adapter.py` but never imported in `orchestrator.py`. The class is listed in `multi_agent_adapter.__all__`, but no import statement references it. The `execution_engine.py` mixin imports only `execute_multi_agent_workflow` from that module, not the adapter class.

**Fix**: Add `from app.orchestration.multi_agent_adapter import MultiAgentWorkflowAdapter` to the import block.

---

### P0-3: Missing import for `ModelTaskStatus`
**File**: `backend/app/orchestration/orchestrator.py:1012`
**Severity**: NameError at runtime — crashes `_find_completed_task_since()` when a task completion is detected during turn-end memory writeback.

```python
Task.status == ModelTaskStatus.COMPLETED,  # line 1012
```

The code uses `ModelTaskStatus.COMPLETED` but `ModelTaskStatus` is never imported. `Task` is imported from `app.models.task` at line 55, but the file only exports `TaskStatus` (an `StrEnum`). Other files like `task_tools.py` and `task_query_tool.py` correctly use `from app.models.task import TaskStatus as ModelTaskStatus`. This file does not.

**Fix**: Either add `from app.models.task import TaskStatus as ModelTaskStatus` or use `TaskStatus` directly (after importing it) and update the reference at line 1012.

---

## High Issues (P1)

### P1-1: Shallow-copy mutation risk in `WorkflowState.clone()`
**File**: `backend/app/orchestration/statechart_engine.py:62-72`

```python
def clone(self) -> WorkflowState:
    new_state = WorkflowState(
        messages=list(self.messages),
        context_data=dict(self.context_data),  # shallow copy
        ...
    )
    return new_state
```

`dict(self.context_data)` creates a shallow copy — the nested dict values are shared references between the original and cloned state. If parallel branches mutate nested values in `context_data` (e.g., `state.context_data["plan_context"]["active_task_id"] = ...`), mutations from one branch will leak into the other. The statechart engine's parallel execution path at `statechart_engine.py:421-443` uses this `clone()` to fork state for branches.

**Impact**: Data corruption in parallel multi-agent workflows where both branches write to shared nested dicts.

**Fix**: Use `copy.deepcopy(self.context_data)` or `json.loads(json.dumps(self.context_data))` for a deep copy.

---

### P1-2: Demo mode activates on missing API key without logging a warning
**File**: `backend/app/services/llm_service.py:273,319`

```python
if not kwargs.get("api_key"):
    self.demo_mode = True  # line 273
...
if not api_key:
    self.demo_mode = True  # line 319
```

When the API key is missing (misconfiguration), the LLM service silently falls into demo mode and returns canned responses. No warning is logged for this critical fallback. In production, a misconfigured `api_key` would cause all LLM calls to return mock data without any indication of the problem.

**Fix**: Add `logger.warning("LLM API key is empty; activating demo mode. LLM calls will return canned responses.")` before setting `self.demo_mode = True`.

---

### P1-3: Unprotected Redis calls in orchestrator process_stream
**File**: `backend/app/orchestration/orchestrator.py:2380-2382, 2603, 2627`

Several Redis calls in `process_stream` are not wrapped in try/except:

```python
await self.redis.incr(_inter_key)            # line 2380
await self.redis.expire(_inter_key, 24*3600) # line 2381
_inter_count_raw = await self.redis.get(_inter_key)  # line 2382
_growth_raw = await self.redis.get(...)       # line 2603
_raw = await self.redis.get(...)              # line 2627
```

While the spine integration block has a broad try/except around it, individual Redis operations within it would break the flow and skip subsequent spine checks. These are inside the outer spine try/except (line 2403), so they are partially covered, but the inner exceptions could skip important downstream spine signal fetches.

**Fix**: Wrap each Redis interaction in its own try/except with degraded logging, as done for the `GrowthChronicleService` call pattern at lines 2373-2376.

---

## Medium Issues (P2)

### P2-1: `SessionStateManager.acquire_lock` fails open on Redis errors
**File**: `backend/app/orchestration/state_manager.py:284-320`

```python
except Exception as e:
    logger.error(f"Error acquiring lock for session {session_id}: {e}")
    return False  # Denies request on error
```

The lock acquisition returns `False` on Redis errors, which blocks the request entirely. Meanwhile, `_acquire_session_lock` in `orchestrator_production.py:374-388` returns `True` on failure (fail-open). The `orchestrator.py` code calls `self._acquire_session_lock` which likely uses the state_manager behavior. Inconsistent fail-open vs fail-closed behavior between the two orchestrators creates confusion.

---

### P2-2: `ProductionChatOrchestrator` is a dead code path but not fully removed
**File**: `backend/app/orchestration/orchestrator_production.py:226-329`

The class is gated behind `SPARKLE_ALLOW_LEGACY_PRODUCTION_ORCHESTRATOR=1` and has a docstring saying "Legacy production orchestrator. This stack is no longer bridge-safe." However, the file is still 67KB, imports many dependencies, and has its own `CircuitBreaker`, `MessageTracker`, and session management. This dead code adds import-time overhead and maintenance burden.

**Fix**: Consider removing the file entirely or moving it to `backend/app/_deprecated/`.

---

### P2-3: `dynamic_tool_registry` is a module-level singleton with shared mutable state
**File**: `backend/app/orchestration/dynamic_tool_registry.py:29-47`

The `DynamicToolRegistry` uses `__new__` for singleton pattern and stores tools in class-level `_tools: dict`. While it has `threading.RLock` for thread safety, in an async context (FastAPI + asyncio), the `RLock` could block the event loop during tool registration. However, registration only happens at startup, so this is low risk in practice.

---

### P2-4: Planning workflow has unbounded Redis session data
**File**: `backend/app/orchestration/planning_workflow.py:272-302`

`PlanningSession.to_dict()` uses `dataclasses.asdict()` which serializes the entire `collected` dict and `bottlenecks` list without size limits. If `collected` accumulates large payloads (e.g., knowledge node lists, sprint pack data), the Redis `setex` at line 446 could store very large values. The TTL is 2 hours, but within that window, multiple active planning sessions could consume significant Redis memory.

**Fix**: Add a size guard before `save_session` — truncate `collected` values exceeding a reasonable threshold (e.g., 50KB).

---

### P2-5: `_merge_context_data` uses insertion-order eviction
**File**: `backend/app/orchestration/statechart_engine.py:96-107`

```python
while len(target) > settings.MAX_CONTEXT_DATA_KEYS:
    oldest_key = next(iter(target))
    del target[oldest_key]
```

Since Python 3.7, `dict` preserves insertion order, so this evicts the oldest-inserted key. But many context keys are repeatedly overwritten (e.g., `dual_core_decision`, `situation_brief`), which moves them to the end. This means the eviction could delete important but infrequently-updated keys (like initial `session_id`) while preserving frequently-updated but less important ones. The behavior is deterministic but may surprise developers.

---

## Low Issues (P3)

### P3-1: Hardcoded Chinese strings in `dual_core_router.py`
**File**: `backend/app/orchestration/dual_core_router.py` (multiple lines)

The cognitive adjustment strings (e.g., "先帮助用户澄清目标、约束和成功标准，再进入具体方案") are hardcoded in Chinese. Per the project's i18n strategy (CLAUDE.md: ARB l10n), user-facing strings should use the `isChinese ? '中文' : 'English'` pattern or ARB localization. Since these strings flow into prompts (not UI), this is low priority, but it means non-Chinese-speaking users will receive Chinese-injected cognitive adjustments in their prompts.

---

### P3-2: `_utcnow()` helper duplicated across 5+ files
**Files**: `orchestrator.py:194`, `orchestrator_production.py:110`, `planning_workflow.py:153`, `statechart_engine.py:55`, `state_manager.py:71`

Each file defines its own `_utcnow()` which does `datetime.now(UTC)` with slightly different implementations (some strip tzinfo, some don't). Inconsistent tzinfo handling across these helpers could cause subtle comparison bugs.

**Fix**: Use the central `app.core.time_utils.utcnow` everywhere.

---

### P3-3: `orchestrator.py` has many aliased imports for `memory_helpers`
**File**: `backend/app/orchestration/orchestrator.py:96-128`

Each function from `memory_helpers` is imported with a private alias pattern (`_safe_float`, `_extract_struggle_score`, `_first_memory_value`, etc.) and then re-exposed as a static/class method on `ChatOrchestrator`. This creates 13 import lines and 13 delegation methods. A single `from app.orchestration.memory_helpers import *` or a mixin would be cleaner.

---

### P3-4: F-string in `CircuitBreaker` logger call
**File**: `backend/app/orchestration/orchestrator_production.py:145`

```python
logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
```

Using f-strings with `loguru` bypasses its lazy formatting. Should use `logger.warning("Circuit breaker OPENED after {} failures", self.failure_count)`.

---

## Positive Findings

1. **Kill switch integration is thorough**: Every Aurora feature uses tri-state (`off`/`shadow`/`live`) via `normalize_mode` and `record_mode_gauge`. The privacy module at `app/aurora/privacy.py` correctly uses kill switches for PII redaction.

2. **PII redaction is well-implemented**: The regex patterns for Chinese IDs, phone numbers, emails, and bank cards are comprehensive with proper lookbehind/lookahead guards. The `sha256_token` function is used for audit logging without storing raw PII. Laplace noise for differential privacy is mathematically correct.

3. **Distributed lock management is production-ready**: The `SessionStateManager` uses Lua scripts for atomic lock release, NX option for lock acquisition, and a lock renewal mechanism. The orchestrator's `process_stream` properly acquires/releases locks with renewal tasks.

4. **Dual-core routing logic is comprehensive and well-structured**: The `DualCoreRouter.route()` method handles 12+ signal dimensions (emotional block, procrastination, SRL phase, metacognition, spine states, scaffolding zone, route outcomes, capsule preferences, Aurora preferences, corrections) with explicit precedence weights and clear documentation.

5. **Circuit breaker patterns are solid**: Both the legacy `CircuitBreaker` and the newer `circuit_breaker.py` implement proper CLOSED/OPEN/HALF_OPEN states with Prometheus gauge integration.

6. **Stream backpressure handling is well-designed**: The `_enqueue_stream_response` method with priority-based eviction (droppable vs critical) and bounded wait-for-put is a mature pattern for gRPC streaming.

7. **Aurora governance rules are enforced through the codebase**: Kill switch checks, privacy boundaries, and hard bounds are consistently applied across the Aurora runtime, planning sidecar, and core session modules.

8. **Error handling is generally defensive**: The broad `except Exception` handlers are appropriate for this layer (orchestrator should never crash), and each one logs the error for observability.

## Files Audited

### Core Orchestration
- `backend/app/orchestration/orchestrator.py` (full file, ~3500 lines)
- `backend/app/orchestration/orchestrator_production.py` (full file, ~670 lines)
- `backend/app/orchestration/dual_core_router.py` (full file, ~1090 lines)
- `backend/app/orchestration/planning_workflow.py` (full file, ~5200+ lines)
- `backend/app/orchestration/session_state_mixin.py` (full file, ~1200 lines)
- `backend/app/orchestration/response_builder.py` (full file, ~1800+ lines)
- `backend/app/orchestration/execution_engine.py` (first 200 lines)
- `backend/app/orchestration/ux_envelope.py` (first 200 lines)
- `backend/app/orchestration/plan_review_service.py` (first 200 lines)
- `backend/app/orchestration/state_manager.py` (first 400 lines)
- `backend/app/orchestration/statechart_engine.py` (full file)
- `backend/app/orchestration/dynamic_tool_registry.py` (full file)

### Aurora
- `backend/app/aurora/privacy.py` (full file)
- `backend/app/aurora/core_session.py` (first 200 lines)
- `backend/app/aurora/engine.py` (full file)
- `backend/app/aurora/config.py` (referenced)
- `backend/app/aurora/common.py` (referenced)
- `backend/app/aurora/context.py` (referenced)

### LLM Service
- `backend/app/services/llm_service.py` (first 600 lines)

### Tools
- `backend/app/tools/task_tools.py` (referenced for ModelTaskStatus pattern)
- `backend/app/tools/task_query_tool.py` (referenced for ModelTaskStatus pattern)
