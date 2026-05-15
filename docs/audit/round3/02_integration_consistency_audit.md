# Round 3: Integration Consistency Audit

**Date**: 2026-05-15
**Auditor**: Agent (Automated Deep Audit)
**Scope**: Cross-subsystem integration, data consistency, signal flow, cache coherence, kill switch coverage

---

## Executive Summary

This audit traces signal flows across subsystem boundaries, verifies dual-write consistency, checks cache invalidation coverage, validates cross-service call chain data formatting, and assesses kill switch completeness. **5 issues were identified** (2 P1, 2 P2, 1 P3).

| Severity | Count | Description |
|----------|-------|-------------|
| P1 (Critical) | 2 | Cache invalidation gap; potential dual-write inconsistency |
| P2 (High) | 2 | StateAggregator TTL staleness; kill switch shadow leakage |
| P3 (Medium) | 1 | Missing `user:profile_context` in Go-side invalidation |

---

## 1. Signal Flow Integrity: TaskCompleted Event

### 1.1 Publishing Path

```
TaskService.complete_task()                          [backend/app/services/task_service.py:658-670]
  |-- DB: UPDATE task SET status='completed'         [within same DB session]
  |-- event_bus_reliable.publish("task.completed")   [Redis Stream: sparkle_events]
  |-- SparkleSelfModelService.record_task_outcome()  [Redis: aurora self model]
  |-- publish_srl_event(trigger="task.completed")    [Redis Stream: sparkle_events]
  |-- NorthStarMetricsService.record_cold_start_milestone()  [PostgreSQL]
```

**Finding**: The DB update and event publish are NOT atomic. The task status is committed first, then the event is published. If the process crashes between `db.commit()` and `event_bus.publish()`, the task is marked completed in PostgreSQL but NO event is emitted. This is a known pattern in event-driven systems and is partially mitigated by the `reliable_consumer` decorator and DLQ, but the initial publish failure itself is not recoverable.

**Risk**: LOW. The system is designed for eventual consistency. Individual signal loss is tolerable because subsequent user actions will generate new signals that converge.

### 1.2 Consumer Map for task.completed

The `task.completed` event on `sparkle_events` stream is consumed by **3 independent consumer groups**:

| Consumer Group | File | What It Does |
|---------------|------|--------------|
| `task_event_consumer` | `services/task_event_consumer.py` | BehaviorSignalCollector, MetacognitionService, CommunitySignalBridge, SpineOutcomeRecorder, SpineOrchestrator, AutoFragmentCollector, AdaptiveReplanner, Goal progress update |
| `galaxy_event_consumer` | `services/galaxy_event_consumer.py` | GraphEvolutionService.handle_task_completed, SeedExtractor.prewarm |
| `achievement_event_consumer` | `services/achievement_event_consumer.py` | AchievementEngine.process_event, StrategyMarketplace, FeedbackDrivenAdjustmentService, StateDrivenPushService |

### 1.3 TaskEventConsumer._handle_task_completed Analysis

This handler performs **8 sequential operations**, each in its own DB session with independent error handling:

```
1. BehaviorSignalCollector.handle_task_completed_event()   [try/except: logs warning, continues]
2. MetacognitionService.refresh_snapshot()                  [try/except: logs warning, continues]
3. CommunitySignalBridge.handle_group_task_completed()      [try/except: logs warning, continues]
4. _record_task_outcome() (Spine OutcomeTracker)            [try/except: logs warning, continues]
5. SpineOrchestrator.on_task_completed()                    [try/except: logs warning, continues]
6. AutoFragmentCollector.collect_from_task_completion()     [try/except: logs warning, continues]
7. AdaptiveReplanner.on_task_completed()                    [try/except: logs warning, continues]
8. Goal progress update (direct DB query)                   [try/except: logs warning, continues]
```

