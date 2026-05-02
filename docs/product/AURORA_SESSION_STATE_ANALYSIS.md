# Aurora Session State Lifecycle Analysis

**Date**: 2026-05-02
**Scope**: Complete mapping of session state storage, lifecycle, FSM, recovery, and architectural gaps
**Status**: Research report -- no files modified

---

## Executive Summary

Sparkle's Aurora session state is spread across **7 distinct Redis key families** and **3 PostgreSQL tables**, governed by **5 different TTL policies** ranging from 5 minutes to 30 days. There is no unified session state object. The core chat FSM state (`SessionStateManager`) lives entirely in Redis with a 1-hour TTL, while the Aurora cognitive runtime has its own parallel Redis+PostgreSQL persistence layer. The L3 CoreSession FSM has yet another independent Redis store with a 30-minute TTL. **Redis restart causes total loss of all active session state with no recovery path.**

---

## 1. State Storage: The Seven-Layer Model

### Layer 1: FSM State (SessionStateManager)

**File**: `backend/app/orchestration/state_manager.py` (lines 64-680)

| Attribute | Value |
|-----------|-------|
| Redis key | `session:{session_id}:state` |
| Data structure | JSON-serialized `FSMState` dataclass |
| TTL | **3600 seconds (1 hour)** -- configurable via constructor `ttl` param, default at line 70 |
| Write trigger | Every `_update_state()` call in orchestrator |
| Size estimate | ~500 bytes (tiny: session_id, state enum, details, request_id, timestamp) |

**FSMState fields** (lines 33-48):
```
session_id: str
state: str              # INIT | THINKING | GENERATING | TOOL_CALLING | DONE | FAILED
details: str            # Human-readable state detail
request_id: str | None
user_id: str | None
timestamp: float
last_processed_message: str | None   # For resume
accumulated_response: str            # Partial response buffer
tool_calls_in_progress: list         # Active tool calls
```

**FSM states** (lines 24-29, also `backend/app/orchestration/orchestrator.py` lines 211-216):
- `INIT` -- Request received, validation starting
- `THINKING` -- (reserved, not actively used in process_stream)
- `GENERATING` -- LLM generation active
- `TOOL_CALLING` -- (reserved, tool execution)
- `DONE` -- Turn completed
- `FAILED` -- Error state

### Layer 2: WorkflowState Checkpoint (RedisCheckpointer)

**File**: `backend/app/checkpoint/redis_checkpointer.py` (lines 11-82)

| Attribute | Value |
|-----------|-------|
| Redis key | `checkpoint:{session_id}` |
| Data structure | JSON-serialized `WorkflowState` from statechart engine |
| TTL | **86400 seconds (24 hours)** -- line 15 |
| Write trigger | Every node execution in StateGraph (line 213 of `statechart_engine.py`) |
| Size estimate | 10-200 KB depending on context_data contents |

**WorkflowState fields** (defined in `backend/app/orchestration/statechart_engine.py` lines 23-62):
```
messages: list[dict]         # Full conversation messages
context_data: dict           # Blackboard with all contextual data
next_step: str | None        # Router hint for next node
errors: list[str]            # Accumulated errors
is_finished: bool
trace_id: str
```

Context data is bounded by:
- `MAX_CONTEXT_DATA_KEYS = 200` (settings.py line 808)
- `MAX_CONTEXT_DATA_VALUE_BYTES = 10 KB` per value (settings.py line 809)

### Layer 3: Session Feedback (SessionStateMixin)

**File**: `backend/app/orchestration/session_state_mixin.py` (lines 43-46, 500-553)

| Attribute | Value |
|-----------|-------|
| Redis key | `session:feedback:{session_id}` |
| Data structure | JSON-serialized `SessionAdaptationContext` |
| TTL | **21600 seconds (6 hours)** -- `session_feedback.py` line 10 |
| Write trigger | Every user message (detect_session_feedback in mixin lines 599-667) |
| Size estimate | 2-5 KB |

Contains conversation rhythm analysis, feedback signal detection (mismatch/simplify/expand), and accumulated adaptation context.

### Layer 4: Context Versions (SessionStateMixin)

**File**: `backend/app/orchestration/session_state_mixin.py` (lines 44-46, 911-934)

| Attribute | Value |
|-----------|-------|
| Redis key | `user:context:versions:{user_id}` |
| Data structure | JSON dict of domain -> version hash |
| TTL | **21600 seconds (6 hours)** -- line 45 |
| Domains | `tasks`, `plans`, `focus`, `progress`, `prefs` |
| Size estimate | ~500 bytes |

Used for conflict detection: if context versions changed between turns, the system self-heals by refreshing stale data.

### Layer 5: Aurora Runtime State (AuroraRuntimeStore)

**File**: `backend/app/aurora/runtime_v1/state.py` (lines 408-550)

| Attribute | Value |
|-----------|-------|
| Redis key | `aurora:runtime:{user_id}:{surface}:{conversation_id}` |
| Data structure | JSON-serialized `AuroraState` Pydantic model |
| TTL | **86400 seconds (24 hours)** -- line 409 |
| Surfaces | `aurora_modeling`, `aurora_planning`, `aurora_checkpoint` |
| Size estimate | 5-20 KB |

