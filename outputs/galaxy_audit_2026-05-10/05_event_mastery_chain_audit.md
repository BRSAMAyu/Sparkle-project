# Event Mastery Chain Audit Report

**Date**: 2026-05-10
**Scope**: Mastery-related event publishing, consumption, deduplication, ordering, and error handling
**Auditor**: Claude Code (automated trace)

---

## Executive Summary

The audit traced the complete mastery event chain across 9 core files, identifying **7 issues** ranging from P1 (data corruption) to P3 (operational debt). The most critical finding is a **triple mastery deduction** risk that was partially mitigated by a guard comment but remains fragile. The deferred event pattern in `ErrorBookMasterySyncService` is correctly implemented.

---

## 1. Event Source Map

### 1.1 `GalaxyStatsService.spark_node()` (stats_service.py)
**File**: `backend/app/services/galaxy/stats_service.py`, lines 33-254

**Events published**:
- `node_mastery_updated` via `event_bus.publish()` (line 117-127) -- with payload `{event_type: "node_mastery_updated", user_id, node_id, old_mastery, new_mastery, reason: "task_complete"}`
- Outbox event `galaxy.node.mastery_updated` written to `event_outbox` table (line 407-436)
- Achievement events: `NODE_UNLOCKED` (line 169-175), `NODE_MASTERED` (line 178-184), and a second `NODE_MASTERED` at 100% (line 187-193)

### 1.2 `GalaxyFeedbackService` (feedback_service.py)
**File**: `backend/app/services/galaxy/feedback_service.py`, lines 33-399

**Events published**:
- `node_mastery_updated` via `event_bus.publish()` (line 302) -- with `{event_type: "node_mastery_updated", user_id, node_id, old_mastery, new_mastery, reason}`

### 1.3 `ErrorBookMasterySyncService` (error_book_mastery_sync_service.py)
**File**: `backend/app/services/error_book_mastery_sync_service.py`, lines 83-624

**Events published**: DEFERRED via `_pending_event` pattern.
- `_update_node_mastery()` (line 242-341) returns `{..., _pending_event: {topic: "node_mastery_updated", payload: NodeMasteryUpdatedEvent(...).to_dict()}}`
- The caller (`ErrorBookService`) flushes pending events AFTER `db.commit()` via `_flush_pending_mastery_events()` (error_book_service.py lines 134-145)
- Mastery DB write is delegated to `GalaxyService.update_node_mastery()` (line 343-362)

### 1.4 `GalaxyService.update_node_mastery()` (galaxy_service.py)
**File**: `backend/app/services/galaxy_service.py`, lines 3009-3339

**Events published**:
- Outbox event `galaxy.node.mastery_updated` written to `event_outbox` table (line 3305-3315)
- Achievement event `NODE_MASTERED` via `_process_mastery_achievement_after_commit()` (line 3322-3362)
- Does NOT publish `node_mastery_updated` to the event bus directly (only outbox + achievement)

### 1.5 `GalaxyEventConsumer` (galaxy_event_consumer.py)
**File**: `backend/app/services/galaxy_event_consumer.py`, lines 30-512

**Re-publishes**: NO. It consumes events but does not re-publish mastery events. It only calls `GraphEvolutionService`, `SeedExtractor`, `ErrorReplanBridge`, `ErrorMasteryBridge`, and `PlanHealthInterventionBridge`.

### 1.6 `CommunitySignalBridge.handle_resource_shared()` (community_signal_bridge.py)
**File**: `backend/app/services/community_signal_bridge.py`, lines 176-259

**Events published**:
- `community.resource_shared` (line 188-199)
- `galaxy.node.updated` (line 226-240) -- after calling `GalaxyService.update_node_mastery()` directly

---

## 2. Event Consumer Map

| Consumer | Stream | Group | Subscribes to mastery events? |
|----------|--------|-------|-------------------------------|
| `GalaxyEventConsumer` | sparkle_events | galaxy_event_consumer | `error_created`, `galaxy.node.updated`, `task.completed`, `node_mastery_updated`, `SimulationGapRevealed` |
| `AchievementEventConsumer` | sparkle_events | achievement_event_consumer | `task.completed`, `galaxy.node.updated`, `community.group_task_completed`, `focus.session.completed`, etc. |
| `CommunitySignalBridge` | (synchronous, not a consumer) | -- | -- |
| `ErrorReplanBridge` | (called synchronously from GalaxyEventConsumer) | -- | -- |
| `ProfileEventConsumer` | sparkle_events | profile_event_consumer | `node_mastery_updated`, `error_created` |