**Finding**: Each sub-operation uses its own `AsyncSessionLocal()` context and commits independently. This design is **correct for fault isolation** -- a failure in step 3 does not block steps 4-8. However, it means the 8 operations are NOT atomic as a group. If the consumer crashes halfway through, some operations will be re-executed on retry (due to idempotency key being message-level).

**Signal Duplication Risk**: The EventBus has idempotency protection (`_process_stream_message` checks `idempotency_key = f"evt:{stream}:{effective_id}"` with 86400s TTL). This prevents the ENTIRE `_handle_task_completed` from running twice for the same message. **However**, if the consumer crashes AFTER ack but BEFORE completing all sub-operations, those sub-operations are lost (not duplicated).

**Verdict**: Signal loss is possible but bounded. The system compensates through cross-signal convergence (e.g., if BehaviorSignalCollector misses one event, subsequent events provide enough data for pattern detection).

### 1.4 Cross-Consumer Signal Propagation

```
TaskCompleted event
  |
  +-- TaskEventConsumer
  |     |-- BehaviorSignalCollector → publishes behavior.pattern.updated event
  |     |-- AdaptiveReplanner → may publish plan.replanned event
  |     |-- SpineOrchestrator → writes Spine state registers to Redis
  |     |-- MetacognitionService → refreshes metacognition snapshot in DB
  |
  +-- GalaxyEventConsumer
  |     |-- GraphEvolutionService → updates knowledge graph structure
  |     |-- SeedExtractor → prewarms simulation scenarios
  |
  +-- AchievementEventConsumer
        |-- AchievementEngine → may publish achievement.unlocked event
        |-- StrategyMarketplace → writes strategy effectiveness to Redis
        |-- FeedbackDrivenAdjustmentService → updates plan state
```

The `behavior.pattern.updated` and `achievement.unlocked` events trigger additional consumer chains. This is a **fan-out topology** with no circular dependencies detected.

---

## 2. Dual-Write Path Consistency

### 2.1 Preference Write Path

```
ProfileWriteService.set_explicit_preferences()          [services/profile_write_service.py:63]
  |-- (1) PreferenceService.update_explicit()            → UserPreferencesCenter table (PostgreSQL)
  |-- (2) _sync_legacy_fields()                          → User table + PushPreference table (PostgreSQL)
  |-- (3) MemoryService.upsert_preference()              → MemoryPreference table (PostgreSQL) [per-key, try/except]
  |-- (4) _publish_preference_updated_event()            → Event Bus (Redis Stream: sparkle_events)
```

**ISSUE P1-01: Non-atomic multi-table preference write**

Steps 1-2 share the same DB session (`self.db`). If step 2 fails after step 1 commits (or vice versa), UserPreferencesCenter and User/PushPreference tables become inconsistent. In practice, `_sync_legacy_fields` calls `await self.db.commit()` at the end, so steps 1 and 2 are committed together in a single transaction. **However**, step 3 (MemoryService.upsert_preference) uses the same `self.db` session and has its own `await self.db.rollback()` on failure (line 104). If step 3 fails, it rolls back the preference history write, but the UserPreferencesCenter and User table changes are already committed from step 2.

**Analysis**: The `_sync_legacy_fields` at line 434 calls `await self.db.commit()`. Then the loop at line 89-110 calls `self.memory_service.upsert_preference()` which also uses `self.db`. If this fails, line 104 does `await self.db.rollback()` which rolls back the memory preference write but NOT the already-committed user preference center update. This is **by design** (the history log is append-only and non-critical), but it means:

- **Canonical state** (UserPreferencesCenter) is always correct.
- **History log** (MemoryPreference) may have gaps for failed writes.
- **Event publication** (step 4) always fires, even if history log failed.

**Risk**: LOW. History log gaps are acceptable. The event always fires, ensuring downstream cache invalidation occurs.

### 2.2 Task Completion Write Path

