# Reviewer A — E17: Aurora checkpoint surface交互正确性
Timestamp: 2026-04-26T12:15:00+08:00
Chain Index: 22

## Chain Flow Summary

The checkpoint surface operates via a three-stage pipeline: (1) **Celery scan** triggers `scan_and_send_checkpoint_nudges` which writes an `AuroraNudgeEntry` widget into the user's chat stream; (2) **User taps CTA** which fires `checkpoint_debrief_start` → `CheckpointDebriefService` runs a hardcoded 3-turn state machine; (3) **Finalize** calls `AuroraCheckpointRuntimeService.finalize_checkpoint_debrief` which persists state to DB+Redis, schedules follow-up wakes, and optionally triggers `AdaptiveReplanner.adjust_for_checkpoint`. Wake processing via `process_due_wakes` can send follow-up messages later.

## Critical Issues 🔴

**1. `AuroraRuntimeStore.load_runtime_state` is defined but NEVER called from production code**

- `state.py:394` defines `load_runtime_state()` with a full Redis read+deserialize path
- `service.py:1780` `_persist_runtime_state()` writes to `aurora:runtime:{user_id}:aurora_checkpoint:{conversation_id}` every turn
- `checkpoint_runtime.py:1018` `_write_runtime_state()` also writes to the same key
- **Neither service ever reads it back**. The `plan_turn()` method in `service.py:378` builds the entire dashboard readout from scratch each turn, ignoring previously persisted state
- Evidence: `grep -rn "load_runtime_state" backend/app/ --include="*.py" | grep -v test_ | grep -v "__pycache__"` returns zero results in production code
- **Impact**: If Aurora identified specific tensions, latent threads, or activity profile adjustments in a previous checkpoint turn, they are completely lost. The "resume" described in the chain description does not exist — there is no context continuity between checkpoint surface turns.

**2. Checkpoint debrief is a hardcoded 3-turn script with zero Aurora cognition**

- `checkpoint_nudge_service.py:192-300` `CheckpointDebriefService.process_turn()` uses hardcoded response strings ("这个检查点的情况怎么样？", "哪个部分你感觉最踏实？", "卡在哪里了") — no LLM call, no decision loop
- The Aurora decision loop (`AuroraDecisionLoop.decide`) is only invoked during `finalize_checkpoint_debrief` (after the debrief is already over) and during wake processing
- **Impact**: Users see static scripted responses instead of personalized coaching. Aurora cannot adapt its questions based on what it already knows about the user's plan, Galaxy nodes, or past performance.

**3. `aurora_checkpoint` surface excludes `cold_start_context` from the decision loop**

- `dashboard.py:253-258` `_SURFACE_CONTEXT_EXCLUSIONS["aurora_checkpoint"]` excludes `cold_start_context`
- This means during checkpoint turns, Aurora cannot see: confirmed weak nodes, strategy preference, sprint pack nodes, deep pattern alerts, previous sprint summary, galaxy weak nodes
- **Impact**: Even if Aurora's decision loop were active during checkpoint turns, it would be blind to the most valuable diagnostic data — exactly the data that checkpoint reviews need most.

## Major Issues 🟡

**1. Goal-met detection is crude and misses hedging language**

- `checkpoint_nudge_service.py:378-380` `_goal_met_from_text()` returns True if no NEGATIVE_MARKERS are present. Markers: 落后, 没完成, 没做完, 跑偏, 没时间, 来不及, 没跟上, 没有完成
- Missing: hedging phrases like "还行", "一般", "不太确定", "差不多", "马马虎虎", "说不上来", "有点模糊"
- A user saying "还行吧，有些地方不太确定" would be classified as goal_met=True, skipping adaptive replanning
- Evidence: `NEGATIVE_MARKERS` tuple at line 177-186

**2. Multiple concurrent checkpoint debriefs can collide**

- `checkpoint_nudge_service.py:329-335` `_start_session()` writes `debrief:active:{session_id}` → `nudge_id` to Redis with 1-hour TTL
- If a second checkpoint nudge fires while the first debrief is still active (within the 1-hour window), `_start_session` overwrites the `active` key with the new nudge_id
- The old debrief session data remains in Redis but `_get_active_session` can no longer find it
- **Impact**: The user's in-progress first debrief is silently abandoned. The `_get_active_session` method only tracks ONE active debrief per session.

**3. Follow-up wake messages bypass Aurora's chat rendering path**