---

## 3. Critical Question Analysis

### 3.1 Triple Mastery Deduction (ErrorCreated)

**Question**: When `ErrorCreated` fires, does it get consumed by BOTH `GalaxyEventConsumer._handle_error_created` AND `ErrorBookMasterySyncService.apply_error_diagnosis`?

**Answer**: There is NO triple deduction, but the guard is fragile.

**Detailed trace**:

1. `ErrorBookService.analyze_and_link()` calls `ErrorBookMasterySyncService.apply_error_diagnosis()` SYNCHRONOUSALLY (error_book_service.py line 356) BEFORE publishing the `error_created` event.
2. `apply_error_diagnosis()` writes mastery via `GalaxyService.update_node_mastery()` (line 343-362).
3. AFTER `db.commit()`, `ErrorBookService` publishes deferred `_pending_event` (line 362).
4. THEN `ErrorBookService` publishes `error_created` event to the event bus (line 368-373).
5. `GalaxyEventConsumer._handle_error_created()` receives the event but does NOT modify `mastery_score` (confirmed by the explicit guard comment at line 80-86).

**Guard mechanism**: The `_handle_error_created()` method has a docstring comment (line 80-86):
```
MASTERY GUARD: 节点掌握度更新已迁移到 ErrorBookMasterySyncService (断点2)，
该服务在 error_book_service.py 的 analyze_and_link 回调中同步调用，
使用基于 error_type 的精确权重（如 knowledge_gap=-10）。
本异步处理器 **绝不** 修改 mastery_score。
```

Additionally, `GalaxyService` has the deprecated methods `handle_error_created()` and `update_mastery_from_error()` **removed** (galaxy_service.py line 161-170), with a comment explaining they were removed to prevent double-deduction.

**FINDING (P2)**: The guard relies entirely on a developer comment and code convention. There is no programmatic enforcement. A future developer could accidentally add a mastery mutation in `_handle_error_created()` without realizing the conflict.

> **Severity**: P2 (fragile but currently correct)
> **File**: `backend/app/services/galaxy_event_consumer.py`, lines 77-86
> **Suggestion**: Add a unit test that asserts `_handle_error_created` does not call any method that modifies `UserNodeStatus.mastery_score`. Consider adding a defensive `assert` at the top of the method checking that mastery has already been applied.

---

### 3.2 Pending Events Leak

**Question**: Does `ErrorBookMasterySyncService.apply_error_diagnosis` actually publish the `_pending_event` to the event bus?

**Answer**: YES, correctly implemented.

**Detailed trace**:

1. `_update_node_mastery()` (line 242-341) creates `_pending_event` dict but does NOT publish it. It returns it as part of the result dict (line 322-341).
2. `apply_error_diagnosis()` (line 95-160) collects results from `_update_node_mastery()`.
3. Back in `ErrorBookService` (line 356-362):
   ```python
   mastery_results = await mastery_sync.apply_error_diagnosis(user_id, error)
   await self.db.commit()  # Commit FIRST
   await self._flush_pending_mastery_events(mastery_results)  # THEN publish
   ```
4. `_flush_pending_mastery_events()` (error_book_service.py lines 134-145) iterates results, extracts `_pending_event.topic` and `_pending_event.payload`, and calls `event_bus.publish(topic, payload)`.

**Edge case**: If `_flush_pending_mastery_events()` fails after `db.commit()`, the mastery change is durable but the event is lost. This means consumers (like `GalaxyEventConsumer._handle_mastery_updated`) would not see the update, but the DB state is correct.

**FINDING (P3)**: Event loss after commit is possible but only affects downstream reactions (graph evolution, achievement processing). The mastery outbox event written inside `GalaxyService.update_node_mastery()` provides a separate reconciliation path.

> **Severity**: P3 (best-effort is acceptable for non-critical side effects)
> **File**: `backend/app/services/error_book_service.py`, lines 134-145
> **Suggestion**: Consider wrapping `_flush_pending_mastery_events` in a retry loop. The outbox table already provides a reconciliation mechanism.

---

### 3.3 Achievement Double-Fire

**Question**: When mastery reaches 100, does `spark_node` fire NODE_MASTERED or HIDDEN_TRIGGER for the Perfectionist achievement?

**Answer**: Both fires are correct but there is a double-trigger via TWO code paths.

