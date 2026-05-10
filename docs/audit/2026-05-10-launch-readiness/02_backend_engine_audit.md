# Backend Engine Launch-Readiness Audit

**Date**: 2026-05-10
**Scope**: Python Engine (backend/app)
**Auditor**: Senior Backend Architect (automated audit)
**Status**: CRITICAL -- launch blocked

---

## Executive Summary

The audit identified **11 findings** across the Python Engine layer, including **2 P0 blockers** and **4 P1 critical issues**. The most severe finding is that the `LLMSecurityWrapper` does not expose `reason_json()`, `chat_json()`, `reason()`, `continue_with_tool_results()`, or `chat_stream_with_tools()`, which means at least 15 call sites across production code paths will crash with `AttributeError` at runtime.

---

## Findings

### [B-001] LLMSecurityWrapper Missing Method Delegation -- Runtime Crash
- **Severity**: P0 (blocker)
- **File**: `backend/app/core/llm_security_wrapper.py` (full file), `backend/app/services/llm_service.py` line 1490
- **Description**: The global `llm_service` singleton is a `LLMSecurityWrapper` instance, not the raw `LLMService`. The wrapper only exposes `chat()`, `chat_with_tools()`, `stream_chat()`, and `generate_embeddings()`. It does NOT expose `reason()`, `reason_json()`, `chat_json()`, `continue_with_tool_results()`, `chat_stream_with_tools()`, or `reason_model` property. There is no `__getattr__` delegation to the underlying `llm_service_impl`.

  **Affected call sites (15+ locations):**
  - `app/orchestration/plan_review_service.py:1014` -- `llm_service.reason_json()`
  - `app/orchestration/plan_review_service.py:1098` -- `llm_service.chat_json()`
  - `app/orchestration/planning_workflow.py:2825` -- `llm_service.reason_json()`
  - `app/orchestration/task_guide_enricher.py:278` -- `llm_service.reason_json()`
  - `app/orchestration/execution_engine.py:1374` -- `llm_service.continue_with_tool_results()`
  - `app/api/v1/chat.py:292,543,695` -- `llm_service.continue_with_tool_results()`
  - `app/api/v1/chat.py:609` -- `llm_service.chat_stream_with_tools()`
  - `app/agents/enhanced_agents.py:288,526` -- `llm_service.reason()`
  - `app/agents/standard_workflow.py:2964` -- `llm_service.chat_json()`
  - `app/services/llm_extractor_service.py:88` -- `llm_service.chat_json()`
  - `app/services/skill_extract_service.py:101` -- `llm_service.chat_json()`
  - `app/services/skill_share/service.py:252` -- `llm_service.chat_json()`
  - `app/services/llm_dispatcher.py:519` -- `llm_service.reason_model` (property)

- **Impact**: Every plan review, LLM-based planning, tool continuation, streaming chat, skill extraction, and reasoning path crashes with `AttributeError`. This makes the system completely non-functional for any non-trivial interaction.

- **Fix Context**: Add a `__getattr__` method to `LLMSecurityWrapper` that delegates to `self.llm_service` for any unhandled attribute:

  ```python
  # In backend/app/core/llm_security_wrapper.py, class LLMSecurityWrapper:
  def __getattr__(self, name: str) -> Any:
      """Delegate unrecognized attributes to the underlying LLMService."""
      return getattr(self.llm_service, name)
  ```

  Alternatively, add explicit wrapper methods for `reason`, `reason_json`, `chat_json`, `continue_with_tool_results`, and `chat_stream_with_tools` that apply the same security pipeline as `chat`.

---

### [B-002] Cross-Model Review Uses Wrong Attribute Name (tool_name vs name)
- **Severity**: P0 (blocker)
- **File**: `backend/app/orchestration/plan_review_service.py` line 1050
- **Description**: The `_should_cross_review()` method accesses `tc.tool_name` on `ToolCallSpec` objects, but the `ToolCallSpec` dataclass uses the attribute `name`, not `tool_name`. The code uses `hasattr(tc, "tool_name")` to guard, which means `tool_names` will always be an empty list and the high-risk tool detection in cross-review will never trigger.

  ```python
  # Line 1050 (BROKEN):
  tool_names = [tc.tool_name for tc in (plan.tool_calls or []) if hasattr(tc, "tool_name")]

  # Line 1125 (CORRECT, in the same file):
  tool_names = [tc.name for tc in plan.tool_calls]
  ```

