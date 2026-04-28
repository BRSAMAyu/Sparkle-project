# Sparkle Bug Fix Progress — 2026-04-28

## Session Summary

**Test Results**: 56 failures → 34 failures (22 fixed), 5794 → 5828 passed
**Commits**: 3 fix commits on `gpt_pro方案推进`

---

## P0 Fixes (Committed)

### 1. WebSocket Session Context Loss on Reconnect
**File**: `backend/gateway/internal/handler/chat_orchestrator_chatflow.go`
**Root Cause**: Go Gateway built ChatRequest without loading conversation history from Redis. On WS reconnect, Python received empty history and treated the request as a new conversation.
**Fix**: Load history via `chatHistory.GetMessages()` and populate `req.History`.

### 2. Semantic Cache Ignoring Multi-Turn Context
**File**: `backend/gateway/internal/handler/chat_orchestrator_chatflow.go`
**Root Cause**: Semantic cache scope didn't include session context, so Turn 3 with similar text to Turn 1 returned Turn 1's cached response.
**Fix**: Skip semantic cache when session has existing history (`sessionHasHistory` flag).

### 3. EventBus Redis URL Mismatch
**File**: `backend/app/core/event_bus.py:889`
**Root Cause**: EventBus constructor defaulted to `redis://localhost:6379/0` (no password) instead of `settings.REDIS_URL`.
**Fix**: Chain: `redis_url or os.getenv("REDIS_URL") or settings.REDIS_URL`.

### 4. EventBus xautoclaim Crash (redis-py 7.4.0)
**File**: `backend/app/core/event_bus.py:1291-1301`
**Root Cause**: redis-py 7.4.0 returns 3-tuple from XAUTOCLAIM, code unpacked 2.
**Fix**: Index-based access `result[0], result[1]` instead of tuple unpacking.

---

## P1 Fixes (Committed)

### 5. CognitiveStreamWorker Missing UserStateSnapshot
**File**: `backend/app/services/analytics/cognitive_stream_worker.py`
**Fix**: Added `StateEstimatorService.update_state()` call in `_process_event()`.

### 6. Stale QueryPlanTasksTool Duplicate
**File**: `backend/app/tools/query_plan_tasks_tool.py` (deleted)
**Fix**: Removed incompatible duplicate; correct version in `task_query_tool.py`.

### 7. Aurora Switches All Promoted to Live
**File**: `docker-compose.yml`
**Fix**: Added `ENABLE_AURORA_RUNTIME_V1=true` + 22 switch overrides → 33 total live in Docker.

### 8. Integration Test Hardening
**File**: `backend/tests/integration/test_event_pipeline_integration.py`
**Fix**: Consumer group created before publish; module-scoped event loop.

---

## Pre-Existing Fixes (Committed)

### 9. AuroraEnergyState Frozen Model Mutation
**File**: `backend/app/aurora/runtime_v1/state.py`
**Root Cause**: `AuroraSchemaBase(frozen=True)`, but `record_l3_session` and `resolve_energy_level` mutated fields directly.
**Fix**: Use `model_copy(update={...})` for immutable updates.

### 10. ProfileContext Missing goal_context Attribute
**File**: `backend/app/services/aurora_control_surface_service.py`
**Fix**: Read goals from `user_insight_state.goals` instead of `goal_context.goals`.

### 11. Retrieval Intent Classifier Mode Names Renamed
**File**: `backend/tests/unit/test_retrieval_intent_classifier.py`
**Fix**: Updated all test expectations from old names (skip/aggressive/selective) to new names (no_retrieval/targeted_source_rag/graph_only).

### 12. Scene Test Helper Date Staleness
**File**: `backend/tests/unit/scene_test_helpers.py`
**Fix**: Changed hardcoded April 2026 dates to current UTC time.

### 13. AuroraRuntimeTurnPlan Missing Attributes
**File**: `backend/app/aurora/runtime_v1/service.py`
**Fix**: Added `action` and `chat_directive` fields to dataclass.

### 14. GalaxyService NoneType on db=None
**File**: `backend/app/orchestration/planning_workflow.py`
**Fix**: Added early return guard in `_refresh_study_material_context`.

---

## Remaining 34 Failures (Investigation Needed)

- `test_signal_spine.py` (3): Policy experiment / learning base issues
- `test_theater_seed_and_accuracy.py` (1): Simulation engine timing
- Various API, service, and unit tests (~30): Schema drift, config changes, i18n