**AuroraState fields** (lines 303-330):
```
user_id: str
surface: str                              # aurora_modeling | aurora_planning | aurora_checkpoint
conversation_id: str
runtime_session_id: str
user_model_snapshot: dict                  # Current user model state
informational_tensions: list               # Open tensions/pain points
current_intent: AuroraIntent | None        # What Aurora is pursuing
latent_threads: list                       # Background threads to pick up later
activity_profile: ActivityProfile          # Expression settings, intensity
self_scheduled_wakes: list                 # Proactive follow-ups
streaming_status: str                      # idle | emitting | waiting_user
ingress_events: list                       # Event log
last_decision_at: datetime | None
updated_at: datetime
```

**Surface index** stored separately:
- Key: `aurora:surface-index:{user_id}` -- maps surface name to latest conversation_id
- Same TTL (24 hours)

### Layer 6: Aurora Energy State (AuroraEnergyStore)

**File**: `backend/app/aurora/runtime_v1/state.py` (lines 646-791)

| Attribute | Value |
|-----------|-------|
| Redis key | `aurora:energy:{user_id}` |
| Data structure | JSON-serialized `AuroraEnergyState` |
| TTL | **172800 seconds (48 hours)** -- line 693 |
| Size estimate | ~500 bytes |

```
user_id: str
current_level: AuroraEnergyLevel     # L0 | L1 | L2 | L3
wake_score: float                     # 0.0-1.0
last_l3_session_at: datetime | None
l3_session_count_today: int
cooldown_until: datetime | None
updated_at: datetime
```

### Layer 7: Aurora Core Session (L3 FSM)

**File**: `backend/app/aurora/core_session.py` (lines 40-367)

| Attribute | Value |
|-----------|-------|
| Redis keys | `aurora:core_session:{session_id}` (primary), plus `aurora:core_session:active:{user_id}`, `aurora:core_session:current:{user_id}`, `aurora:core_session:last:{user_id}`, `aurora:core_session:resume:{token}` |
| Data structure | JSON-serialized `AuroraCoreSession` dataclass |
| TTL | **1800 seconds (30 min)** -- line 42 |
| Idle timeout | **600 seconds (10 min)** -- line 43 |
| Size estimate | 5-50 KB (contains full message history) |

**8 FSM stages** (lines 27-36):
```
declare -> observe -> judge -> ask -> await_user -> process_response -> update -> exit
```

Session constraints:
- Max 6 user turns (`MAX_USER_TURNS`, line 44)
- Max 12 Aurora messages (`MAX_AURORA_MESSAGES`, line 45)
- Resume token: opaque `acs_{uuid}` string (line 53) stored as a Redis pointer to session_id

### Layer 8: Distributed Lock (per session)

**File**: `backend/app/orchestration/state_manager.py` (lines 85-88, 200-384)

| Attribute | Value |
|-----------|-------|
| Redis key | `session:{session_id}:lock` |
| TTL | **30 seconds** -- line 78, auto-renewed every 10 seconds |
| Purpose | Prevent concurrent requests to same session |
| Implementation | Redis SET NX + Lua script for atomic release |

### Layer 9: Idempotency Cache

**File**: `backend/app/orchestration/state_manager.py` (lines 89-91, 386-429)

| Attribute | Value |
|-----------|-------|
| Redis key | `session:{session_id}:response:{request_id}` |
| TTL | **300 seconds (5 minutes)** -- line 386 |
| Purpose | Return cached response for retried requests |

### Layer 10: Self Model

**File**: `backend/app/aurora/runtime_v1/self_model.py` (lines 10-11)

| Attribute | Value |
|-----------|-------|
| Redis key | `aurora:self_model:{user_id}` |
| TTL | **2592000 seconds (30 days)** -- line 11 |
| Size estimate | 10-30 KB (comprehensive user model) |

### Layer 11: Write Pipeline Temporary State

**File**: `backend/app/aurora/runtime_v1/write_pipeline.py` (lines 23-34)

| Attribute | Value |
|-----------|-------|
| Redis key | `aurora:write-pipeline:temporary:{user_id}:{claim_id}` |
| TTL | **86400 seconds (24 hours)** -- line 23 |
| Claim keys | `aurora:claims:{user_id}:{domain}` -- 24h TTL |

---

## 2. PostgreSQL Persistence Layer

Three Aurora-specific tables exist in PostgreSQL, created via Alembic migrations:

### Table: `aurora_state_snapshots`

**Migration**: `backend/alembic/versions/s40b1c2d3e4_add_aurora_runtime_v1.py`
**Model**: `backend/app/aurora/runtime_v1/models.py` (lines 14-41)
**Service**: `backend/app/aurora/runtime_v1/persistence.py` (lines 60-92)

| Column | Type | Purpose |
|--------|------|---------|
| id | GUID (PK) | Primary key |
| user_id | GUID (FK -> users.id) | User reference |
| surface | String(64) | aurora_modeling / aurora_planning / aurora_checkpoint |
| conversation_id | String(128) | Conversation scope |
| runtime_session_id | String(128) | Session scope |
| snapshot_version | Integer | Auto-incrementing per user |
| snapshot_at | DateTime | When snapshot was taken |
| user_model_snapshot | JSONB | Current user model state |
| informational_tensions | JSONB | List of active tensions |
| current_intent | JSONB | Current Aurora intent |
| latent_threads | JSONB | Background threads |
| activity_profile | JSONB | Expression/intensity settings |
| last_decision_at | DateTime | Last decision timestamp |
| metadata | JSONB | Runtime metadata |

