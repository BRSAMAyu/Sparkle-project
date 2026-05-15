# Round 2 Audit: Error Handling Pattern Audit

**Date**: 2026-05-15
**Scope**: `backend/app/` (Python Engine)
**Auditor**: Automated systematic scan + manual classification
**Total `except Exception` instances**: 2,146

---

## Executive Summary

The Python backend contains **2,146 `except Exception` catch-all blocks** across the codebase. After systematic classification:

| Category | Count | Percentage |
|----------|-------|------------|
| Logged + swallowed (warning/error/debug) | ~1,575 | 73% |
| Returns default value | ~569 | 27% |
| Re-raised (catch-log-reraise) | ~218 | 10% |
| Bare `except Exception:` (no variable binding) | 574 | 27% |
| `except Exception:` + `pass` (completely silent) | ~62 | 3% |

**Critical Finding**: While most exceptions are at least logged, the sheer volume of catch-all blocks creates a "forest of warnings" problem -- real failures are indistinguishable from expected fallback paths in log noise.

**Top Risk Files** (by exception density):

| File | Count | Risk Level |
|------|-------|------------|
| `signals/spine_orchestrator.py` | 103 | CRITICAL |
| `core/celery_tasks.py` | 95 | CRITICAL |
| `orchestration/orchestrator.py` | 36 | HIGH |
| `core/celery_app.py` | 31 | HIGH |
| `services/task_service.py` | 26 | HIGH |
| `orchestration/context_builder.py` | 26 | HIGH |
| `services/achievement_engine.py` | 18 | HIGH |
| `services/profile_event_consumer.py` | 15 | HIGH |
| `orchestration/adaptive_replanner.py` | 15 | MEDIUM |
| `services/agent_grpc_service.py` | 18 | HIGH |

---

## 1. Critical Path Analysis

### 1.1 ProfileWriteService (`services/profile_write_service.py`)

**11 `except Exception` blocks.** Classification:

| Line | Context | Verdict | Reasoning |
|------|---------|---------|-----------|
| L103 | `upsert_preference` failure in `set_explicit_preferences` | **UNREASONABLE** | Calls `db.rollback()` then continues. History write silently dropped; preference is updated but no audit trail. No alert fired. |
| L143 | `find_preference` / `delete_preference` failure in `remove_explicit_preference` | **UNREASONABLE** | History record left orphaned. Deletion appears successful to caller but data is inconsistent. |
| L220 | `upsert_preference` failure in `update_inferred_preference` | **UNREASONABLE** | Same pattern as L103. Inferred preferences updated in UserPreferencesCenter but no history record. |
| L385 | `redis.hgetall` failure in `list_inferred_backups` | REASONABLE | Cache read fallback; returns empty dict. |
| L392 | `json.loads` failure | REASONABLE | Data parse fallback. |
| L470 | `event_bus.publish` failure for `ProfilePreferenceUpdated` | **UNREASONABLE** | Event silently dropped. Downstream consumers (personalization cache invalidation, Spine) miss the update. |
| L487 | `event_bus.publish` failure for `ProfilePreferenceDeleted` | **UNREASONABLE** | Same as above. |
| L529 | `redis.hset` failure in `_backup_inferred_value` | REASONABLE | Non-critical backup; override still works without backup. |
| L537 | `redis.hget` failure in `_load_inferred_backup` | REASONABLE | Graceful degradation. |
| L544 | `json.loads` failure | REASONABLE | Parse fallback. |
| L556 | `redis.hdel` failure in `_delete_inferred_backup` | REASONABLE | Cleanup; non-critical. |

**Impact**: Preference writes can succeed at the `UserPreferencesCenter` level but silently fail to create history/audit records. This breaks the append-only audit trail invariant. Additionally, dropped events mean downstream caches (personalization, Spine) may serve stale preference data for up to their TTL (30-300 seconds).

---

### 1.2 AchievementEngine (`services/achievement_engine.py`)

**18 `except Exception` blocks.** Key patterns:

