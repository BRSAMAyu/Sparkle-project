# Round 3 Audit: SpineOrchestrator God Class

> **Target**: `backend/app/signals/spine_orchestrator.py`
> **Stats**: 4,950 lines | 1 class | 136 methods | 103 `except Exception` | ~40 injected dependencies
> **Date**: 2026-05-15
> **Auditor**: Agent (deep static analysis)

---

## Executive Summary

SpineOrchestrator is the single largest class in the Sparkle codebase and serves as the central hub for the entire Signal-to-Action Spine. While it has already undergone partial extraction (DirectiveStore, CardStore, PolicyEngine were previously factored out), it still violates the Single Responsibility Principle at least **8-fold**. The class coordinates signal detection, policy evaluation, directive persistence, outcome recording, Aurora session management, community loops, goal arbitration, state management, metrics, enrichment, and divine-moment card emission -- all within a single `__init__` that instantiates ~40 service objects.

**Risk Level**: HIGH -- the breadth of responsibility makes isolated testing impossible, changes propagate unpredictably, and the 103 `except Exception` blocks (while mostly justifiable) create observability gaps.

---

## 1. Responsibility Domain Analysis

### 1.1 Current Responsibilities (8 identified domains)

| # | Domain | Method Count | Lines | Description |
|---|--------|-------------|-------|-------------|
| D1 | **Signal Ingestion** | 12 | ~500 | `on_task_completed`, `on_chat_turn`, `on_first_message`, `on_file_uploaded`, `on_quiz_result`, `on_mistake_event`, `on_achievement_event`, `on_external_event`, `on_recall_check`, `on_user_return`, `on_absence_detected`, `_detect_chat_turn_signal` |
| D2 | **Pipeline Execution** | 3 | ~450 | `_run_signal_pipeline`, `_enrich_pipeline_post_policy` (270 lines alone), `_run_live_quality_guard` |
| D3 | **Directive Persistence & Retrieval** | 22 | ~350 | All `_store_*` / `get_*_directive` methods + directive application |
| D4 | **Outcome Recording & Learning** | 6 | ~350 | `record_outcome`, `_load_strategy_beliefs`, `_persist_strategy_beliefs`, outcome attribution, counterfactual shadow |
| D5 | **Aurora Session Lifecycle** | 9 | ~350 | `start_aurora_core_session`, `close_aurora_session`, `process_aurora_reply`, `pause_*`, `resume_*`, `check_*_health`, `consume_aurora_decisions`, `_consume_aurora_decisions_for_attribution` |
| D6 | **Community & Social** | 8 | ~250 | `on_community_cohort_data`, `on_community_resource_data`, `on_partner_observation`, `on_partner_checkin`, `on_community_hint`, community directive + hint retrieval |
| D7 | **Goal Management** | 8 | ~200 | `register_goal`, `detect_goal_drift`, `arbitrate_goals`, `get_goal_graph`, goal-scoped state, `_apply_goal_type_overlay` |
| D8 | **UI/UX & State Presentation** | 14 | ~500 | `get_status_band_summary`, `_compute_6state_band`, `build_experience_envelope`, `get_rendered_timeline`, `_build_correction_options`, recovery/context/community cards, milestone cards, `check_fatigue`, `detect_crisis_mode`, `detect_cognitive_load`, `detect_affective_pressure` |

### 1.2 Recommended Decomposition

```
SpineOrchestrator (Facade, ~500 lines)
  |
  +-- SignalIngestionService        (D1)  -- event -> ActionableSignal
  +-- PipelineExecutor              (D2)  -- signal -> trace (core pipeline)
  +-- DirectiveFacade               (D3)  -- store/retrieve/apply directives
  +-- OutcomeLearningService        (D4)  -- outcome + learning + counterfactual
  +-- AuroraSessionService          (D5)  -- already exists as AuroraCoreSessionService, but lifecycle methods still here
  +-- CommunityIntegrationService   (D6)  -- community signals + loops
  +-- GoalManagementService         (D7)  -- goal registration, drift, arbitration
  +-- SpinePresentationService      (D8)  -- status bands, envelopes, cards, fatigue, crisis
```

**Migration Strategy**: Introduce Facade interface first. Each domain becomes a separate service file in `app/signals/spine_services/`. SpineOrchestrator delegates to services. Existing callers unchanged. Then gradually move callers to services directly.