- **Impact**: High-risk tool detection (`delete_task`, `reset_progress`, etc.) is silently disabled in the cross-model review path. A plan containing destructive tool calls could be auto-approved by the primary reviewer and the cross-review would not flag it because the tool name list is always empty.

- **Fix Context**: Change line 1050 from:

  ```python
  tool_names = [tc.tool_name for tc in (plan.tool_calls or []) if hasattr(tc, "tool_name")]
  ```

  to:

  ```python
  tool_names = [tc.name for tc in (plan.tool_calls or [])]
  ```

---

### [B-003] Token Usage Recording Crashes When selection Is None
- **Severity**: P1 (critical)
- **File**: `backend/app/services/llm_service.py` lines 1115-1116, 1226-1227
- **Description**: In `chat_with_tools()` and `continue_with_tool_results()`, when `self._current_selection` is `None`, the code falls back to a direct `self.provider.client.chat.completions.create()` call. However, `selection` is set to `self._current_selection` (which is `None`), and the usage recording block accesses `selection.model_key` without a None guard:

  ```python
  selection = self._current_selection
  if selection:
      response = await self._create_raw_completion_with_fallback(...)
  else:
      response = await self.provider.client.chat.completions.create(**request_params)

  # This runs regardless of whether selection is None:
  if response.usage:
      _record_token_usage(
          selection.model_key,  # AttributeError: 'NoneType' has no 'model_key'
          ...
      )
  ```

- **Impact**: Any tool-calling or tool-continuation path that uses the fallback (no `LLMSelection`) will crash when recording token usage. This affects legacy mode and any edge case where dynamic routing hasn't initialized a selection.

- **Fix Context**: Guard the usage recording blocks with a None check, or set a fallback model_name:

  ```python
  model_name = selection.model_key if selection else "unknown"
  _record_token_usage(model_name, response.usage.prompt_tokens, ...)
  ```

---

### [B-004] Module-Level Checkpointer Creation at Import Time
- **Severity**: P1 (critical)
- **File**: `backend/app/agents/graph/workflow.py` lines 158-172, 340
- **Description**: `_make_checkpointer()` is called at module import time (line 171 and indirectly via `get_planning_graph()` at line 340). At import time, `cache_service.redis` is always `None` because Redis has not been initialized yet (Redis connection happens in the app lifespan startup). This means:

  1. The main graph always falls back to `MemorySaver` -- checkpoints are lost on server restart
  2. The planning graph singleton (created once at line 340) permanently uses `MemorySaver` even after Redis becomes available
  3. Multiple workers/processes cannot share checkpoint state

- **Impact**: LangGraph state is never persisted to Redis. Any long-running multi-turn conversation or plan review that spans a server restart loses all state. In a multi-process deployment, different workers cannot see each other's checkpoints.

- **Fix Context**: Defer checkpointer creation to first use rather than import time:

  ```python
  _checkpointer = None

  def _get_checkpointer():
      global _checkpointer
      if _checkpointer is None:
          _checkpointer = _make_checkpointer()
      return _checkpointer

  def _get_or_create_planning_graph():
      # Re-create if Redis became available after initial creation
      ...
  ```

---

### [B-005] chat_with_tools and continue_with_tool_results Lack Timeout Protection
- **Severity**: P1 (critical)
- **File**: `backend/app/services/llm_service.py` lines 1098-1105, 1210-1217
- **Description**: The `chat()` method uses `asyncio.timeout(120)` (line 593), and `reason()` uses `asyncio.timeout(180)` (line 836). However, `chat_with_tools()` and `continue_with_tool_results()` use `_create_raw_completion_with_fallback()` which has NO timeout. If the LLM API hangs, these calls will block indefinitely.

- **Impact**: A hung LLM API call during tool execution will block the entire request indefinitely, consuming a connection slot and preventing the user from getting any response.

- **Fix Context**: Add timeout to `_create_raw_completion`:

  ```python
  async def _create_raw_completion(self, selection, request_params):
      ...
      async with llm_concurrency.acquire(provider_name):
          async with asyncio.timeout(120):  # Add timeout
              return await current_provider.client.chat.completions.create(**params)
  ```

---