**Write trigger**: `AuroraPersistenceStore.save_cognitive_snapshot()` -- called during checkpoint debrief completion and wake execution. NOT called on every message.

**Read trigger**: `AuroraPersistenceStore.load_cognitive_snapshot()` -- called to hydrate state when Redis is empty. Only loads the latest snapshot per user.

### Table: `aurora_scheduled_wakes`

**Migration**: Same migration as above
**Model**: `backend/app/aurora/runtime_v1/models.py` (lines 44-69)

Stores proactive follow-up wake records with status lifecycle: `pending` -> `executed` / `suppressed` / `cancelled`.

### Table: `aurora_decision_telemetry`

**Migration**: `backend/alembic/versions/stage_c5_aurora_decision_telemetry.py`
**Model**: `backend/app/aurora/runtime_v1/models.py` (lines 72-99)

Stores decision outcomes from the Aurora decision loop for analysis and outcome tracking.

---

## 3. State Lifecycle: Complete Timeline

### Session Creation

1. **gRPC StreamChat request arrives** (`orchestrator.py` line 2004)
2. `session_id` extracted from request, or generated if missing (line 2032-2034)
3. FSM state set to `INIT` via `_update_state()` (line 2093)
4. Distributed lock acquired (line 2070)
5. Lock renewal background task started (line 2088)

### During Active Conversation

6. FSM transitions: `INIT` -> `GENERATING` -> (optional `TOOL_CALLING`) -> `DONE`
7. StateGraph checkpoints saved at each node via `RedisCheckpointer` (`statechart_engine.py` line 213)
8. Session feedback analysis runs on every user message (mixin line 599)
9. Context versions tracked and self-healed (mixin line 936)
10. Aurora runtime state updated for `aurora_*` mode turns (service.py)

### Session End (per turn)

11. FSM state set to `DONE` (orchestrator.py line 3409) or `FAILED` (line 3430)
12. Lock released (via finally block)
13. Lock renewal task stopped
14. Response cached for idempotency (300s TTL)

### State Destruction

| State Layer | TTL | Natural Expiry |
|-------------|-----|---------------|
| FSM state | 1 hour | Expires 1 hour after last update |
| Checkpoint | 24 hours | Expires 24 hours after last node execution |
| Session feedback | 6 hours | Expires 6 hours after last message |
| Context versions | 6 hours | Expires 6 hours after last update |
| Aurora runtime | 24 hours | Expires 24 hours after last surface activity |
| Aurora energy | 48 hours | Expires 48 hours after last energy update |
| Core session (L3) | 30 minutes | Expires 30 min after creation, 10 min idle |
| Distributed lock | 30 seconds | Auto-renewed during processing |
| Idempotency cache | 5 minutes | Quick expiry for dedup |
| Self model | 30 days | Long-lived user model |
| Write pipeline | 24 hours | Claim validity period |

### User Closes App For...

**5 minutes**: All state intact. FSM state, checkpoint, feedback, Aurora runtime all still alive. Next message resumes seamlessly.

**30 minutes**: FSM state (1h TTL) still alive. Checkpoint (24h) still alive. L3 Core Session expired (30 min TTL). If user had an active L3 calibration session, it is lost. The resume token key is deleted.

**1 hour**: FSM state expired. Checkpoint still alive. Aurora runtime still alive. The orchestrator will create fresh FSM state on next request. The checkpoint is loadable but is NOT loaded automatically -- the statechart engine starts fresh (confirmed at `statechart_engine.py` line 199: "For now, we always start fresh or from provided state").

**6 hours**: FSM state expired. Session feedback expired. Context versions expired. Checkpoint still alive. Aurora runtime still alive. Full context rebuild from PostgreSQL + fresh Redis hydration.

**24 hours**: Most Redis state expired. Only self-model (30d) and possibly Aurora energy (48h) remain. Next message triggers full context reconstruction from PostgreSQL.

**3 days**: Only self-model (30d TTL) persists. Complete cold start.

---

## 4. State Recovery Analysis

### Can State Be Recovered After Redis Restart?

**No.** There is no Redis persistence (RDB/AOF) configured in the default docker-compose. All session state is ephemeral.

### What Has PostgreSQL Backup?

| Data | PostgreSQL Backed? | Recovery Possible? |
|------|--------------------|--------------------|
| FSM state (INIT/GENERATING/DONE) | No | **Lost forever** -- state resets to fresh |
| WorkflowState checkpoint | No | **Lost forever** -- starts from scratch |
| Session feedback adaptation | No | **Lost forever** -- adaptation context resets |
| Context versions | No | **Lost forever** -- re-fetched from DB |
| Aurora runtime state | Partially | **Partially recoverable** from `aurora_state_snapshots` table, but only the latest snapshot (not per-turn) |
| Aurora scheduled wakes | Yes | **Recoverable** -- stored in `aurora_scheduled_wakes` table |
| Aurora energy state | No | **Lost** -- resets to default L0 |
| Core session (L3) | No | **Lost forever** -- calibration session terminated |
| Self model | No (Redis only) | **Lost** -- 30d of accumulated model data gone |
| Chat messages | Yes | **Safe** -- stored in `chat_messages` table |
| User profile/preferences | Yes | **Safe** -- stored in PostgreSQL |