---

## 2. Exception Handling Audit (103 `except Exception`)

### 2.1 Classification Breakdown

| Category | Count | Assessment |
|----------|-------|------------|
| **A: Defensive + Logged** | 20 | Reasonable -- logs at appropriate level, returns safe fallback |
| **B: Silent pass** | 1 | PROBLEMATIC -- swallows exception with no logging |
| **C: Silent return None** | 1 | QUESTIONABLE -- returns None without logging |
| **D: Re-raise** | 2 | CORRECT -- log then re-raise |
| **E: Enrichment non-critical** | 76 | ACCEPTABLE -- enrichment/metrics must not block main pipeline |
| **F: Redis degraded** | 3 | ACCEPTABLE -- Redis failures use classify_error for observability |

### 2.2 Problematic Exceptions (3 items)

#### L2735 `_estimate_deadline_hours` -- SILENT PASS
```python
except Exception:
    pass
return None
```
**Issue**: If deadline estimation fails for any reason beyond Redis, it silently returns None. No observability.
**Fix**: Add `logger.debug("deadline estimation failed for user={}", user_id, exc_info=True)`.

#### L1871 `get_l1_turn_context` -- SILENT RETURN
```python
except Exception:
    return None
```
**Issue**: L1 context retrieval failure is invisible. If Aurora L1 is broken, there is no signal.
**Fix**: Add `logger.debug("get_l1_turn_context failed for user={}", user_id, exc_info=True)`.

#### L2578 `get_recall_notification` -- DEGRADED WITHOUT TRACE ID
```python
except Exception:
    logger.debug("get_recall_notification degraded: Redis unavailable for user={}", user_id)
    return None
```
**Issue**: `exc_info=True` is missing, making it impossible to diagnose WHY Redis failed.
**Fix**: Add `exc_info=True`.

### 2.3 Pattern Assessment

**The 76 "enrichment non-critical" blocks are architecturally intentional.** The Spine's core pipeline (Signal -> Policy -> Directive -> Trace) must never be blocked by a failing enrichment module. The `_enrich_pipeline_post_policy` method alone has **15** `except Exception` blocks because it chains 11 independent enrichment steps. This is the correct pattern for a "best effort" enrichment chain.

**However**, the enrichment blocks all use identical warning messages like `"_enrich_pipeline_post_policy: operation failed"`. This makes it impossible to distinguish which of the 11 steps failed from log output alone. **Recommendation**: Give each block a unique message identifying the step (e.g., `"enrich_policy_experiments_failed"`, `"enrich_crisis_check_failed"`).

### 2.4 `except Exception` vs Specific Exceptions

All 103 blocks catch `Exception` rather than specific types. This is a code smell but pragmatically justified in this codebase because:
1. Redis client errors are not consistently typed
2. Downstream services may raise arbitrary exceptions
3. The enrichment pattern requires maximum resilience

**Long-term recommendation**: Introduce a `SpineException` hierarchy with `SpineTransientError` (retriable) and `SpineFatalError` (must surface) to allow selective catching.

---

## 3. Method Visibility Analysis

### 3.1 Current State

| Visibility | Count | Lines (approx) |
|-----------|-------|--------|
| **Public** (`async def method_name`) | 88 | ~3,800 |
| **Private** (`async def _method_name`) | 37 | ~1,050 |
| **Static** (`@staticmethod`) | 2 | ~15 |

### 3.2 Methods That Should Be Private

These public methods are only called internally (from within SpineOrchestrator or its pipeline) and have no external callers:

| Method | Current | Should Be | Reason |
|--------|---------|-----------|--------|
| `consume_aurora_decisions` | public | `_consume_aurora_decisions` | Only called from `_run_signal_pipeline` and `_consume_aurora_decisions_for_attribution` |
| `get_active_directive` | public | KEEP public | Called by `planning_workflow.py` |
| `get_l1_turn_context` | public | `_get_l1_turn_context` | Only called from `orchestrator.py` internal path |
| `rank_signals` | public | `_rank_signals` | Only called from `build_state_packet` (internal) |
| `check_aurora_wake` | public | KEEP public | Called from external task completion path |
| `generate_reply_options` | public | KEEP public | API-exposed |
| `process_reply_selection` | public | KEEP public | API-exposed |