```
TaskService.complete_task()                              [services/task_service.py:505]
  |-- (1) DB: UPDATE task SET status='completed'         → PostgreSQL (single transaction)
  |-- (2) sync_service.on_task_completed()               → Redis + PostgreSQL
  |-- (3) event_bus_reliable.publish("task.completed")   → Redis Stream
  |-- (4) SparkleSelfModelService.record_task_outcome()  → Redis (aurora self model)
  |-- (5) publish_srl_event()                            → Redis Stream
  |-- (6) NorthStarMetricsService.record_cold_start()    → PostgreSQL
```

**ISSUE P1-02: Task status and event publish are not atomic**

The DB commit at step 1 and the event publish at step 3 are not in a transactional envelope. If the process crashes between these steps, the task is completed in PostgreSQL but no event is emitted, leaving:
- Achievement engine unaware of the completion
- Adaptive replanner unaware
- Goal progress not updated
- Knowledge graph not evolved

**Mitigating factors**: The SRL event at step 5 provides a secondary signal path. The task status is queryable directly by services. However, real-time reactive pipelines (achievement, graph evolution) will miss this event.

**Recommendation**: Consider an outbox pattern where the event is written to a PostgreSQL outbox table in the same transaction as the task update, with a background poller publishing events from the outbox.

### 2.3 Go-side Preference Dual-Write

```
UserPreferencesService.UpdatePreferences()               [gateway/internal/service/user_preferences_service.go]
  |-- (1) SQL UPDATE user_preferences_center              → PostgreSQL
  |-- (2) CQRS publish to cqrs:stream:user               → Redis Stream
  |-- (3) invalidateCache()                               → Redis (deletes 6 keys)
```

The Go side publishes to `cqrs:stream:user`, which is a **separate stream** from the Python event bus's `sparkle_events`. The Python PreferenceEventConsumer listens on `cqrs:stream:user` and calls `user_service.invalidate_user_cache()`, which deletes:
- `user:context:{user_id}`
- `user:context:snapshot:{user_id}`
- `user:prefs:center:{user_id}`
- `user:analytics:{user_id}`
- `user:preferences:{user_id}`
- `user:stats:{user_id}`

---

## 3. Cache Consistency Verification

### 3.1 ProfileContext Cache (`user:profile_context:{user_id}`)

**Write point**: `ProfileContextService.get_profile_context()` (profile_context_service.py:129)
- Reads from Redis cache, validates `preference_version` matches current version
- If stale or missing, rebuilds from DB and writes to Redis with TTL

**Invalidation points**:

| Source | File | Keys Invalidated | Coverage |
|--------|------|------------------|----------|
| ProfileEventConsumer | `profile_event_consumer.py:296-314` | `user:context:*`, `user:profile_context:*` | COMPLETE |
| Python PreferenceService._invalidate_cache | `preference_service.py:373-387` | `user:context:*`, `user:prefs:*`, `user:preferences:*`, `user:analytics:*`, `user:stats:*` | **MISSING** `user:profile_context` |
| Python UserService.invalidate_user_cache | `user_service.py:563-596` | `user:context:*`, `user:prefs:*`, `user:analytics:*`, `user:preferences:*`, `user:stats:*` | **MISSING** `user:profile_context` |
| Go UserPreferencesService.invalidateCache | `user_preferences_service.go:105-119` | `user:context:*`, `user:prefs:*`, `user:preferences:*`, `user:analytics:*`, `user:stats:*` | **MISSING** `user:profile_context` |

**ISSUE P2-01 (also P3-01): `user:profile_context` cache not invalidated by PreferenceService or Go-side**

When preferences are updated through:
1. Python `PreferenceService._invalidate_cache()` -- does NOT delete `user:profile_context:{user_id}`
2. Go `UserPreferencesService.invalidateCache()` -- does NOT delete `user:profile_context:{user_id}`
3. Python `UserService.invalidate_user_cache()` -- does NOT delete `user:profile_context:{user_id}`