| Line | Context | Verdict |
|------|---------|---------|
| L202 | Redis cache for recent achievement events | REASONABLE -- debug-level log, cache-only |
| L324 | Auto-seed achievement definitions on first query | REASONABLE -- seed failure logged at warning, cache still populated |
| L1209 | `db.get(Task, ...)` for task snapshot | **UNREASONABLE** -- silently returns `None`, achievement may be awarded with incomplete context |
| L1237 | `db.get(Plan, ...)` for plan lookup | **UNREASONABLE** -- `pass`, completely silent. Achievement logic continues without plan context. |
| L1260 | `db.get(KnowledgeNode, ...)` for node snapshot | **UNREASONABLE** -- silently returns partial dict. |
| L1508 | `_record_achievement_narrative_signal` | **MEDIUM** -- narrative record dropped, not critical but data loss |
| L1540 | `_record_chronicle_unlock` | **MEDIUM** -- chronicle entry dropped |
| L1567 | `_publish_achievement_progress` | **UNREASONABLE** -- event bus publish failed; no downstream processing of progress |
| L1609 | `_broadcast_unlock_signals` | **UNREASONABLE** -- unlock broadcast dropped; WebSocket notification lost |
| L1656 | Celery retry queue for photon reward | REASONABLE -- falls back to local retry |
| L1714 | Local photon reward retry | **MEDIUM** -- reward permanently lost after all retries |
| L1911 | WebSocket notification send | **MEDIUM** -- user never sees notification |
| L2096 | Quality streak calculation | REASONABLE -- optional calculation |
| L2641 | Combo bonus photon grant | **UNREASONABLE** -- photons silently not granted |
| L2669 | Milestone notification WebSocket send | **MEDIUM** -- notification lost |
| L2707 | Daily first rewards grant | **UNREASONABLE** -- rewards silently not granted |
| L2925 | Contract reward grant | **UNREASONABLE** -- contract rewards silently not granted |
| L2947 | Contract photon deduction | **UNREASONABLE** -- contract deduction silently not applied |

**Impact**: Achievement unlocks can silently lose photon rewards, notifications, progress events, and context data. The user sees the unlock badge but never receives the associated rewards. This directly affects user trust and the gamification loop.

---

### 1.3 EventBus (`core/event_bus.py`)

**12 `except Exception` blocks.** The EventBus itself has robust DLQ handling:

| Line | Context | Verdict |
|------|---------|---------|
| L737 | DLQ health check failure | REASONABLE -- monitoring-only |
| L827 | DLQ depth gauge update failure | REASONABLE -- metrics-only |
| L921 | DLQ move failure | REASONABLE -- best-effort ack to prevent pending pileup |
| L926 | Ack failure after DLQ failure | REASONABLE -- logged at error level |
| L1005 | Redis connect failure | REASONABLE -- sets cooldown, logged |
| L1047 | Publish retry attempt | REASONABLE -- retries with backoff |
| L1078 | DLQ persist failure for publish | REASONABLE -- last resort |
| L1188 | Message processing exception | REASONABLE -- delegates to `_handle_failed_message` (retry + DLQ) |
| L1192 | Top-level processing error | REASONABLE -- routes to DLQ/retry |
| L1273 | Consumer loop error | REASONABLE -- reconnect + backoff |
| L1280 | Reconnection failure | REASONABLE -- logged |
| L1428 | Stream scan failure | REASONABLE -- admin tool |

**Verdict**: EventBus core is well-structured. All consumer exceptions properly route through retry -> DLQ pipeline. The DLQ has both Redis stream and PostgreSQL persistence.

---

### 1.4 AdaptiveReplanner (`orchestration/adaptive_replanner.py`)

**15 `except Exception` blocks.**