**Note**: Grep analysis shows `rank_signals` has no external callers (it is always used via `self.signal_ranker.rank()` internally). Marking it private would reduce the public surface.

### 3.3 True Public API Surface

Based on caller analysis of 21 consumer files, the **actual external API** is ~30 methods:

**From `orchestrator.py`**: `on_chat_turn`, `build_experience_envelope`, `on_first_message`, `get_l1_turn_context`, `build_state_packet`, `get_active_states`, `add_counter_evidence`, `get_active_directive`, `apply_directive_to_task_spec`, `get_response_directive`

**From `planning_workflow.py`**: `get_active_directive`, `apply_directive_to_task_spec`, `inject_skill_to_task`

**From API layer** (`signals.py`, `aurora.py`, `_experience.py`): `get_status_band_summary`, `get_rendered_timeline`, `handle_user_receipt_action`, `set_source_tray_selection`, `get_source_tray_state`, `start_aurora_core_session`, `process_aurora_reply`, `close_aurora_session`, `pause_aurora_session`, `resume_aurora_session`, `check_aurora_session_health`

**From event consumers**: `on_task_completed`, `on_achievement_event`, `on_mistake_event`, `on_file_uploaded`, `on_recall_check`, `build_recall_notification`, `on_user_return`, `on_absence_detected`

**From Celery tasks**: `build_recall_notification`, `record_outcome`, `record_strategy_outcome`

### 3.4 Redundant Methods

| Method | Issue |
|--------|-------|
| `_store_response_directive` | 1-line delegate to `directive_store.store_response` -- no added value |
| `_store_notification_directive` | Same -- pure delegation |
| `_store_retrieval_directive` | Same -- pure delegation |
| `_store_plan_directive` | Same -- pure delegation |
| `_store_model_write_directive` | Same -- pure delegation |
| `_store_ux_directive` | Same -- pure delegation |

These 6 methods exist solely to forward to `self.directive_store`. They can be inlined at call sites.

---

## 4. Interaction with Other Spine Components

### 4.1 Dependency Graph

```
SpineOrchestrator.__init__ instantiates 40 dependencies:
  |
  +-- Core Storage
  |     CausalTraceStore(redis)
  |     DirectiveStore(redis, trace_store)
  |     CardStore(redis, community_loops)
  |     StateRegister(redis)
  |
  +-- Signal Detection (7 detectors)
  |     TaskTimeoutDetector, MistakeSignalDetector, AchievementReinforcementConsumer,
  |     RecallOpportunityDetector, ExamRescueDetector, NonExamFirstMinuteDetector,
  |     MaterialSignalDetector, CommunitySignalDetector, AbsenceDetector
  |
  +-- Policy & Evaluation
  |     PolicyEngine(reply_engine), SignalRanker(state_register), PolicyAnalytics(redis),
  |     PolicyExperimentManager(redis), ExamSprintPolicyService, GoalTypeAdapter
  |
  +-- Aurora Runtime
  |     AuroraCoreSessionService, L3FullCoreEngine, L0RuleEngine, L1LightAurora,
  |     AuroraInputAssembler, AuroraOutputArbitrator, AuroraSelfCorrector,
  |     AuroraSelfModelAccessor, EnergyLevelDecider
  |
  +-- Outcome & Learning
  |     OutcomeRecorder, OutcomeTracker, OutcomeConsumingService,
  |     LearningBase, LearningGuard, SkillExtractionService, SkillLifecycleManager
  |
  +-- Social & Community
  |     CommunityLoopManager, RelationshipModelService, PartnerCommitmentLoop
  |
  +-- Presentation
  |     SpineReplyOptionEngine, TimelineCardRenderer, SpineMetricsCollector,
  |     ActionableStatePacketBuilder
  |
  +-- Governance
  |     CitationValidator, LowYieldGuard, fabrication_scanner,
  |     SafetyDegradationManager, HighImpactConfirmationFramework, ResearchIsolationGuard
  |
  +-- Goal Management
  |     GoalWorldGraphService, MultiGoalArbitrator, GrowthChronicleService
  |
  +-- Other
  |     CoreSessionManager, SparkleSelfModelService, CorrectionFeedbackProcessor,
  |     SourceEffectivenessTracker, StaleStateGuard
```