**Path 1 -- `GalaxyStatsService.spark_node()`** (stats_service.py):
- Line 178-184: `NODE_MASTERED` when mastery >= 80 (fires at 80, 90, 100 -- every call)
- Line 187-193: A SECOND `NODE_MASTERED` when mastery >= 100 (redundant with above)

**Path 2 -- `GalaxyService.update_node_mastery()`** (galaxy_service.py):
- Line 3322-3362: `_process_mastery_achievement_after_commit()` fires `NODE_MASTERED` when new_mastery >= 80

**Path 3 -- `AchievementEventConsumer._handle_node_updated()`** (achievement_event_consumer.py):
- Line 294-299: `NODE_MASTERED` when `old_mastery < 80 <= new_mastery`
- Line 300-306: `HIDDEN_TRIGGER` with code `"PERFECTIONIST"` when `old_mastery < 100 <= new_mastery`

**FINDING (P1)**: When `spark_node()` is called and mastery goes from, say, 78 to 100:
1. `spark_node` fires `NODE_MASTERED` at line 178 (mastery >= 80) -- **first NODE_MASTERED**
2. `spark_node` fires `NODE_MASTERED` at line 187 (mastery >= 100) -- **second NODE_MASTERED** (redundant)
3. `spark_node` publishes `node_mastery_updated` event to event bus
4. `GalaxyEventConsumer._handle_mastery_updated()` receives this and runs graph evolution (no achievement)
5. BUT the `galaxy.node.updated` event is NOT published by `spark_node` -- so `AchievementEventConsumer._handle_node_updated()` is NOT triggered from this path.

When `update_node_mastery()` is called directly (e.g., from ErrorBookMasterySyncService or CommunitySignalBridge):
1. `update_node_mastery()` fires `NODE_MASTERED` at line 3355-3360 when new_mastery >= 80 -- **third potential NODE_MASTERED**
2. `CommunitySignalBridge` additionally publishes `galaxy.node.updated` which triggers `AchievementEventConsumer._handle_node_updated()` for another `NODE_MASTERED` + `HIDDEN_TRIGGER`

The **Perfectionist** achievement specifically relies on `HIDDEN_TRIGGER` which is only fired from `AchievementEventConsumer._handle_node_updated()`. This path is only triggered when `galaxy.node.updated` is published, which ONLY happens from `CommunitySignalBridge.handle_resource_shared()`. Therefore:

**The Perfectionist achievement (100% mastery) will NEVER trigger from normal task completion or error book paths.** It only works for knowledge sharing events.

> **Severity**: P1 (broken user-facing feature)
> **File**: `backend/app/services/galaxy/stats_service.py`, lines 178-193
> **Description**: `spark_node()` fires `NODE_MASTERED` twice (lines 178 and 187) but never fires `HIDDEN_TRIGGER` for the Perfectionist achievement. The `HIDDEN_TRIGGER("PERFECTIONIST")` code in `AchievementEventConsumer._handle_node_updated()` can only be reached via `galaxy.node.updated` events, which `spark_node()` does not publish.
> **Code snippet** (stats_service.py line 178-193):
> ```python
> # Node mastered event (when mastery reaches 80%+)
> if status.mastery_score >= 80:
>     await achievement_engine.process_event(
>         user_id=str(user_id),
>         event_type=AchievementEvent.NODE_MASTERED,
>         ...
>     )
>
> # Perfectionist achievement (100% mastery)
> if status.mastery_score >= 100:
>     await achievement_engine.process_event(
>         user_id=str(user_id),
>         event_type=AchievementEvent.NODE_MASTERED,  # <-- Should be HIDDEN_TRIGGER
>         ...
>     )
> ```
> **Suggested fix**: Change line 188 from `AchievementEvent.NODE_MASTERED` to `AchievementEvent.HIDDEN_TRIGGER` with `hidden_trigger_code="PERFECTIONIST"`, OR publish a `galaxy.node.updated` event from `spark_node()`.

---

### 3.4 Event Ordering

**Question**: Can events arrive out of order? Can `node_mastery_updated` arrive before the node itself is created in the consumer's view?

**Answer**: YES, ordering is not guaranteed.

**Analysis**:
- Events are published to a single Redis Stream (`sparkle_events`). Redis Streams maintain insertion order within a single stream.
- However, the order of PUBLISHING is not deterministic across code paths.
- In the `ErrorBookService.analyze_and_link()` flow:
  1. `apply_error_diagnosis()` is called synchronously, creating/updating `UserNodeStatus`
  2. `db.commit()` persists the state
  3. `_flush_pending_mastery_events()` publishes `node_mastery_updated`
  4. `error_created` event is published AFTER

  This means `node_mastery_updated` is published BEFORE `error_created`. The `GalaxyEventConsumer` will process the mastery update before the error event, which is the correct order for this specific flow.