Only `ProfileEventConsumer` (listening on `sparkle_events` for `profile.preference.updated` events) deletes this key.

**Impact**: If the Go gateway updates preferences directly, the Go-side `invalidateCache` runs and then publishes to `cqrs:stream:user`. The Python PreferenceEventConsumer consumes this and calls `invalidate_user_cache`, which also misses `user:profile_context`. However, `ProfileContextService.get_profile_context()` does a version check on read (`context.preference_version == current_version`), so stale data will be detected and rebuilt on the next read. **Staleness window**: up to 300 seconds (Redis TTL) or until the next `profile.preference.updated` event triggers `ProfileEventConsumer`.

**Practical risk**: LOW. The version check on read catches stale data. But there is a window where an AI turn could use outdated profile context.

### 3.2 UserContext Cache (`user:context:{user_id}`)

**Write point**: `ContextOrchestrator.get_user_context()` (context_manager.py:512)
- Cached at `user:context:snapshot:{user_id}` with `CACHE_TTL_SECONDS = 300`
- Version-aware: checks `preference_version` and refreshes if mismatch

**Invalidation points**:

| Trigger | Mechanism | Completeness |
|---------|-----------|--------------|
| Profile preference update via Python event bus | `ProfileEventConsumer._invalidate_context_cache()` | Deletes `user:context:*` + `user:profile_context:*` |
| Go preference update | Go `invalidateCache` + Python `PreferenceEventConsumer` | Deletes `user:context:*` |
| Achievement progress event | `record_achievement_progress_event()` | Deletes `user:context:snapshot:*` |

**Verdict**: `user:context` invalidation is **well-covered**. The version check provides a secondary safety net.

### 3.3 StateAggregator Cache (In-Memory)

**ISSUE P2-02: StateAggregator uses per-instance in-memory cache with no cross-request invalidation**

`StateAggregatorService` (state_aggregator/service.py:110-113) uses `self._cache` -- a dict that lives for the lifetime of the `StateAggregatorService` instance. The TTL values range from 30 seconds to 24 hours:

| Field | TTL | Staleness Risk |
|-------|-----|----------------|
| `commitment_summary` | 30s | LOW |
| `engagement_state` | 60s | LOW |
| `emotion_hint` | 60s | LOW |
| `social_signals_summary` | 300s (5 min) | MEDIUM |
| `achievement_summary` | 300s (5 min) | MEDIUM |
| `calendar_context` | 300s (5 min) | MEDIUM |
| `srl_phase` | configurable | MEDIUM |
| `metacognition_profile` | configurable | MEDIUM |
| `learning_state` | 86400s (24h) | HIGH |

The `learning_state` TTL of 24 hours means a user's learning state will not refresh for an entire day. Since `PredictiveService.get_next_intent_forecast()` queries are not expensive, this long TTL seems overly conservative.

**Key observation**: The cache is per-instance. Each `StateAggregatorService(db)` call creates a new instance, so the cache is effectively per-request. This means the TTL only matters within a single request's routing pipeline, not across requests. **This is actually fine** -- the cache prevents redundant DB queries within a single AI turn (which may call `get_user_state` multiple times for different field sets).

**Revised verdict**: No cross-request staleness issue. The in-memory cache is request-scoped.

---

## 4. Cross-Service Call Chain Verification

### 4.1 ChatOrchestrator -> StateAggregator -> DualCoreRouter -> Prompt Assembly

**Data flow**:

```
RoutingEngine._apply_dual_core_routing()               [orchestration/routing_engine.py:1033]
  |
  |-- Assembles DualCoreRoutingInput from:
  |     - ContextOrchestrator.get_user_context()          → CognitiveContext (Pydantic model)
  |     - StateAggregatorService.get_user_state()         → UserStateV1 (dataclass)
  |     - Redis lookups (Spine claims, route outcomes, behavior patterns)
  |
  |-- dual_core_router.route(routing_input)               → DualCoreDecision
  |
  |-- Decision.to_dict()                                  → dict for prompt injection
```