### 4.2 Interaction Patterns

**Good Patterns**:
1. **DirectiveStore delegation**: Directive persistence is properly delegated (previously extracted from God class)
2. **Circuit breaker**: `redis_resilience.resilient_redis_call` wraps critical pipeline steps
3. **Concurrency guard**: Pipeline lock prevents concurrent pipeline runs per user (`spine:pipeline_lock:{user_id}`)

**Problematic Patterns**:
1. **Direct Redis calls in orchestrator**: The class makes ~60 direct `self.redis.*` calls outside of its delegated stores. These should go through `resilient_redis_call` consistently.
2. **Late imports**: 15+ methods use inline `import json` or late imports inside method bodies (e.g., L2266 `from app.signals.external_integration import ...`). This hides dependency relationships and hurts startup performance.
3. **Circular risk**: `close_aurora_session` creates synthetic `ActionableSignal`s and calls `self.policy_engine.evaluate()` which could trigger another pipeline run if not guarded.
4. **Double-write**: `arbitrate_goals` calls `trace_store._save_trace` and `link_to_user` TWICE (lines 4817-4820) -- a clear bug.

### 4.3 State Register Coupling

The class accesses `StateRegister` through 4 patterns:
1. `state_register.upsert_from_signal(user_id, signal)` -- write
2. `state_register.get_active_states(user_id)` -- read all
3. `state_register.get_state(user_id, key)` -- read single
4. `state_register._save_state(user_id, entry)` -- direct write (in `recover_from_snapshot`, line 4670)

The last pattern (`_save_state`) accesses a private method of another class, breaking encapsulation.

---

## 5. Performance Hotspot Analysis

### 5.1 Hot Path: `_run_signal_pipeline` (Lines 1316-1746, 430 lines)

This method is called for EVERY actionable signal. It performs:

| Step | Redis Ops | Estimated Latency |
|------|-----------|-------------------|
| Lock acquisition | 1 SET NX | ~1ms |
| Interaction counter | 1 INCR + conditional EXPIRE | ~1ms |
| Create trace | 1 SET (via trace_store) | ~1ms |
| Link to user | 1 RPUSH | ~1ms |
| Store signal | 1 SET | ~1ms |
| L0 rule evaluation | Multiple reads + writes | ~5-10ms |
| Signal ranking | In-memory | ~0.1ms |
| L2 escalation check | 1 read (state) | ~1ms |
| Load recent effects | 1 LRANGE | ~1ms |
| Load strategy beliefs | 1 GET | ~1ms |
| Consume Aurora decisions | 1 LRANGE | ~1ms |
| Load distilled strategies | 1+ reads | ~2ms |
| Policy engine evaluate | In-memory | ~1ms |
| **Store 7 directives** | **7 SET** | **~7ms** |
| Build receipt | 2 SET | ~2ms |
| Enrich pipeline post-policy | **11 independent Redis operations** | **~15-25ms** |
| Record outcome | ~10 Redis ops | ~10ms |
| Release lock | 1 DEL | ~1ms |
| **TOTAL** | **~30-40 Redis ops** | **~50-70ms** |

### 5.2 Critical Bottleneck: `_enrich_pipeline_post_policy` (Lines 3233-3498, 265 lines)

This single method runs **11 independent enrichment steps** sequentially. Each step has its own `except Exception` guard. Estimated latency: 15-25ms of pure Redis I/O.

**Recommendation**: Run enrichment steps concurrently using `asyncio.gather()` with `return_exceptions=True`. This could reduce enrichment latency from ~20ms to ~3ms (the slowest single step).

### 5.3 Sequential Directive Storage

Lines 1570-1653 store 7 directive types sequentially:
```python
await self.directive_store.store_response(user_id, response_dir)
# ... fabrication scan, citation validation ...
await self.directive_store.store_notification(user_id, notif_dir)
await self.directive_store.store_retrieval(user_id, ret_dir)
await self.directive_store.store_plan(user_id, plan_dir)
await self.directive_store.store_model_write(user_id, mw_dir)
await self.directive_store.store_ux(user_id, ux_dir)
await self._store_community_directive(user_id, comm_dir)
await self._store_skill_directive(user_id, skill_dir)
```