### [B-006] New task_resources Models Not Exported in __all__
- **Severity**: P2 (important)
- **File**: `backend/app/models/__init__.py` line 224
- **Description**: The uncommitted change adds `from app.models.task_resources import TaskKnowledgeLink, TaskResourceLink, TaskResourceType` at line 224, but these three symbols are NOT added to the `__all__` list. Code that does `from app.models import TaskResourceLink` will fail with `ImportError`.

  Additionally, `UserBlock` (from `app.models.community`) is imported in the test file but is also missing from both the import block and `__all__` in `__init__.py`.

- **Impact**: Any module attempting to import these models from the package root will fail. The Alembic autogeneration may also miss these tables if the models aren't discoverable through the package.

- **Fix Context**: Add the missing entries to the `__all__` list in `backend/app/models/__init__.py`:

  ```python
  # In the __all__ list, add:
  "TaskKnowledgeLink",
  "TaskResourceLink",
  "TaskResourceType",
  "UserBlock",
  ```

  Also add `UserBlock` to the community import block.

---

### [B-007] response.choices[0] Without Bounds Check
- **Severity**: P2 (important)
- **File**: `backend/app/services/llm_service.py` lines 1107, 1218
- **Description**: In `chat_with_tools()` and `continue_with_tool_results()`, the code accesses `response.choices[0]` without checking if the choices list is non-empty. Some LLM providers (especially content-filtered responses) may return an empty choices list.

  ```python
  choice = response.choices[0]  # IndexError if choices is empty
  ```

- **Impact**: A content-filtered or malformed LLM response will crash with `IndexError`, which will be caught by the outer exception handler but will incorrectly record a circuit breaker failure.

- **Fix Context**: Add a guard:

  ```python
  if not response.choices:
      raise HTTPException(status_code=502, detail="LLM returned empty response")
  choice = response.choices[0]
  ```

---

### [B-008] _cross_model_review Calls chat_json Without task_type
- **Severity**: P2 (important)
- **File**: `backend/app/orchestration/plan_review_service.py` lines 1096-1100
- **Description**: The new `_cross_model_review()` method calls `llm_service.chat_json()` with a simple `temperature=0.3`. The cascade routing introduced in the uncommitted changes to `llm_service.py` allows `chat()` to accept `task_type` for model tier selection. The cross-review should use a different model than the primary review, but it doesn't pass any task_type to ensure a different model tier is selected. Both the primary and cross-review could hit the same model, defeating the purpose.

- **Impact**: Cross-model review may use the same model as the primary review, providing no independent second opinion.

- **Fix Context**: When the wrapper issue is fixed, call with an explicit task_type:

  ```python
  result = await llm_service.chat_json(
      messages=messages,
      temperature=0.3,
      task_type=TaskType.STANDARD_RESPONSE,  # Use a different tier
  )
  ```

---

### [B-009] AuroraPrivacyKillSwitchService.get_mode Coroutine Never Awaited
- **Severity**: P2 (important)
- **File**: `backend/app/aurora/privacy.py` line 60 (reported in test warnings)
- **Description**: Test output shows a `RuntimeWarning: coroutine 'AuroraPrivacyKillSwitchService.get_mode' was never awaited` at `app/aurora/privacy.py:60`. The `get_mode` method is an async method that returns a coroutine, but the calling code at line 60 does not await it:

  ```python
  mode = normalize_mode(  # This calls get_mode() without await
      ...
  )
  ```

- **Impact**: Privacy kill switch state is never properly read. The mode will always fall back to the default (likely "off"), meaning privacy protections that should be active may not be enforced.

- **Fix Context**: Ensure `get_mode()` is properly awaited wherever it is called.

---

### [B-010] Local Signoff Preflight Skips CQRS Health Check
- **Severity**: P3 (minor)
- **File**: `backend/scripts/local_signoff_preflight.py` line 219
- **Description**: The CQRS health check endpoint (`/api/v1/health/cqrs`) was commented out with the reason "CQRS health requires auth token, skip in preflight". While this is a pragmatic fix, it means the preflight no longer verifies that the CQRS subsystem is healthy, which could mask gateway startup issues.

- **Impact**: The local signoff preflight is less comprehensive. A broken CQRS endpoint would not be caught until manual testing.

- **Fix Context**: Either generate a test auth token for the preflight, or add a separate CQRS readiness check that doesn't require auth.

---