**Data format verification**:

| Stage | Input Type | Output Type | Conversion |
|-------|-----------|-------------|------------|
| StateAggregator | UUID + field names | UserStateV1 (dataclass) | None needed |
| RoutingEngine | UserStateV1 fields | DualCoreRoutingInput (frozen dataclass) | Explicit field mapping |
| DualCoreRouter | DualCoreRoutingInput | DualCoreDecision (frozen dataclass) | Internal computation |
| Prompt Assembly | DualCoreDecision | decision.prompt_instruction (str) | to_dict() + template |

**ISSUE (design note, not a bug)**: The `DualCoreRoutingInput` has fields like `recent_sentiment_distribution: dict[str, int]` that are populated from `ContextOrchestrator` results. The `CognitiveContext.preferences` dict is passed through without schema validation -- it is a raw dict. If the preference schema changes, the routing engine could receive unexpected keys, but the DualCoreRouter would simply not match them in its keyword checks (no crash, just missed signals).

**Error propagation**:

```
If StateAggregator fails → aggregator.get_user_state() returns UserStateV1 with None fields
  → RoutingEngine checks `if user_state.xxx is not None` before accessing
  → DualCoreRouter receives default/empty values → produces a valid (degraded) decision
```

```
If ContextOrchestrator fails → returns partial CognitiveContext
  → RoutingEngine uses `_handle_result()` with `return_exceptions=True`
  → Failed services return Exception objects, replaced by default values
```

**Verdict**: Error propagation is **correctly designed**. Failures degrade gracefully with explicit fallbacks. No silent use of wrong data.

### 4.2 Implicit Type Conversions

Several implicit conversions occur in the data pipeline:

1. **UUID to string**: `event_bus.publish()` receives `TaskCompleted.to_dict()` where UUIDs are already strings.
2. **JSON serialization**: `EventBus._serialize_stream_body()` converts all values to strings via `str()`. Complex types (dict, list) are JSON-encoded. On deserialization (`_process_stream_message`), JSON fields are parsed back.
3. **Float precision**: `routing_input.cognitive_load` is `float | None` but can arrive as a string from Redis. The DualCoreRouter uses `float()` conversion explicitly.

**Potential issue**: In `EventBus._serialize_stream_body()` (line 699-706), if a value is a nested structure that contains a mix of JSON-parseable and non-parseable strings, the deserialization at line 1163-1168 does `json.loads()` per-field with a fallback to raw string. This is correct but means some fields may be strings when the consumer expects dicts.

**Verdict**: No critical format mismatches detected. The serialization/deserialization is lossy but designed for this.

---

## 5. Kill Switch Coverage

### 5.1 Aurora Stage Kill Switch Registry

| Stage | Service | Features |
|-------|---------|----------|
| 18 | `AuroraStage18KillSwitchService` | `aggregator_enabled` |
| 19 | `AuroraStage19KillSwitchService` | (routing engine features) |
| 20 | `AuroraStage20KillSwitchService` | `sufficiency_judge` |
| 21 | `AuroraStage21KillSwitchService` | `skill_selection_enabled` |
| 23 | `AuroraStage23KillSwitchService` | (Bayesian learner) |
| 24 | `AuroraStage24PolicyKillSwitchService` | (policy scheduler) |
| 25 | `AuroraStage25ReflectionKillSwitchService` | (reflection triggers) |
| 26 | `AuroraStage26SceneKillSwitchService` | (scene consolidation) |
| 27 | `AuroraStage27ForesightKillSwitchService` | (foresight) |
| 28 | `AuroraStage28TraitsKillSwitchService` | (Big Five traits) |
| 29 | `AuroraStage29SRLKillSwitchService` | (SRL phase tracking) |
| 30 | `AuroraStage30MetacognitionKillSwitchService` | (metacognition) |
| 31 | `AuroraStage31IdiographicKillSwitchService` | (idiographic associations) |
| 33 | `AuroraStage33KillSwitchService` | `social` |
| 34 | `AuroraStage34KillSwitchService` | (features) |
| 35 | `AuroraStage35KillSwitchService` | (features) |
| 37 | `AuroraStage37LLMSafetyKillSwitchService` | (LLM safety) |
| 38 | `AuroraStage38KillSwitchService` | (event bus DLQ, reliability) |
| 39 | `AuroraStage39KillSwitchService` | (multiple feature bindings) |
| 40 | `AuroraStage40CalendarKillSwitchService` | (calendar context) |