- However, for `GalaxyEventConsumer._handle_error_created()` (line 104-107), if a node has no `UserNodeStatus`, it creates one with `mastery_score=0.0`. If a `node_mastery_updated` event arrives first (from a different consumer group read), the consumer might create a status with stale data.

**FINDING (P3)**: No ordering guarantee across consumer groups. Each consumer group reads independently. A `node_mastery_updated` event could theoretically be processed by `ProfileEventConsumer` before `GalaxyEventConsumer` has processed the preceding `error_created` event. This is generally safe because `GalaxyEventConsumer._handle_mastery_updated()` calls `GraphEvolutionService.handle_mastery_updated()` which only does graph structure updates, not state-dependent logic.

> **Severity**: P3 (low practical impact)
> **File**: `backend/app/services/galaxy_event_consumer.py`, line 414-421
> **Suggestion**: If ordering becomes critical, use Redis Stream entry IDs for causal ordering or add a `caused_by_event_id` field.

---

### 3.5 Idempotency

**Question**: Do all consumers handle duplicate events gracefully?

**Answer**: The EventBus provides message-level idempotency, but not business-logic-level idempotency.

**Infrastructure-level idempotency** (event_bus.py lines 1161-1182):
- Uses an idempotency store (`get_idempotency_store("redis")`)
- Checks `evt:{stream}:{message_id}` before processing
- Acquires a lock, processes, then marks as done with 24h TTL
- Skips duplicate messages (line 1166-1169)

**Business-logic-level idempotency**:

| Consumer | Method | Idempotent? |
|----------|--------|-------------|
| GalaxyEventConsumer._handle_error_created | Creates UserNodeStatus if missing | Partially -- uses `db.get()` first, but `append_graph_event_source()` may append duplicate provenance entries |
| GalaxyEventConsumer._handle_node_updated | Reads and writes PlanState facts | NO -- `facts["knowledge_readiness"]` is overwritten each time, but multiple identical events produce identical writes (naturally idempotent) |
| GalaxyEventConsumer._handle_mastery_updated | Calls GraphEvolutionService | Depends on GraphEvolutionService implementation |
| AchievementEventConsumer._handle_node_updated | Calls AchievementEngine | Depends on AchievementEngine deduplication |
| AchievementEventConsumer._handle_achievement_unlocked | Creates cognitive fragment, notification | NOT idempotent -- duplicate events create duplicate fragments and notifications (mitigated by infrastructure-level dedup) |

**FINDING (P2)**: `GalaxyEventConsumer._handle_error_created()` at line 112-136 does NOT check if provenance has already been appended. If the infrastructure-level idempotency fails (e.g., Redis restart loses the idempotency key), `append_graph_event_source()` could be called twice, creating duplicate provenance entries.

> **Severity**: P2 (data quality issue, not data corruption)
> **File**: `backend/app/services/galaxy_event_consumer.py`, lines 112-136
> **Suggestion**: Add a check in `_handle_error_created()` to verify if provenance already exists for this error_id before appending.

---

### 3.6 DLQ Coverage

**Question**: What happens when an event consumer throws an exception? Does it go to DLQ? Is DLQ ever reconciled?

**Answer**: DLQ coverage exists but reconciliation is manual-only.

**DLQ Flow** (event_bus.py lines 886-932):
1. `_process_stream_message()` catches exceptions from the callback
2. Calls `_handle_failed_message()` (line 1187)
3. If `retry_count < max_retries`: requeue via `_requeue_for_retry()` (increments retry count)
4. If `retry_count >= max_retries`: move to DLQ via `_move_to_dlq()`
5. DLQ entries are stored in Redis stream `{stream}:dlq` and persisted to `event_dlq` PostgreSQL table via `_persist_dlq_entry()` (line 740)

**Reconciliation**: There is NO automatic DLQ reconciliation mechanism. DLQ stats are available via `get_dlq_stats()` (line 1275) but no consumer re-processes DLQ entries.

**FINDING (P2)**: DLQ events are never automatically retried. If an event fails `max_retries` times (default 3), it goes to the DLQ and stays there permanently. For mastery-related events, this means a user could complete a task, the mastery update event fails 3 times, and the downstream effects (achievements, graph evolution, plan readiness) never execute.