### [B-011] Collaboration Confidence Threshold Is a Hardcoded Magic Number
- **Severity**: P3 (minor)
- **File**: `backend/app/agents/graph/nodes/collaboration.py` line 453
- **Description**: The keyword confidence threshold `_KEYWORD_CONFIDENCE_THRESHOLD = 0.65` is defined as a local variable inside `analyze_collaboration_plan()`. This value is critical for routing decisions (whether to escalate from keyword matching to LLM analysis) but cannot be configured or tuned without code changes.

- **Impact**: Cannot adjust the keyword-to-LLM escalation threshold via configuration. Requires code deployment to tune.

- **Fix Context**: Move to `settings` or a module-level constant:

  ```python
  _KEYWORD_CONFIDENCE_THRESHOLD = getattr(settings, "AGENT_KEYWORD_CONFIDENCE_THRESHOLD", 0.65)
  ```

---

## Test Results

### Test Run Summary
- **Total**: 398 passed, 142 skipped, 245 warnings, 1 error
- **Command**: `pytest tests/ --tb=line -q -x`

### Failing Tests

| Test | Root Cause | Fix |
|------|-----------|-----|
| `tests/integration/test_achievement_progress_context.py::test_achievement_progress_event_reaches_chat_context` | **ConnectionRefusedError**: PostgreSQL not running on port 5432. This is an integration test that requires live infrastructure. | Not a code bug. Requires `docker compose up -d sparkle_db` before running integration tests. |

### Warnings Requiring Attention

1. **RuntimeWarning** in `app/aurora/privacy.py:60` -- coroutine `AuroraPrivacyKillSwitchService.get_mode` was never awaited (see B-009)
2. **DeprecationWarning** in `app/api/v1/marketplace.py:161,335` -- `HTTP_422_UNPROCESSABLE_ENTITY` deprecated, should use `HTTP_422_UNPROCESSABLE_CONTENT`
3. **RuntimeWarning** in `pydantic/fields.py:681` -- coroutine `AsyncMockMixin._execute_mock_call` was never awaited (test mock issue in vocabulary tests)
4. **SAWarning** -- Can't sort tables for DROP; unresolvable foreign key dependency between `goals` and `plans` tables

### Pre-existing Issues (Not Part of This Audit)
- IsarCore download failure (Flutter)
- _FakeRedis.set() missing nx parameter
- Accessibility schema drift

---

## Summary Table

| ID | Title | Severity | File |
|----|-------|----------|------|
| B-001 | LLMSecurityWrapper missing method delegation | P0 | `app/core/llm_security_wrapper.py` |
| B-002 | Cross-review uses wrong attribute (tool_name vs name) | P0 | `app/orchestration/plan_review_service.py:1050` |
| B-003 | Token usage crashes when selection is None | P1 | `app/services/llm_service.py:1115,1226` |
| B-004 | Module-level checkpointer ignores Redis | P1 | `app/agents/graph/workflow.py:158-172,340` |
| B-005 | chat_with_tools/continue_with lack timeout | P1 | `app/services/llm_service.py:1098,1210` |
| B-006 | New models not in __all__ exports | P2 | `app/models/__init__.py` |
| B-007 | response.choices[0] without bounds check | P2 | `app/services/llm_service.py:1107,1218` |
| B-008 | Cross-model review may use same model | P2 | `app/orchestration/plan_review_service.py:1098` |
| B-009 | Aurora privacy get_mode coroutine not awaited | P2 | `app/aurora/privacy.py:60` |
| B-010 | Preflight skips CQRS health check | P3 | `backend/scripts/local_signoff_preflight.py:219` |
| B-011 | Hardcoded collaboration confidence threshold | P3 | `app/agents/graph/nodes/collaboration.py:453` |

---

## Recommended Fix Priority

1. **B-001** (P0) -- Must fix first. Add `__getattr__` to `LLMSecurityWrapper` to delegate to `self.llm_service`. This single fix unblocks all 15+ broken call sites.
2. **B-002** (P0) -- One-line fix. Change `tc.tool_name` to `tc.name` on line 1050.
3. **B-003** (P1) -- Add None guard for `selection.model_key` in two locations.
4. **B-005** (P1) -- Add `asyncio.timeout(120)` to `_create_raw_completion`.
5. **B-004** (P1) -- Defer checkpointer creation from import time to runtime.
6. **B-006** through **B-011** -- Can be batched in a follow-up commit.