### User Experience When State Is Lost

**Redis restart during active session:**

1. User's in-flight message gets no response (gRPC stream broken)
2. Next message: new session_id generated by Flutter client (or reused from client)
3. Orchestrator finds no FSM state -> creates fresh INIT state
4. StateGraph starts from `context_builder` node -- no checkpoint loaded
5. Conversation history loaded from PostgreSQL (chat_messages table)
6. Aurora runtime state: Redis miss -> attempts `AuroraPersistenceStore.load_cognitive_snapshot()` from PostgreSQL
7. If snapshot exists: partial recovery of tensions, intent, activity profile
8. If no snapshot: cold start with default activity profile
9. Session feedback adaptation context is gone -- tone/density resets
10. Context versions reset -- full re-fetch of all context domains

**Result**: User sees a "fresh" conversation where Aurora still has access to chat history but has lost:
- Short-term adaptation context (simplify/expand/mismatch signals)
- Context focusing decisions
- In-progress tool calls
- L3 calibration session (if active)
- Active plan context in session

---

## 5. Core Session FSM (L3 Deep Calibration)

**File**: `backend/app/aurora/core_session.py`

### 8 FSM Stages

```
declare      -> Aurora declares its intent and scope for this calibration
observe      -> Aurora reviews user model and identifies tensions
judge        -> Aurora evaluates what needs calibration
ask          -> Aurora presents questions/options to user
await_user   -> Waiting for user response (includes resume token)
process_response -> Process user's answer or selection
update       -> Apply model writes based on calibration
exit         -> Session complete, produce CalibrationResult
```

### Resume Token Mechanism

**File**: `backend/app/aurora/core_session.py` (lines 52-53, 250-251, 288-299, 349-358)

- Token format: `acs_{uuid_hex}` (line 53)
- Stored at: `aurora:core_session:resume:{token}` -> points to session_id
- On resume: lookup session_id from token, load full session from `aurora:core_session:{session_id}`
- **Critical limitation**: Token lives in Redis with 30-minute TTL. After Redis restart or TTL expiry, the resume token is permanently lost. No PostgreSQL fallback exists for resume tokens.

### Core Session Constraints

- Maximum 6 user turns (line 44)
- Maximum 12 Aurora messages (line 45)
- 30-minute hard limit (line 42)
- 10-minute idle timeout (line 43)
- Energy quota: 1-3 sessions per day depending on sprint mode (`AuroraEnergyStore.COOLDOWN_TEMPLATES`)

---

## 6. Standard Chat FSM (StateGraph)

**File**: `backend/app/agents/standard_workflow.py` (lines 3057-3200)

### Node Graph (11 nodes)

```
context_builder -> retrieval -> router -> [conditional]
                                         |-> collaboration -> collaboration_post_process
                                         |-> generation -> generation_review
                                         |-> tool_execution -> execution_review
                                                              |-> reflection
                                                              |-> generation (loop)
                                                              |-> __end__
                                         |-> generation
                                         |-> tool_execution
```

### Statechart Engine

**File**: `backend/app/orchestration/statechart_engine.py`

The `StateGraph` class (line 123) implements a hierarchical state machine with:
- Nodes (callable functions or sub-graphs)
- Static and conditional edges
- Parallel execution support
- Checkpointing interface (line 144: `checkpointer` attribute)
- Max step limit of 50 (line 189)

**Checkpoint note** (line 199):
```python
# Load from checkpoint if available (TRACKED(TD-008): implement resume logic)
# For now, we always start fresh or from provided state
```
This is a known tech debt item (TD-008): checkpoint resume is NOT implemented despite the `RedisCheckpointer` saving checkpoints.

---

## 7. Competing Patterns and Tradeoffs

### Redis-Only (Current State)

**Advantages:**
- Low latency (sub-millisecond reads)
- Simple implementation
- Natural TTL-based cleanup
- No schema migration burden

**Disadvantages:**
- Total loss on Redis restart
- No durability guarantee
- No multi-device consistency
- State size bounded by Redis memory
- No audit trail for session state changes

### Redis + PostgreSQL (Hybrid)

**Advantages:**
- Survives Redis restart
- Audit trail in PostgreSQL
- Can query historical state
- Multi-device can read consistent state from DB
- Redis remains the hot path for performance

**Disadvantages:**
- Dual-write consistency challenges
- Schema migration overhead
- Write latency increases
- Need garbage collection for expired PostgreSQL state

### Pure PostgreSQL

**Advantages:**
- Full durability
- ACID guarantees
- No state loss
- Easy multi-device access

**Disadvantages:**
- Higher latency (1-5ms per read vs 0.1ms Redis)
- Connection pool pressure
- Need manual TTL/garbage collection
- More complex query patterns for session state

### Industry Patterns

| System | Approach | TTL | Recovery |
|--------|----------|-----|----------|
| ChatGPT | PostgreSQL + Redis cache | Session-based | Full recovery from DB |
| Claude API | Stateless (client sends history) | Per-request | N/A |
| LangGraph Cloud | Checkpoint PostgreSQL | Configurable | Full checkpoint resume |
| Character.AI | Redis primary + DB snapshots | 30 min idle | Best-effort recovery |
| Sparkle (current) | Redis primary + selective PG snapshots | 1h-24h varied | Partial (snapshots only) |