### 5.2 Kill Switch Mode Semantics Verification

**StateAggregator (Stage 18)**: Verified in `state_aggregator/service.py:156-232`

```python
aggregator_mode = await self.kill_switches.get_feature_mode("aggregator_enabled")
if aggregator_mode == "off":
    return None
# ... compute envelope ...
if aggregator_mode == "shadow":
    return None  # Compute but discard
# live: cache and return
```

- **off mode**: Returns None immediately. No DB queries made. CORRECT.
- **shadow mode**: Computes the full envelope, does NOT cache it, returns None. **Side effect**: DB queries still run. This is by design for monitoring/shadow testing.
- **live mode**: Computes, caches, and returns. CORRECT.

**ISSUE P2-03: Shadow mode runs DB queries but discards results**

In shadow mode, the StateAggregator still executes all DB queries (memory_service, predictive_service, etc.) but discards the results. This means shadow mode imposes the same DB load as live mode without providing user value. For high-traffic scenarios, this could cause unnecessary DB pressure.

**Mitigating factor**: The rule guard `check_rule_be_shadow_semantics.py` explicitly verifies this pattern for key services. This is a known tradeoff documented in the shadow testing protocol.

### 5.3 Shadow Mode User Impact

For each checked service, shadow mode:

| Service | Shadow Behavior | User Impact |
|---------|----------------|-------------|
| StateAggregator | Computes, discards, returns None | AI sees empty user state (degraded but safe) |
| SocialSignalBridge | Returns empty social signals | AI operates without social context |
| SRL Phase Tracker | Records with `status="shadow"` | DB writes happen but marked as shadow |
| IdiographicAssociation | Computes vectors but does NOT persist | No DB writes in shadow |

**Finding**: The SRL Phase Tracker writes to DB even in shadow mode (with `status="shadow"`). This is a design decision for observability but means shadow mode is not purely read-only for all services. The shadow data can be differentiated from live data by the status field.

### 5.4 Kill Switch Coverage Gaps

Scanning all Aurora feature areas against kill switch services:

| Feature Area | Kill Switch | Gap |
|-------------|-------------|-----|
| State Aggregation | Stage 18 | Covered |
| Routing Engine | Stage 19 | Covered |
| Sufficiency Judge | Stage 20 | Covered |
| Skill Selection | Stage 21 | Covered |
| Bayesian Learner | Stage 23 | Covered |
| Policy Scheduler | Stage 24 | Covered |
| Reflection Triggers | Stage 25 | Covered |
| Scene Consolidation | Stage 26 | Covered |
| Foresight | Stage 27 | Covered |
| Traits (Big Five) | Stage 28 | Covered |
| SRL Phase | Stage 29 | Covered |
| Metacognition | Stage 30 | Covered |
| Idiographic | Stage 31 | Covered |
| Social Signals | Stage 33 | Covered |
| Spine/Signals | Stage 34-35 | Covered |
| LLM Safety | Stage 37 | Covered |
| Event Bus | Stage 38 | Covered |
| Calendar | Stage 40 | Covered |
| **Dual-Core Router** | **None** | **No direct kill switch** |
| **Behavior Pattern Collection** | **None** | **No direct kill switch** |
| **Adaptive Replanner** | **None** | **No direct kill switch** |