> **Severity**: P2 (operational risk)
> **File**: `backend/app/core/event_bus.py`, lines 886-932
> **Suggestion**: Implement a DLQ reconciliation cron job that re-processes events after a delay, or add monitoring/alerting on DLQ size.

---

## 4. Additional Findings

### 4.1 Redundant `NODE_MASTERED` in spark_node (P2)

**File**: `backend/app/services/galaxy/stats_service.py`, lines 178-193

The `>= 80` check at line 178 and the `>= 100` check at line 187 both fire `NODE_MASTERED`. When mastery is 100, the achievement engine receives `NODE_MASTERED` twice for the same node in the same `spark_node` call. If `AchievementEngine.process_event()` is not idempotent, this could double-count the mastery event.

```python
# Line 178-184: First NODE_MASTERED (fires when mastery >= 80)
if status.mastery_score >= 80:
    await achievement_engine.process_event(
        user_id=str(user_id),
        event_type=AchievementEvent.NODE_MASTERED,
        ...
    )

# Line 187-193: Second NODE_MASTERED (fires when mastery >= 100, which is also >= 80)
if status.mastery_score >= 100:
    await achievement_engine.process_event(
        user_id=str(user_id),
        event_type=AchievementEvent.NODE_MASTERED,  # DUPLICATE
        ...
    )
```

> **Severity**: P2
> **Suggested fix**: Change the second check to `AchievementEvent.HIDDEN_TRIGGER` with `hidden_trigger_code="PERFECTIONIST"`, or merge into a single conditional.

### 4.2 GalaxyFeedbackService publishes node_mastery_updated without revision (P3)

**File**: `backend/app/services/galaxy/feedback_service.py`, lines 206-283

`_update_mastery_from_feedback()` directly reads and writes `UserNodeStatus.mastery_score` WITHOUT going through `GalaxyService.update_node_mastery()`. This bypasses:
- Optimistic locking (revision check)
- Outbox event writing
- Mastery audit log
- Cache invalidation

It publishes `node_mastery_updated` via `event_bus.publish()` but the event payload lacks a revision field, making it impossible to detect race conditions.

```python
# Line 256: Direct mastery manipulation without revision
new_mastery = max(self.MIN_MASTERY, min(self.MAX_MASTERY, int(old_mastery + score * 10)))
```

> **Severity**: P3 (legacy code, low-traffic path)
> **Suggested fix**: Route through `GalaxyService.update_node_mastery()` for consistency, or add revision-based conflict detection.

### 4.3 CommunitySignalBridge bypasses deferred event pattern (P3)

**File**: `backend/app/services/community_signal_bridge.py`, lines 218-240

`handle_resource_shared()` calls `GalaxyService.update_node_mastery()` directly (which commits internally at line 3319), then publishes `galaxy.node.updated` event. If the event publish fails, the mastery update is already committed. This is the opposite of the deferred pattern used by `ErrorBookMasterySyncService`.

```python
# Line 218-224: Mastery committed inside update_node_mastery
await galaxy_service.update_node_mastery(
    user_id=user_id,
    node_id=resource_id,
    new_mastery=int(round(new_mastery)),
    reason="community_knowledge_share_bonus",
)

# Line 226-240: Event published after commit (fire-and-forget)
await event_bus.publish("galaxy.node.updated", {...})
```

> **Severity**: P3 (acceptable for bonus events, mastery delta is small)
> **Suggested fix**: Consider using the deferred event pattern for consistency.

---

## 5. Issue Summary Table

| # | Severity | File | Line(s) | Description |
|---|----------|------|---------|-------------|
| 1 | **P1** | `stats_service.py` | 178-193 | Perfectionist achievement never triggers from task completion -- `HIDDEN_TRIGGER` code path is unreachable from `spark_node()`. The `>= 100` block fires a duplicate `NODE_MASTERED` instead. |
| 2 | **P2** | `galaxy_event_consumer.py` | 77-86 | Triple deduction guard is comment-only, no programmatic enforcement preventing future mastery mutations in `_handle_error_created()`. |
| 3 | **P2** | `galaxy_event_consumer.py` | 112-136 | Provenance append is not idempotent -- duplicate events can create duplicate provenance entries. |
| 4 | **P2** | `stats_service.py` | 178-193 | Redundant `NODE_MASTERED` fires twice when mastery reaches 100 (both `>= 80` and `>= 100` blocks trigger). |
| 5 | **P2** | `event_bus.py` | 886-932 | DLQ has no automatic reconciliation. Failed mastery events stay in DLQ permanently. |
| 6 | **P3** | `feedback_service.py` | 206-283 | Direct mastery manipulation bypasses revision-based optimistic locking, audit log, and outbox pattern. |
| 7 | **P3** | `community_signal_bridge.py` | 218-240 | Event published after commit without deferred pattern -- event loss possible. |