---

## 8. Pain Points and Failure Scenarios

### P1: Redis Restart During Active Session

**Impact**: Total loss of in-flight conversation state. User gets no response. Next message starts fresh.

**Evidence**: `SessionStateManager` has no fallback load path. `RedisCheckpointer.load()` returns None on Redis miss. The orchestrator has no "state recovery" code path -- it always creates fresh state.

**Files affected**:
- `backend/app/orchestration/state_manager.py` line 126: returns None on Redis miss
- `backend/app/orchestration/orchestrator.py` line 2093: always overwrites with INIT
- `backend/app/checkpoint/redis_checkpointer.py` line 66: returns None on miss

### P2: TTL Expiry During Long Conversation

**Impact**: If a user is active but takes more than 1 hour between messages (FSM TTL), the FSM state resets. The checkpoint (24h) survives but is NOT loaded.

**Evidence**: The statechart engine comment at line 199 confirms checkpoints are saved but never loaded for resume. TD-008 tracks this.

**Files affected**:
- `backend/app/orchestration/state_manager.py` line 70: `ttl: int = 3600`
- `backend/app/orchestration/statechart_engine.py` line 199: resume not implemented

### P3: L3 Core Session Loss

**Impact**: If a user is mid-calibration (up to 6 turns invested) and the app goes to background for 10 minutes, the idle timer kills the session. No recovery possible. Resume token is deleted.

**Evidence**: `AuroraCoreSession.is_idle_expired` at line 145 checks 10-minute idle. `AuroraCoreSessionStore.save()` at line 295-299 cleans up resume keys on non-active status.

**Files affected**:
- `backend/app/aurora/core_session.py` lines 42-43: 30 min max, 10 min idle
- `backend/app/aurora/core_session.py` lines 295-299: resume key cleanup

### P4: Multiple Device Access

**Impact**: If a user opens the app on two devices simultaneously, they get different session_ids. Each device has independent FSM state, checkpoints, and session feedback. Aurora runtime state is keyed by `user_id:surface:conversation_id`, so different conversations get different runtime states.

**Evidence**: Session ID comes from the gRPC request (`orchestrator.py` line 2031). Each device generates its own session. The distributed lock prevents concurrent writes to the same session but does not coordinate across sessions.

**Files affected**:
- `backend/app/orchestration/orchestrator.py` line 2031: session_id from request
- `backend/app/orchestration/state_manager.py` line 81: lock key per session_id

### P5: State Migration During Schema Changes

**Impact**: The `AuroraState` Pydantic model has changed across stages. The `_coerce_legacy_state_payload()` method (state.py lines 560-643) attempts backward-compatible deserialization, but this only handles Redis payloads. PostgreSQL snapshot schema is fixed by migration. If the Pydantic model diverges from the PG schema, snapshot loading breaks.

**Evidence**: The `_coerce_legacy_state_payload()` method is 83 lines of defensive coercion code, indicating repeated format drift.

**Files affected**:
- `backend/app/aurora/runtime_v1/state.py` lines 560-643: legacy coercion
- `backend/app/aurora/runtime_v1/persistence.py` line 97: no coercion on PG load

### P6: Accumulated State Size

**Impact**: `WorkflowState.context_data` is bounded to 200 keys (settings.py line 808) with 10KB per value. However, there is no total size budget. A session with 200 keys of 10KB each = 2MB per checkpoint, serialized as JSON. For a busy system with 1000 concurrent sessions, this is 2GB of Redis memory just for checkpoints.

**Evidence**: `statechart_engine.py` line 93-96 implements key eviction but not total size budget.

### P7: Orphaned State Keys

**Impact**: When a session ends normally (DONE state), the FSM state key is overwritten but not explicitly deleted. It expires via TTL. However, checkpoint keys, feedback keys, context version keys, and response cache keys are never explicitly cleaned up on session end. They rely solely on TTL expiry.

**Evidence**: `SessionStateManager.cleanup_session()` exists (line 445) but is only used "for testing or manual cleanup". It is never called from the orchestrator's normal DONE path.

**Files affected**:
- `backend/app/orchestration/state_manager.py` line 445: cleanup_session exists but unused
- `backend/app/orchestration/orchestrator.py` line 3409: DONE path does not call cleanup

---

## 9. State Flow Diagram

```
User Message
    |
    v
[orchestrator.process_stream]  (orchestrator.py:2004)
    |
    +-- 1. Generate/reuse session_id (line 2031-2034)
    |
    +-- 2. _validate_request (line 2048)
    |       |
    |       +-- SessionStateManager._check_idempotency (mixin:882)
    |           +-- Redis: GET session:{sid}:response:{rid}
    |
    +-- 3. Acquire distributed lock (line 2070)
    |       +-- Redis: SET NX session:{sid}:lock EX 30
    |       +-- Start lock renewal task (every 10s)
    |
    +-- 4. FSM: INIT (line 2093)
    |       +-- Redis: SETEX session:{sid}:state 3600 {FSMState JSON}
    |
    +-- 5. Build context (_build_full_context)
    |       +-- Load chat history from PostgreSQL
    |       +-- Load user context (plans, tasks, preferences)
    |       +-- _detect_session_feedback -> Redis: GET/SETEX session:feedback:{sid}
    |       +-- _apply_context_focus_overlay -> Redis: GET user:context:versions:{uid}
    |       +-- _hydrate_companion_runtime_context -> CompanionStateService
    |       +-- _attach_situation_brief -> SituationBriefBuilder
    |
    +-- 6. Execute StateGraph (graph.invoke)
    |       +-- context_builder node
    |       +-- RedisCheckpointer.save -> SETEX checkpoint:{sid} 86400 {WorkflowState JSON}
    |       +-- retrieval node -> checkpoint saved
    |       +-- router node -> checkpoint saved
    |       +-- generation node -> LLM call
    |       +-- ... (conditional branches)
    |
    +-- 7. FSM: DONE (line 3409)
    |       +-- Redis: SETEX session:{sid}:state 3600 {DONE}
    |
    +-- 8. Release lock (finally block)
            +-- Lua: atomic check-and-delete session:{sid}:lock
            +-- Stop lock renewal task
```