| Line | Context | Verdict |
|------|---------|---------|
| L53 | `to_dict()` conversion fallback | REASONABLE |
| L653 | Calendar capacity context | REASONABLE -- returns empty dict, non-critical enrichment |
| L889 | Persist compressed `daily_spec` | **UNREASONABLE** -- plan data lost, re-planning will use stale spec |
| L1118 | Too-hard feedback row attach | REASONABLE -- debug-level, non-critical |
| L1189 | Too-hard task breakdown LLM | REASONABLE -- returns empty list, graceful degradation |
| L1526 | Record breakdown feedback | REASONABLE -- debug-level |
| L1753 | PlanHealthSignal emit | **MEDIUM** -- non-fatal but health monitoring loses signal |
| L1764 | Card protocol bridge init | REASONABLE -- pre-migration graceful degradation |
| L1821 | ParameterCompiler skip | REASONABLE -- logged at debug, non-critical |
| L1934 | PlanAdjustmentApplier failure | **UNREASONABLE** -- adjustments silently not applied, plan continues with stale parameters |
| L1951 | Card protocol writeback failure | **MEDIUM** -- writeback lost but non-blocking |
| L2047 | Card protocol writeback (full replan) | **MEDIUM** -- same pattern |
| L2210 | Persist struggle streak | **UNREASONABLE** -- struggle tracking lost, affects adaptive decisions |
| L2226 | Datetime parse | REASONABLE -- data validation |
| L2656 | Rollback last patch | **UNREASONABLE** -- rollback failure means plan is in potentially broken state |

**Impact**: Plan adjustments and rollbacks can silently fail, leaving plans in inconsistent states. Struggle streaks and compressed specs can be lost, causing the adaptive system to make decisions based on stale data.

---

### 1.5 StateAggregator (`state_aggregator/service.py`)

**2 `except Exception` blocks** (very clean):

| Line | Context | Verdict |
|------|---------|---------|
| L835 | JSON parse of recent achievement events from Redis cache | REASONABLE -- cache fallback |
| L837 | Redis cache read for achievement events | REASONABLE -- returns empty, graceful degradation |

**Verdict**: StateAggregator is well-designed. No critical exception swallowing. It is read-only by design, so failures naturally degrade to empty/null values which is the correct behavior for a state aggregation service.

**Cascade Risk**: StateAggregator does NOT swallow exceptions. However, it reads from services that DO swallow exceptions. If MemoryService, AchievementEngine, or PreferenceService silently corrupt their data, StateAggregator will faithfully aggregate and return corrupt data to DualCoreRouter.

---

### 1.6 PhotonService (`services/photon_service.py`)

**1 `except Exception` block**:

| Line | Context | Verdict |
|------|---------|---------|
| L519 | Transfer failure | REASONABLE -- logs error then **re-raises** |

**Verdict**: PhotonService transfer correctly re-raises. Single instance, properly handled.

---

### 1.7 MemoryInferredWriteLane (`services/memory_inferred_write_lane.py`)

**3 `except Exception` blocks**:

| Line | Context | Verdict |
|------|---------|---------|
| L158 | Background task wrapper | **MEDIUM** -- entire inferred write lane silently fails; user's inferred memories are lost for this turn |
| L378 | Dry-run record to Redis | REASONABLE -- dry-run only |
| L497 | Scene consolidation post-write | **MEDIUM** -- memory is written but scene consolidation skipped; scenes may miss the new memory |

---

## 2. Consumer DLQ Coverage Analysis

### 2.1 EventBus DLQ Infrastructure

The EventBus provides automatic DLQ with:
- **Retry**: Exponential backoff, configurable max retries (default 3)
- **DLQ**: Redis stream + PostgreSQL dual persistence
- **Auto-restart**: Consumer loops auto-restart on crash
- **Idempotency**: Dedup via Redis lock + idempotency store
- **Stale claim**: XAUTOCLAIM for messages stuck in pending

### 2.2 Consumer Coverage Matrix