- `checkpoint_runtime.py:459-481` `_process_single_wake` creates `ChatMessage` objects directly with `self.db.add()`
- These messages include `actions` with `aurora_runtime_follow_up` type, but this action type has no mobile UI handler
- `chat_notifier_actions.dart` only handles: `prompt`, `checkpoint_debrief_start`, `route`, `switch_plan`, `open_task`
- **Impact**: Follow-up messages from wakes arrive as plain text without any interactive widget, losing the "acknowledge and continue" affordance.

## Minor Issues 🟢

**1. Debrief session TTL is only 1 hour**

- `checkpoint_nudge_service.py:26` `DEBRIEF_SESSION_TTL_SECONDS = 60 * 60` (1 hour)
- If a user starts a debrief but doesn't complete it within 1 hour (e.g., gets distracted), the Redis state expires and the debrief is lost
- The next user message will not trigger debrief continuation — `_get_active_session` returns None
- This is aggressive for an app targeting students who may study in interrupted sessions

**2. Runtime state TTL is 24 hours but wake scheduling can extend beyond that**

- `checkpoint_runtime.py:30` `RUNTIME_STATE_TTL_SECONDS = 24 * 60 * 60`
- Wake delays can be up to 42 hours (`delay_hours = max(4.0, min(42.0, delay_hours))` at line 1200)
- If a wake is deferred multiple times, the runtime state key may expire before the wake fires
- Impact: The wake still fires (it has its own DB record), but the `_write_runtime_state` update at line 489 writes to a key that was already expired and re-creates it

## Working Well ✅

**1. State persistence to both DB and Redis**: `AuroraStateSnapshot` (DB) and Redis `aurora:runtime:*` provide dual persistence. DB snapshots survive Redis restarts. (`models.py:14-41`, `checkpoint_runtime.py:245-291`, `checkpoint_runtime.py:1018-1078`)

**2. Wake scheduling with comprehensive safety**: DND windows, privacy boundaries, urgency-based follow-up policy, recent activity grace periods, and max deferral limits all work correctly. (`checkpoint_runtime.py:523-627`, `checkpoint_runtime.py:703-869`)

**3. Follow-up timing decisions are well-gated**: `_evaluate_due_follow_up_timing` has 7 different suppression/cancellation/deferral conditions before deciding to execute, preventing nagging. (`checkpoint_runtime.py:703-869`)

**4. Sprint Pack mistake injection**: `dashboard.py:655-674` `_inject_sprint_pack_mistakes_into_checkpoint` correctly loads Sprint Pack mistake types into checkpoint_state for targeted error analysis. Strategy default `error_analysis_required=True` for checkpoint surface is correct. (`decision_loop.py:1562-1563`)

**5. Mobile widget integration**: `AuroraNudgeEntry` renders correctly in `action_card.dart` (line 896-897), with proper debrief_context passthrough and CTA button. `chat_notifier_actions.dart` handles `checkpoint_debrief_start` correctly.

**6. Orchestrator debrief integration**: `orchestrator.py:1909-1936` correctly intercepts debrief responses and short-circuits the normal chat flow, returning the debrief message with `debrief_mode: "checkpoint"` metadata.

## Files Examined

- `backend/app/aurora/runtime_v1/service.py` (1969 lines)
- `backend/app/aurora/runtime_v1/state.py` (482 lines)
- `backend/app/aurora/runtime_v1/decision_loop.py` (1749 lines)
- `backend/app/aurora/runtime_v1/checkpoint_runtime.py` (1359 lines)
- `backend/app/aurora/runtime_v1/dashboard.py` (1666 lines)
- `backend/app/aurora/runtime_v1/models.py` (100 lines)
- `backend/app/services/checkpoint_nudge_service.py` (475 lines)
- `backend/app/orchestration/orchestrator.py` (lines 1900-1959)
- `mobile/lib/features/chat/presentation/widgets/aurora_nudge_entry.dart` (67 lines)
- `mobile/lib/features/chat/presentation/widgets/action_card.dart` (nudge_entry references)
- `mobile/lib/features/chat/presentation/widgets/plan_strategy_card.dart` (checkpoint display)
- `mobile/lib/features/chat/presentation/providers/chat_notifier_actions.dart` (lines 54-120)

## Confidence: High — Traced full pipeline from Celery scan through debrief state machine to wake processing and mobile rendering. Core issues confirmed via grep for load_runtime_state usage (zero results in production code).