---

## 10. Redis Key Inventory

| Key Pattern | TTL | Layer | Purpose |
|-------------|-----|-------|---------|
| `session:{sid}:state` | 1h | FSM | Current FSM state |
| `session:{sid}:lock` | 30s | Lock | Distributed session lock |
| `session:{sid}:response:{rid}` | 5m | Idempotency | Cached response |
| `session:{sid}:active_plan` | 1h | Plan tracking | Active plan for session |
| `checkpoint:{sid}` | 24h | StateGraph | WorkflowState checkpoint |
| `session:feedback:{sid}` | 6h | Feedback | Session adaptation context |
| `user:context:versions:{uid}` | 6h | Versioning | Domain version hashes |
| `snapshot:{snapshot_id}` | 1h | Snapshot | State snapshot for LangGraph |
| `aurora:runtime:{uid}:{surface}:{cid}` | 24h | Aurora | Runtime cognitive state |
| `aurora:surface-index:{uid}` | 24h | Aurora | Surface -> conversation mapping |
| `aurora:energy:{uid}` | 48h | Energy | Aurora energy level/cooldown |
| `aurora:core_session:{sid}` | 30m | L3 Core | Core calibration session |
| `aurora:core_session:active:{uid}` | 30m | L3 Core | Active session pointer |
| `aurora:core_session:current:{uid}` | 30m | L3 Core | Current session pointer |
| `aurora:core_session:last:{uid}` | 30m | L3 Core | Last session pointer |
| `aurora:core_session:resume:{token}` | 30m | L3 Core | Resume token -> session_id |
| `aurora:self_model:{uid}` | 30d | Self Model | Accumulated user model |
| `aurora:write-pipeline:temporary:{uid}:{claim_id}` | 24h | Write | Temporary write state |
| `aurora:claims:{uid}:{domain}` | 24h | Claims | Write pipeline claims |

**Total per active session**: ~8-10 Redis keys
**Total per user (cross-session)**: ~5 additional Redis keys (energy, self_model, context versions, surface index)

---

## 11. Architectural Decision Framework

### Option A: Add PostgreSQL Checkpoint Table for FSM State

**What**: Create `session_fsm_state` table. Write FSM state to both Redis (hot path) and PostgreSQL (durability). On Redis miss, load from PostgreSQL.

**Effort**: Medium (1 new table, dual-write in SessionStateManager, fallback load path)

**Resolves**: P1 (Redis restart), P2 (TTL expiry), P7 (orphaned keys)

**Does not resolve**: P3 (L3 session loss), P4 (multi-device), P5 (schema migration)

### Option B: Implement TD-008 (Checkpoint Resume)

**What**: Actually load and resume from `RedisCheckpointer` when a session resumes after TTL expiry.

**Effort**: Small (modify statechart_engine.py line 199 to load checkpoint on session_id match)

**Resolves**: P2 (TTL expiry -- partially)

**Does not resolve**: P1 (Redis restart), P3, P4, P5

### Option C: Add PostgreSQL Persistence for L3 Core Sessions

**What**: Create `aurora_core_sessions` table. Write L3 session state to PostgreSQL on every turn. On Redis miss, load from PostgreSQL.

**Effort**: Medium (1 new table, modify AuroraCoreSessionStore)

**Resolves**: P3 (L3 session loss)

### Option D: Unified Session State Object

**What**: Create a single `SessionState` aggregate that encompasses FSM state, checkpoint, feedback, and context versions. Persist the aggregate as a single PostgreSQL row with Redis caching.

**Effort**: Large (refactor 7+ files, new table, migration strategy)

**Resolves**: All pain points

**Risk**: High regression potential; requires careful migration

### Recommendation

**Phased approach:**

1. **Immediate (1-2 days)**: Implement Option B (TD-008 checkpoint resume). This is the highest-ROI, lowest-risk change. The checkpoint is already being saved; it just needs to be loaded.

2. **Short-term (1 week)**: Implement Option A (FSM state PostgreSQL table) to protect against Redis restarts. The `SessionStateManager.update_state()` method is the single write point; adding a parallel PostgreSQL write is low-risk.

3. **Medium-term (2 weeks)**: Implement Option C (L3 Core Session PostgreSQL persistence). The `AuroraCoreSessionStore.save()` method is the single write point.

4. **Long-term**: Evaluate Option D after the above changes are stable and metrics show the remaining gaps.