| Consumer | DLQ Covered? | Internal Error Handling | Risk |
|----------|-------------|------------------------|------|
| `AchievementEventConsumer` | YES (via EventBus) | `handle_event` dispatches to sub-handlers; each sub-handler opens its own DB session. Top-level exceptions propagate to EventBus DLQ. Sub-handler exceptions are caught per-operation. | **MEDIUM** -- sub-handler exceptions swallowed, but at least logged |
| `TaskEventConsumer` | YES (via EventBus) | Each sub-operation (BehaviorSignalCollector, MetacognitionService, CommunitySignalBridge, AdaptiveReplanner) is individually try-caught with its own DB session. | **HIGH** -- critical operations like replanning and metacognition refresh can silently fail |
| `ProfileEventConsumer` | YES (via EventBus) | `handle_event` dispatches without top-level try. Each sub-handler has its own session and try-catch. | **MEDIUM** -- 15 named exception catches; some are pure pass-through |
| `GalaxyEventConsumer` | YES (via EventBus) | Sub-handlers individually try-caught. | **MEDIUM** |
| `GalaxyExecutionConsumer` | YES (via EventBus) | `handle_event` wraps entire body in try-except Exception. | **HIGH** -- entire execution result processing silently swallowed |
| `CapsuleEventConsumer` | YES (via EventBus) | Minimal error handling. | LOW |
| `CognitiveEventConsumer` | YES (via EventBus) | Logs mention DLQ. | LOW |
| `DocumentFeedbackEventConsumer` | YES (via EventBus) | Simple try-catch. | LOW |
| `ExecutionEventConsumer` | YES (via EventBus) | Simple try-catch. | LOW |
| `GroupFileEventConsumer` | YES (via EventBus) | Simple try-catch. | LOW |
| `InterventionEventConsumer` | YES (via EventBus) | Multiple try-catch per sub-handler. | MEDIUM |
| `MainChainArtifactConsumer` | YES (via EventBus) | Simple try-catch. | LOW |
| `NudgeEventConsumer` | YES (via EventBus) | Simple try-catch. | LOW |
| `PlanHealthEventConsumer` | YES (via EventBus) | Multiple try-catch. | MEDIUM |
| `PreferenceEventConsumer` | YES (via EventBus) | Has custom DLQ handling beyond EventBus. | LOW |
| `SocialSignalEventConsumer` | YES (via EventBus) | Simple try-catch. | LOW |
| `AchievementPlanConsumer` | YES (via EventBus) | Retry logic for plan not found. | LOW |
| `GalaxyPlanConsumer` | YES (via EventBus) | Retry logic for plan not found. | LOW |
| `PlanTaskGenerationConsumer` | YES (via EventBus) | Retry logic for plan not found. | LOW |
| `UserMemorySeedConsumer` | YES (via EventBus) | Basic error handling. | LOW |
| `UserProfileBootstrapConsumer` | YES (via EventBus) | Basic error handling. | LOW |
| `WelcomeOnboardingConsumer` | YES (via EventBus) | Basic error handling. | LOW |

**Summary**: All consumers are covered by EventBus DLQ at the infrastructure level. However, most consumers catch exceptions internally (within their sub-handlers) and never let exceptions propagate to the EventBus DLQ. This means the DLQ only catches truly catastrophic failures (like Redis disconnection), not business logic failures.

---

## 3. Cascade Failure Risk Matrix

### 3.1 StateAggregator -> DualCoreRouter Cascade

```
StateAggregator reads from:
  - MemoryService (episodic, commitments, reflections)
  - AchievementEngine (streak, achievements)
  - UserPreferencesCenter (traits, preferences)
  - PredictiveService (foresight)
  - SocialSignalBridge (social signals)
  - MetacognitionService (metacognition profile)
  - SRLPhaseStateRecord (SRL phase)
  - IdiographicAssociationService (associations)
```

**Risk**: StateAggregator itself has NO exception swallowing. It propagates errors. However, the services it reads FROM may have silently corrupted data:

| Source | Failure Mode | Corrupted Data | Impact on DualCoreRouter |
|--------|-------------|----------------|-------------------------|
| MemoryService | Inferred write lane failed silently | Missing episodic memories | Router makes decisions without knowing about recent events |
| AchievementEngine | Progress event publish failed | Stale achievement progress in cache | Router may recommend tasks user already completed |
| PreferenceService | Profile preference event dropped | Stale preferences in cache (up to 300s TTL) | Router uses outdated learning style, schedule, depth preferences |
| MetacognitionService | Refresh snapshot failed silently | Missing metacognition data | Router cannot assess self-regulation state |
| SocialSignalBridge | Social signal update failed | Missing social context | Router misses social learning opportunities |

### 3.2 ProfileWriteService -> Downstream Cascade

```
ProfileWriteService._publish_preference_updated_event FAILED
  -> ProfileEventConsumer never receives update
    -> Personalization cache NOT invalidated
      -> StateAggregator reads stale preferences (TTL 30-300s)
        -> DualCoreRouter routes with wrong preferences
          -> AI generates responses with wrong tone/style/depth
```