These are independent and can be parallelized with `asyncio.gather()`.

### 5.4 `get_rendered_timeline` N+1 Pattern

Lines 577-715: For each trace, it makes 5-6 individual Redis GET calls. With `limit=10`, that is 50-60 Redis round trips.

**Recommendation**: Use Redis pipeline (MULTI/EXEC or `redis.pipeline()`) to batch all reads per trace.

---

## 6. State Management & Thread Safety

### 6.1 Instance State

The class holds **no mutable state** beyond its `__init__` dependencies. All state is externalized to Redis. This is architecturally sound -- the class is effectively stateless once constructed.

### 6.2 Singleton Pattern

```python
_spine_orchestrator: SpineOrchestrator | None = None

def get_spine_orchestrator(redis_client=None) -> SpineOrchestrator:
    global _spine_orchestrator
    if _spine_orchestrator is None:
        _spine_orchestrator = SpineOrchestrator(redis_client=redis_client)
    return _spine_orchestrator
```

**Issue**: This singleton is **not thread-safe**. In an async context with multiple event loops or when used from Celery workers, this could lead to:
1. Race conditions during initialization
2. Multiple instances if `redis_client` differs between calls
3. Stale instance if Redis reconnects

**Fix**: Use `functools.lru_cache` or `threading.Lock` for initialization.

### 6.3 Concurrency Model

The class uses Redis-based locks for concurrency control:
- `spine:pipeline_lock:{user_id}` -- prevents concurrent pipeline execution (30s TTL)
- `spine:task_completed_lock:{user_id}` -- prevents concurrent post-processing (15s TTL)

**Issue 1**: Lock acquisition uses `redis.set(key, "1", nx=True, ex=30)` without retry. If the lock is held, the pipeline is silently skipped (`return None`). For hot paths like `on_chat_turn`, this means signals can be dropped.

**Issue 2**: Lock release in `_run_signal_pipeline` is inside a `try/except` that catches the error but does not retry. If the DEL fails, the lock expires after 30s, which is acceptable but creates a 30s dead zone for that user.

**Issue 3**: The lock TTL (30s) may be insufficient for `_enrich_pipeline_post_policy` which chains 11 enrichment steps. Under Redis latency spikes, the pipeline could exceed 30s, causing the lock to expire while the pipeline is still running -- leading to concurrent pipeline execution.

---

## 7. Specific Bugs Found

### 7.1 Double Write in `arbitrate_goals` (Lines 4817-4820)

```python
await self.trace_store._save_trace(trace)
await self.trace_store.link_to_user(user_id, trace.trace_id)
await self.trace_store._save_trace(trace)      # DUPLICATE
await self.trace_store.link_to_user(user_id, trace.trace_id)  # DUPLICATE
```

### 7.2 Missing `exc_info=True` in Multiple Locations

These locations log exceptions without stack traces, making debugging impossible:

| Line | Method | Current | Fix |
|------|--------|---------|-----|
| 2578 | `get_recall_notification` | `logger.debug(...)` | Add `exc_info=True` |
| 4602 | `save_spine_snapshot` | `logger.warning(...)` | Already has `exc_info=True` -- OK |
| 1347 | `_run_signal_pipeline` | `classify_error` only | OK (classified) |

### 7.3 Inconsistent Error Classification

The class uses `classify_error` from `app.core.error_taxonomy` in only 4 of 103 exception handlers. The remaining 99 use bare `except Exception`. A consistent approach would improve observability.

### 7.4 `_run_live_quality_guard` Called Twice Per Pipeline

1. Line 1702: `await self._run_live_quality_guard(trace)` -- on the single trace
2. Line 3411-3434 (inside `_enrich_pipeline_post_policy`): Loads 20 traces and runs `SpineQualityGuard` on all of them

The first call validates the current trace. The second re-validates the current trace plus 19 historical ones. This is redundant for the current trace.

---

## 8. Code Quality Issues

### 8.1 Method Length Violations

| Method | Lines | Recommended Max |
|--------|-------|-----------------|
| `_run_signal_pipeline` | 430 | 80 |
| `_enrich_pipeline_post_policy` | 265 | 80 |
| `record_outcome` | 180 | 80 |
| `get_rendered_timeline` | 138 | 80 |
| `get_status_band_summary` | 108 | 80 |
| `build_experience_envelope` | 104 | 80 |
| `close_aurora_session` | 105 | 80 |
| `start_aurora_core_session` | 60 | OK |