---

## 12. File Index

| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/orchestration/state_manager.py` | 1-680 | FSM state Redis persistence, locks, idempotency |
| `backend/app/orchestration/statechart_engine.py` | 1-358 | StateGraph engine, WorkflowState blackboard |
| `backend/app/orchestration/session_state_mixin.py` | 1-1033 | Session feedback, context versions, situation brief |
| `backend/app/orchestration/orchestrator.py` | 1-3430+ | Main orchestrator, FSM transitions, process_stream |
| `backend/app/orchestration/state_snapshot.py` | 1-369 | State snapshot for LangGraph planning |
| `backend/app/checkpoint/redis_checkpointer.py` | 1-83 | WorkflowState checkpoint Redis persistence |
| `backend/app/agents/standard_workflow.py` | 3055-3200 | Standard chat StateGraph definition |
| `backend/app/aurora/runtime_v1/state.py` | 1-792 | AuroraState, AuroraRuntimeStore, AuroraEnergyStore |
| `backend/app/aurora/runtime_v1/models.py` | 1-100 | PostgreSQL models for snapshots, wakes, telemetry |
| `backend/app/aurora/runtime_v1/persistence.py` | 1-287 | AuroraPersistenceStore (PostgreSQL R/W) |
| `backend/app/aurora/runtime_v1/checkpoint_runtime.py` | 1-1420 | Checkpoint follow-up runtime service |
| `backend/app/aurora/runtime_v1/service.py` | 1-2516+ | AuroraRuntimeV1Service main service |
| `backend/app/aurora/runtime_v1/self_model.py` | 1-100+ | Self model Redis store (30-day TTL) |
| `backend/app/aurora/runtime_v1/write_pipeline.py` | 1-740+ | Write pipeline claims and temporary state |
| `backend/app/aurora/core_session.py` | 1-470+ | L3 Core Session FSM, store, and service |
| `backend/alembic/versions/s40b1c2d3e4_add_aurora_runtime_v1.py` | 1-117 | Aurora runtime v1 tables migration |
| `backend/alembic/versions/stage_c5_aurora_decision_telemetry.py` | 1-102 | Decision telemetry table migration |
| `backend/app/config/settings.py` | 771-809 | Feature flags and context data limits |
| `backend/app/orchestration/session_feedback.py` | 1-10 | SESSION_FEEDBACK_TTL_SECONDS = 6h |

---

## 13. Summary Statistics

| Metric | Value |
|--------|-------|
| Distinct Redis key families | 19 patterns |
| TTL policies | 5 distinct values (30s, 5m, 30m, 1h, 6h, 24h, 48h, 30d) |
| PostgreSQL tables for Aurora state | 3 |
| FSM state machines | 2 (chat FSM: 6 states, L3 core: 8 stages) |
| StateGraph nodes | 11 |
| State writes per message | 8-12 Redis writes |
| State reads per message | 15-25 Redis reads |
| Max context_data size | 200 keys * 10KB = 2MB theoretical |
| Points of total state loss | Redis restart, L3 idle timeout, FSM TTL expiry |

---

---

## 14. Implementation Addendum — Safe Recovery Pass (2026-05-02)

**Status**: Implemented in code after this research report. This addendum supersedes the earlier "no recovery path" statements for the specific paths below; the original analysis remains useful as the pre-fix baseline.

### 14.1 What Changed

| Area | New behavior | Files |
|------|--------------|-------|
| TD-008 StateGraph checkpoint resume | Checkpoints now carry `session_id`, `request_id`, `checkpoint_kind`, `incomplete`, `saved_at`, `expires_at`, and `completed_at`. `StateGraph.invoke(..., resume_policy="interrupted_only")` only resumes same-request incomplete checkpoints and merges durable context into the fresh request state without overwriting volatile context or the new user message. | `backend/app/checkpoint/redis_checkpointer.py`, `backend/app/orchestration/statechart_engine.py`, `backend/app/orchestration/execution_engine.py` |
| FSM durable fallback | `SessionStateManager` can write recoverable FSM snapshots to PostgreSQL and load them on Redis miss. `DONE` states are marked non-recoverable so completed turns are not resurrected. | `backend/app/orchestration/state_manager.py`, `backend/app/aurora/runtime_v1/models.py` |
| L3 Core Session durability | `AuroraCoreSessionStore` now writes snapshots to PostgreSQL and reloads by session id, latest user session, or resume token hash when Redis misses. | `backend/app/aurora/core_session.py`, `backend/app/aurora/runtime_v1/models.py` |
| L3 idle handling | A 10-minute idle gap now pauses the session instead of expiring it immediately. Users can return to the same calibration without re-explaining previous turns; hard expiry still produces a visible summary. | `backend/app/aurora/core_session.py` |
| Return experience tiers | Returning context now distinguishes `silent_resume`, `light_resume`, `personalized_return`, and `checkpoint_debrief`, so the UX can choose how much to surface instead of treating every return as a 3-day checkpoint. | `backend/app/orchestration/context_builder.py` |
| Schema | Added durable recovery tables. | `backend/alembic/versions/c11_20260502_add_session_recovery_snapshots.py` |

### 14.2 Recovery Semantics

| Scenario | Result after this pass |
|----------|------------------------|
| Same request interrupted mid-graph | Can resume from the last incomplete pre-node checkpoint if `request_id` matches. |
| New user turn after 1h | Does **not** blindly resume old graph execution; instead receives returning context and fresh orchestration. |
| Redis miss for in-progress FSM | Loads a recoverable PostgreSQL snapshot when present and rehydrates Redis. |
| Redis miss for completed FSM | Does not recover; completion remains complete and idempotency cache window is preserved separately. |
| Redis miss for L3 Core Session | Loads from PostgreSQL and rehydrates Redis, including the message history and resume token lookup. |
| L3 idle >10min but before hard expiry | Session becomes `paused` with a user-visible "we can continue here" message. |

### 14.3 Verification Added

| Test | Coverage |
|------|----------|
| `tests/orchestration/test_statechart_engine.py::test_interrupted_checkpoint_resume_preserves_fresh_message_and_volatile_context` | Same-request checkpoint resume preserves new user message and volatile context. |
| `tests/orchestration/test_statechart_engine.py::test_checkpoint_resume_does_not_run_for_new_turn_request` | New request does not accidentally use a stale checkpoint. |
| `tests/unit/test_session_recovery_persistence.py` | FSM Redis miss restores recoverable states and refuses `DONE` recovery. |
| `tests/unit/test_aurora_core_session_entry.py::test_core_session_loads_from_postgres_when_redis_misses` | L3 Core Session can resume from PostgreSQL after Redis loss. |
| `tests/unit/test_aurora_core_session_entry.py::test_core_session_idle_timeout_pauses_instead_of_expiring` | Idle timeout pauses rather than destroying deep calibration state. |

### 14.4 Remaining Boundaries

- Multi-device strong coordination remains out of scope; this pass provides consistent latest-session recovery and return context, not cross-device locking.
- PostgreSQL snapshots are fallback durability, not a unified Session State aggregate. A future Option D can still consolidate these layers once behavior stabilizes.
- Redis RDB/AOF configuration remains an infrastructure choice; application-level recovery now no longer depends on it for the covered session paths.

*End of updated analysis.*

---

## 15. Implementation Addendum — Aurora Complete Experience Closed Loop (2026-05-02)

**Status**: Implemented after the safe recovery pass. This addendum records the shift from state continuity to outcome continuity: Aurora decisions are no longer only prompt modifiers; they now enter SGW feedback and delayed effectiveness evaluation.

### 15.1 What Changed

| Area | New behavior | Files |
|------|--------------|-------|
| DualCore signal surface | `DualCoreDecision` now includes `signal_scores`, `routing_trace_id`, and `scaffolding_zone`. | `backend/app/orchestration/dual_core_router.py` |
| SGW feedback bridge | Routing decisions are written as `PassiveSignal(signal_type="routing_decision")`; delayed evaluation writes `BehavioralOutcome(outcome_type="routing_effectiveness")` and updates `ScaffoldingFSM`. | `backend/app/services/routing_outcome_service.py`, `backend/app/orchestration/routing_engine.py` |
| L3 API durability | Core Session REST endpoints pass `db` into `AuroraCoreSessionService`, so Redis miss fallback to PostgreSQL is active on the product API path. | `backend/app/api/v1/aurora.py` |
| CaseFile / Agenda | Core Session state now persists a `case_file` evidence package and returns a backend-authoritative agenda projection. | `backend/app/aurora/core_session.py` |
| Observability | Added metrics for routing passive signals, routing outcomes, core-session lifecycle events, returning tiers, and correction-to-state-change. | `backend/app/core/metrics.py` |
| Returning context memory | Stage34 memory injection ranks recent episodic memories by correction count, importance, and confidence before recency. | `backend/app/orchestration/context_builder.py` |

### 15.2 Product Semantics

| User-facing promise | Implementation evidence |
|---------------------|-------------------------|
| “Aurora remembers what I corrected.” | Corrections persist receipts and working-memory entries; returning context and routing input consume recent corrections. |
| “Aurora changes how it responds after being wrong.” | Correction metrics expose state/self-model/correction changes; routing profile updates still run through `CorrectionFeedbackProcessor`. |
| “Aurora deep session has a visible structure.” | `agenda_snapshot()` exposes enter/explain/confirm/apply/close so the UI can show where the session is. |
| “Aurora learns if its route worked.” | Routing evaluator feeds delayed success/failure into `ScaffoldingFSM.apply_feedback()`. |

### 15.3 Verification Added

| Test | Coverage |
|------|----------|
| `tests/unit/test_dual_core_router_real_engine.py::test_scaffolding_snapshot_changes_router_surface` | SGW scaffolding state affects DualCore routing surface. |
| `tests/unit/test_aurora_closed_loop.py::test_routing_decision_records_passive_signal_and_sgw_outcome` | Routing decision -> PassiveSignal -> BehavioralOutcome -> ScaffoldingFSM feedback. |
| `tests/unit/test_aurora_closed_loop.py::test_core_session_case_file_agenda_survive_redis_miss` | CaseFile and Agenda survive Redis loss through PG fallback. |

### 15.4 Remaining Boundaries

- Multi-device strong coordination remains intentionally deferred.
- The current memory ranking is semantic-adjacent and correction-aware; full vector semantic retrieval for returning context remains a later enhancement.
- UI polish still needs device-level QA for the pacing and visual feel of multi-message Core Session rendering.