**Severity**: MEDIUM. Self-corrects after TTL expiry (30-300s). But during that window, the user receives AI responses based on stale preferences.

### 3.3 AchievementEngine -> Photon Reward Cascade

```
AchievementEngine._schedule_photon_reward_retry FAILED (Celery)
  -> Local retry also FAILED
    -> Photon reward permanently lost
      -> User never receives earned photons
        -> Economy imbalance, user trust erosion
```

**Severity**: HIGH. No self-correction. Photon rewards are permanently lost.

### 3.4 TaskEventConsumer -> AdaptiveReplanner Cascade

```
TaskEventConsumer._handle_task_completed
  -> AdaptiveReplanner.on_task_completed FAILED silently
    -> Plan not adjusted for task completion
      -> Remaining tasks have wrong difficulty/estimates
        -> Next AdaptiveReplanner run sees stale plan
          -> May trigger unnecessary full replan
```

**Severity**: MEDIUM. Self-corrects on next AdaptiveReplanner run, but causes plan instability in the interim.

### 3.5 Orchestrator -> Memory Write Cascade

```
Orchestrator._write_turn_end_episodic_memory FAILED (L1194)
  -> Turn memory not recorded
    -> Working memory missing this turn
      -> Next turn's context is incomplete
        -> AI response quality degrades
```

**Severity**: MEDIUM. Partially self-correcting (next turn can still access older memories), but creates context gaps.

---

## 4. Complete Exception Inventory by Directory

### 4.1 By Directory

| Directory | Count | % of Total | Risk Density |
|-----------|-------|------------|--------------|
| `services/` | 686 | 32% | HIGH |
| `orchestration/` | 340 | 16% | HIGH |
| `core/` | 293 | 14% | MEDIUM |
| `signals/` | 155 | 7% | CRITICAL |
| `api/v1/` | 224 | 10% | LOW |
| `aurora/runtime_v1/` | 89 | 4% | MEDIUM |
| `tools/` | 37 | 2% | LOW |
| `tasks/` | 19 | 1% | LOW |
| `agents/` | 36 | 2% | LOW |

### 4.2 Top 20 Files by Exception Count

| File | Count | Unreasonable | Critical Data Affected |
|------|-------|-------------|----------------------|
| `signals/spine_orchestrator.py` | 103 | ~30 | Signal-to-action pipeline, spine outcomes |
| `core/celery_tasks.py` | 95 | ~25 | Background jobs, scheduled tasks |
| `orchestration/orchestrator.py` | 36 | ~8 | Chat responses, memory writes, Aurora sidecar |
| `core/celery_app.py` | 31 | ~10 | Celery infrastructure, task registration |
| `services/task_service.py` | 26 | ~5 | Task CRUD, status transitions |
| `orchestration/context_builder.py` | 26 | ~6 | Context assembly for LLM |
| `orchestration/graph_rag.py` | 23 | ~3 | RAG retrieval |
| `core/security_monitor.py` | 23 | ~2 | Security monitoring |
| `services/achievement_engine.py` | 18 | ~8 | Achievement unlocks, photon rewards |
| `services/task_event_consumer.py` | 22 | ~5 | Task completion, replanning triggers |
| `services/agent_grpc_service.py` | 18 | ~4 | gRPC streaming, response delivery |
| `services/profile_event_consumer.py` | 15 | ~3 | Preference cache invalidation |
| `services/profile_context_service.py` | 17 | ~3 | Profile context for AI |
| `services/theater/prediction_theater_service.py` | 17 | ~2 | Prediction theater |
| `orchestration/state_manager.py` | 17 | ~3 | Workflow state management |
| `aurora/runtime_v1/service.py` | 17 | ~4 | Aurora runtime |
| `services/scheduler_service.py` | 19 | ~3 | Scheduling |
| `services/profile_write_service.py` | 11 | ~5 | Preference writes, event publishing |
| `services/error_book_service.py` | 16 | ~2 | Error book operations |
| `orchestration/routing_engine.py` | 16 | ~2 | Routing decisions |

---

## 5. Most Dangerous Silent Swallows (Top 30)