---

## 6. Mastery Event Flow Diagram

```
                    TASK COMPLETION
                         |
                         v
            GalaxyStatsService.spark_node()
                    |          |
                    |          +---> event_bus: node_mastery_updated
                    |          |         |
                    |          |         +---> GalaxyEventConsumer._handle_mastery_updated()
                    |          |         |         +---> GraphEvolutionService
                    |          |         |         +---> SeedExtractor
                    |          |         |
                    |          |         +---> ProfileEventConsumer._handle_knowledge_updated()
                    |          |
                    |          +---> AchievementEngine: NODE_UNLOCKED (if first unlock)
                    |          +---> AchievementEngine: NODE_MASTERED (if >= 80)
                    |          +---> AchievementEngine: NODE_MASTERED (if >= 100, DUPLICATE)
                    |          |
                    |          +---> Outbox: galaxy.node.mastery_updated
                    |          +---> Cache invalidation
                    |          +---> WebSocket streaming
                    |
                    v
            NO galaxy.node.updated published
            => AchievementEventConsumer._handle_node_updated() NOT triggered
            => HIDDEN_TRIGGER("PERFECTIONIST") NEVER fires from this path


                    ERROR CREATED
                         |
                         v
            ErrorBookService.analyze_and_link()
                    |
                    +---> ErrorBookMasterySyncService.apply_error_diagnosis() [SYNC]
                    |         |
                    |         +---> GalaxyService.update_node_mastery()
                    |                   |
                    |                   +---> DB: user_node_status (revision-based)
                    |                   +---> Outbox: galaxy.node.mastery_updated
                    |                   +---> AchievementEngine: NODE_MASTERED (if >= 80)
                    |
                    +---> db.commit()
                    +---> _flush_pending_mastery_events()
                    |         +---> event_bus: node_mastery_updated
                    |
                    +---> event_bus: error_created
                              |
                              +---> GalaxyEventConsumer._handle_error_created()
                              |         +---> GraphEvolutionService (NO mastery mutation)
                              |         +---> ErrorReplanBridge (reads mastery, NO mutation)
                              |         +---> ErrorMasteryBridge (NO mastery mutation)
                              |         +---> PlanHealthInterventionBridge
                              |         +---> Spine on_mistake_event
                              |
                              +---> ProfileEventConsumer._handle_error_created()


                    COMMUNITY SHARE
                         |
                         v
            CommunitySignalBridge.handle_resource_shared()
                    |
                    +---> GalaxyService.update_node_mastery() [direct call]
                    |         +---> DB commit + outbox + achievement
                    |
                    +---> event_bus: galaxy.node.updated
                              |
                              +---> GalaxyEventConsumer._handle_node_updated()
                              |         +---> PlanStateService (readiness calc)
                              |
                              +---> AchievementEventConsumer._handle_node_updated()
                                        +---> NODE_UNLOCKED (if 0 -> >0)
                                        +---> NODE_MASTERED (if <80 -> >=80)
                                        +---> HIDDEN_TRIGGER("PERFECTIONIST") (if <100 -> >=100)
                                        ^^^ ONLY PATH TO PERFECTIONIST ACHIEVEMENT
```

---

## 7. Recommendations (Priority Order)

1. **[P1 Fix]** In `stats_service.py` line 187-193, change `AchievementEvent.NODE_MASTERED` to `AchievementEvent.HIDDEN_TRIGGER` with `hidden_trigger_code="PERFECTIONIST"` to make the Perfectionist achievement reachable from task completion.

2. **[P2 Fix]** Add a defensive assertion or runtime check in `GalaxyEventConsumer._handle_error_created()` that verifies mastery has already been applied (e.g., by checking if a StudyRecord with the error_id already exists). This prevents future regressions.

3. **[P2 Fix]** Implement DLQ monitoring and a manual reconciliation tool (e.g., a CLI command to re-process DLQ entries).

4. **[P3 Fix]** Route `GalaxyFeedbackService._update_mastery_from_feedback()` through `GalaxyService.update_node_mastery()` to unify the mastery write path.

5. **[P3 Fix]** Add provenance deduplication in `_handle_error_created()` to prevent duplicate entries when events are redelivered.