### 8.2 Repeated Patterns

**Pattern: `json.loads(raw if isinstance(raw, str) else raw.decode())`** appears **17 times**. This should be extracted to a utility:

```python
def _redis_json_load(raw: bytes | str | None) -> dict | None:
    if raw is None:
        return None
    return json.loads(raw if isinstance(raw, str) else raw.decode())
```

**Pattern: "Store to Redis with TTL"** appears ~25 times. Consider a helper:

```python
async def _set_json(self, key: str, data: dict, ttl_seconds: int) -> None:
    await self.redis.set(key, json.dumps(data), ex=ttl_seconds)
```

### 8.3 Import Hygiene

- `import json` appears **inline in 22 methods** instead of at module level. This is a micro-optimization that hurts readability.
- Late imports like `from app.services.galaxy_service import GalaxyService` inside `on_file_uploaded` hide true dependencies.
- `from app.aurora.runtime_v1.state import AuroraEnergyStore` is imported inside `_compute_6state_band` on every call.

---

## 9. Recommendations Summary

### P0 -- Fix Now

| # | Issue | Effort | Impact |
|---|-------|--------|--------|
| P0-1 | Fix double-write in `arbitrate_goals` (L4817-4820) | 1 line | Correctness |
| P0-2 | Add `exc_info=True` to 3 silent exception handlers | 3 lines | Observability |
| P0-3 | Make singleton initialization thread-safe | 5 lines | Correctness |

### P1 -- Next Sprint

| # | Issue | Effort | Impact |
|---|-------|--------|--------|
| P1-1 | Extract `SpinePresentationService` (status bands, envelopes, timeline, cards) | ~500 lines | Maintainability |
| P1-2 | Parallelize `_enrich_pipeline_post_policy` with `asyncio.gather` | ~20 lines | Performance (3-5x) |
| P1-3 | Parallelize directive storage with `asyncio.gather` | ~15 lines | Performance (2-3x) |
| P1-4 | Extract `_redis_json_load` utility, deduplicate 17 call sites | ~30 lines | DRY |
| P1-5 | Give enrichment exception blocks unique log messages | ~15 lines | Observability |
| P1-6 | Remove 6 redundant `_store_*_directive` delegate methods | ~30 lines | Surface reduction |

### P2 -- Strategic

| # | Issue | Effort | Impact |
|---|-------|--------|--------|
| P2-1 | Extract `OutcomeLearningService` (outcome + beliefs + counterfactual) | ~350 lines | Testability |
| P2-2 | Extract `CommunityIntegrationService` (all community methods) | ~250 lines | Cohesion |
| P2-3 | Extract `GoalManagementService` (goal OS methods) | ~200 lines | Cohesion |
| P2-4 | Move inline imports to module level | ~50 lines | Readability |
| P2-5 | Batch Redis reads in `get_rendered_timeline` using pipeline | ~30 lines | Performance |
| P2-6 | Introduce `SpineException` hierarchy for selective exception handling | ~100 lines | Correctness |

---

## 10. Metric Summary

| Metric | Value | Assessment |
|--------|-------|------------|
| Total lines | 4,950 | CRITICAL (target: <1,000 per class) |
| Public methods | 88 | CRITICAL (target: <20) |
| Private methods | 37 | HIGH |
| Dependencies injected | ~40 | CRITICAL |
| `except Exception` blocks | 103 | HIGH (mostly justified, 3 problematic) |
| Direct Redis calls | ~60 | HIGH (should use resilient wrappers) |
| Methods > 80 lines | 8 | HIGH |
| Actual external API surface | ~30 | Misaligned with 88 public methods |
| Thread safety | No | P0 for singleton |
| Testability (isolated) | Near impossible | CRITICAL |

**Overall Assessment**: SpineOrchestrator is a well-intentioned hub that grew organically as more capabilities were wired into the Spine. The enrichment pattern (best-effort, non-blocking) is architecturally sound. However, the class has crossed the threshold where incremental additions create more technical debt than value. The decomposition proposed in Section 1.2 would reduce the class to ~500 lines (a true facade) while distributing responsibility across 8 focused services.