These are `except Exception: pass` or `except Exception:` with no logging, in critical data paths:

| File | Line | What is Swallowed |
|------|------|------------------|
| `signals/spine_orchestrator.py` | 2735 | Lock acquisition failure in spine processing |
| `aurora/runtime_v1/self_model.py` | 523 | Self-model update failure |
| `aurora/runtime_v1/l4_async.py` | 208 | Async L4 processing failure |
| `signals/marketplace.py` | 1303 | Strategy marketplace operation |
| `orchestration/graph_rag.py` | 2317 | Graph RAG node processing |
| `orchestration/graph_rag.py` | 2328 | Graph RAG edge processing |
| `orchestration/prompts.py` | 3618 | Prompt template rendering |
| `orchestration/routing_engine.py` | 1831 | Routing engine fallback |
| `orchestration/lang_graph_planner.py` | 830 | LangGraph planner step |
| `orchestration/memory_helpers.py` | 258 | Memory helper function |
| `core/context_pack.py` | 72 | Context pack assembly |
| `core/context_pack.py` | 96 | Context pack assembly |
| `state_aggregator/service.py` | 838 | Achievement events cache read |
| `services/preference_event_consumer.py` | 141 | Preference event processing |
| `api/v1/graph_monitor.py` | 367 | Graph monitor endpoint |
| `api/v1/audit.py` | 151 | Audit endpoint |
| `api/v1/admin_dashboard.py` | 289 | Admin dashboard metric |
| `api/v1/admin_dashboard.py` | 330 | Admin dashboard metric |
| `api/v1/aurora_status.py` | 134 | Aurora status check |
| `signals/aurora_core_session.py` | 481 | Aurora core session operation |
| `tools/task_query_tool.py` | 413 | Task query enrichment |
| `tools/task_query_tool.py` | 437 | Task query enrichment |
| `tools/task_query_tool.py` | 462 | Task query enrichment |
| `tools/task_query_tool.py` | 559 | Task query enrichment |
| `tools/task_query_tool.py` | 584 | Task query enrichment |
| `core/pending_actions.py` | 89 | Pending action processing |
| `core/pending_actions.py` | 138 | Pending action processing |
| `core/pending_actions.py` | 171 | Pending action processing |
| `core/pending_actions.py` | 208 | Pending action processing |
| `core/pending_actions.py` | 284 | Pending action processing |

---

## 6. Remediation Recommendations (Priority Order)

### P0 - Critical (Fix Immediately)

**R2-01**: `AchievementEngine` photon reward silent loss (L1714, L2641, L2707, L2925, L2947)
- **Action**: Replace `except Exception as e: logger.error(...)` with guaranteed retry via persistent outbox pattern.
- **Impact**: Photon economy integrity.
- **Effort**: Medium.

**R2-02**: `ProfileWriteService` event publish silent drop (L470, L487)
- **Action**: Implement at-least-once delivery guarantee. Use transactional outbox pattern or sync publish with retry.
- **Impact**: Preference consistency across services.
- **Effort**: Medium.

**R2-03**: `AdaptiveReplanner._apply_plan_adjustment` silent failure (L1934)
- **Action**: Raise on critical adjustment failures. Log as ERROR (not WARNING). Emit health signal.
- **Impact**: Plan consistency.
- **Effort**: Small.

**R2-04**: `GalaxyExecutionConsumer.handle_event` top-level catch-all
- **Action**: Remove top-level `except Exception` and let errors propagate to EventBus DLQ.
- **Impact**: Execution results processing reliability.
- **Effort**: Small.

### P1 - High (Fix This Sprint)

**R2-05**: `signals/spine_orchestrator.py` -- 103 exception blocks with ~30 unreasonable
- **Action**: Audit each of the 30 unreasonable blocks. Replace bare `except Exception:` with specific exception types. Add structured logging with error codes.
- **Impact**: Spine pipeline observability.
- **Effort**: Large (103 blocks).

**R2-06**: `core/celery_tasks.py` -- 95 exception blocks
- **Action**: Classify into retryable vs terminal. Use Celery's native retry mechanism instead of manual try-catch.
- **Impact**: Background job reliability.
- **Effort**: Large (95 blocks).