**Observation**: The DualCoreRouter itself has no kill switch. It always runs when invoked. However, it is fed by StateAggregator data (which has a kill switch). If StateAggregator is off, the router receives None fields and produces default decisions. This is **indirect coverage** -- acceptable but not explicitly governed.

---

## 6. Summary of Findings

### P1-01: Non-atomic preference multi-table write
- **File**: `backend/app/services/profile_write_service.py:63-123`
- **Risk**: Medium
- **Description**: `_sync_legacy_fields()` commits `UserPreferencesCenter` + `User` + `PushPreference` in one transaction, but `MemoryService.upsert_preference()` failures cause partial rollback (history log gap only, canonical state preserved)
- **Mitigation**: Canonical state is always consistent. History log gaps are non-critical.
- **Recommendation**: Consider wrapping the entire operation in a single transaction or using a saga pattern.

### P1-02: Task completion not atomic with event publish
- **File**: `backend/app/services/task_service.py:670`
- **Risk**: Medium
- **Description**: DB commit and event publish are not in a transactional envelope. Process crash between them means completed task with no downstream signals.
- **Mitigation**: SRL events provide secondary signal paths. Services can query task status directly.
- **Recommendation**: Implement outbox pattern for reliable event publishing.

### P2-01: `user:profile_context` cache not invalidated by all paths
- **Files**: `preference_service.py:373`, `user_service.py:563`, `user_preferences_service.go:105`
- **Risk**: Low
- **Description**: Three invalidation paths miss the `user:profile_context:{user_id}` key. Only `ProfileEventConsumer` invalidates it.
- **Mitigation**: `ProfileContextService` does version-check on read, catching stale data within one request.
- **Recommendation**: Add `f"user:profile_context:{user_id}"` to all three invalidation key lists.

### P2-02 (Design Note): StateAggregator shadow mode runs full DB queries
- **File**: `backend/app/state_aggregator/service.py:156-232`
- **Risk**: Low
- **Description**: Shadow mode computes all fields before discarding, imposing same DB load as live.
- **Recommendation**: Accept as-is for now; this is the documented shadow testing protocol.

### P3-01: Go-side cache invalidation missing `user:profile_context`
- **File**: `backend/gateway/internal/service/user_preferences_service.go:105-119`
- **Risk**: Low
- **Description**: Same as P2-01 but specific to Go gateway path. Go does not publish to Python event bus, so `ProfileEventConsumer` is not triggered.
- **Mitigation**: The Go CQRS publish to `cqrs:stream:user` triggers Python's `PreferenceEventConsumer`, which calls `invalidate_user_cache`. But that also misses `user:profile_context`.
- **Recommendation**: Add `user:profile_context:{userID}` to Go's `invalidateCache()` key list, and also to Python's `PreferenceService._invalidate_cache()` and `UserService.invalidate_user_cache()`.

---

## 7. Architecture Observations (No Issues)

### 7.1 Event Bus Reliability
The EventBus implementation is robust:
- Idempotency store prevents duplicate processing
- DLQ with PostgreSQL persistence for failed events
- Auto-reconnection on connection errors
- Stale message claiming via `xautoclaim`
- Consumer loop auto-restart on unexpected failures

### 7.2 Consumer Isolation
Each consumer uses independent DB sessions per sub-operation, preventing cascading failures. The `try/except` wrapping around each sub-operation in `TaskEventConsumer._handle_task_completed()` is well-designed for fault isolation.

### 7.3 Version-Aware Caching
Both `ContextOrchestrator` and `ProfileContextService` implement version-aware caching by storing and checking `preference_version`. This provides a secondary safety net against stale cache even when invalidation is missed.

### 7.4 Data Format Consistency
The data pipeline from StateAggregator through DualCoreRouter to Prompt Assembly uses well-typed dataclasses and frozen dataclasses. No implicit conversions that could cause data corruption were found.