**R2-07**: `orchestration/orchestrator.py` -- memory write failure (L1194)
- **Action**: Memory writes should not be silently swallowed. At minimum, emit a metric and increment a counter. Ideally, queue for async retry.
- **Impact**: Context continuity.
- **Effort**: Small.

**R2-08**: All bare `except Exception:` with `pass` (62 instances)
- **Action**: Replace with at minimum `logger.debug("...", exc_info=True)`. Better: catch specific exception types.
- **Impact**: Debuggability.
- **Effort**: Small per instance, 62 instances.

### P2 - Medium (Fix Next Sprint)

**R2-09**: Consumer sub-handler exception isolation
- **Action**: TaskEventConsumer and AchievementEventConsumer catch exceptions per sub-operation. While this prevents cascade, it hides failures from EventBus DLQ. Add explicit error metric for each sub-operation and consider moving to event sourcing.
- **Impact**: Observability.
- **Effort**: Medium.

**R2-10**: `TaskQueryTool` -- 5 bare silent catches in enrichment steps
- **Action**: These silently degrade query results. Add fallback logging.
- **Impact**: AI response quality.
- **Effort**: Small.

**R2-11**: `core/pending_actions.py` -- 5 bare silent catches
- **Action**: Pending actions are user-visible. Silent swallow means actions silently fail.
- **Impact**: User experience.
- **Effort**: Small.

### P3 - Low (Backlog)

**R2-12**: Adopt structured exception hierarchy
- **Action**: Introduce domain-specific exceptions (e.g., `PreferenceWriteError`, `AchievementRewardError`, `MemoryWriteError`) and replace generic `except Exception` with targeted catches.
- **Impact**: Code quality, maintainability.
- **Effort**: Large (cross-cutting).

**R2-13**: Add exception metrics dashboard
- **Action**: Create Prometheus counters for each exception category. Alert on thresholds.
- **Impact**: Observability.
- **Effort**: Medium.

**R2-14**: Reduce exception density in `spine_orchestrator.py`
- **Action**: Refactor spine orchestrator to use Result/Either monad pattern or decorator-based error handling to reduce the 103 exception blocks.
- **Impact**: Code maintainability.
- **Effort**: Large.

---

## 7. Pattern Summary

### 7.1 Good Patterns (Keep)

1. **EventBus retry + DLQ pipeline**: Well-designed. All consumers benefit from infrastructure-level DLQ.
2. **PhotonService catch-log-reraise**: Correct pattern for financial operations.
3. **StateAggregator zero catch-all**: Clean read-only design with no exception swallowing.
4. **AchievementEngine after-commit tasks**: Uses SQLAlchemy session lifecycle hooks correctly.
5. **Kill switch failures gracefully degrade**: `except Exception` in kill switch reads returns safe defaults.

### 7.2 Anti-Patterns (Fix)

1. **Silent event publish failures**: `ProfileWriteService` and `AchievementEngine` drop events with only a warning log. Should use outbox pattern.
2. **Financial operations with no compensation**: Photon rewards/penalties silently lost. Should have persistent retry queue with reconciliation job.
3. **DB read failures returning None/partial**: `AchievementEngine` returns empty context on DB read failure, continues processing with incomplete data.
4. **Bare `except Exception: pass`**: 62 instances where exceptions are completely invisible.
5. **Consumer sub-handler isolation**: Prevents cascade but also prevents DLQ from capturing business logic failures.

---

## 8. Statistical Summary

| Metric | Value |
|--------|-------|
| Total `except Exception` blocks | 2,146 |
| Files affected | ~200+ |
| Bare catches (no variable binding) | 574 (27%) |
| Completely silent (`pass`) | 62 (3%) |
| Re-raised | 218 (10%) |
| Returns default value | 569 (27%) |
| Logged then swallowed | 1,575 (73%) |
| Critical path unreasonable | ~47 |
| DLQ-covered consumers | 22/22 (100%) |
| Consumers with internal catch-all | 16/22 (73%) |
| P0 issues found | 4 |
| P1 issues found | 4 |
| P2 issues found | 3 |
| P3 issues found | 3 |

---

*End of Round 2 Error Handling Pattern Audit*
