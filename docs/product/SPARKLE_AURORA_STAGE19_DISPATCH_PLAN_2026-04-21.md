# SPARKLE Aurora Stage 19 Dispatch Plan (2026-04-21)

> Workstream Bundle: `WS-WM-*`
> Phase Mapping: Roadmap v2.0 Stage 19A
> Scope: Working Memory + Consolidation + first LLM extractor integration

## 0. Locked Meta

### 0.1 Strategic scope

Stage 19 only executes Stage 19A. Sufficiency Judge, Conflict Resolver, and Route History are deferred to Stage 20. Skill MVP is deferred to Stage 21.

### 0.2 Architecture boundaries

1. Working Memory is a new transient layer, not an L1 cache.
2. Working Memory storage is Redis-only under `working_memory:<user_id>:<session_id>:<entry_id>`.
3. Consolidation still lands into Stage 16 `inferred_extraction` on `EpisodicMemory`.
4. LLM extraction runs in parallel with the Stage 16 rule path, but de-duplication happens inside Working Memory, not at a fragile pre-write synchronization point.

### 0.3 Codex self-check lock

1. Working Memory may not be implemented as L1 projection cache.
2. LLM output may not bypass Rule Y four-element validation.
3. Consolidation may not write non-repeated or weakly anchored content into L1.
4. Startup must run orphan cleanup, with TTL still acting as the hard fallback.

## 1. Workstreams

### WS-WM-RULE-AC

Land Rule AC definition, the Stage 19 dispatch artifact, `scripts/check_rule_ac_working_memory.py`, and the Stage 19 runner skeleton.

### WS-WM-CORE

1. Freeze Working Memory schema first.
2. Implement Redis-backed Working Memory service with:
   - per-session capacity `<= 40`
   - LRU + low-salience eviction
   - session end + 10 min TTL cap
   - idle 4h expiry
   - orphan cleanup
3. No SQLAlchemy model, no Alembic migration, no persistence write path under `backend/app/working_memory/`.

### WS-WM-LLM-EXTRACT

1. Land frozen prompt `backend/app/services/llm_extractor_prompt.v1.md`.
2. Default model string is `claude-haiku-4-5`.
3. Single call budget `<= 200` tokens, per-session budget `<= 2000`.
4. Dry-run is default ON.
5. Rule Y validation uses the same `InferredEpisodicCandidate` contract as Stage 16.

### WS-WM-CONSOLIDATE

1. Consolidation triggers:
   - `mention_count >= 3 && time_span_seconds >= 60`
   - explicit anchored confirmation
   - commitment with explicit `due_at`
2. Generic `是的` / `对` alone never qualify as confirmation.
3. Consolidation reuses Stage 16 write-lane conflict checks before L1 write.
4. Session-local denial may retract the newly consolidated L1 record and mark the WM entry rejected.

### WS-WM-AGGREGATOR-INTEGRATE

1. Extend `UserStateV1` to schema version `user_state.v1.1`.
2. Add `working_memory_snapshot`.
3. Update all three surfaces in one commit:
   - `backend/app/state_aggregator/schema.py`
   - `proto/user_state.proto`
   - `UserStateFieldName`
4. Run `make proto-gen`.
5. Re-check Router equivalence with the new field present; only KL delta is allowed, not old-field drift.

### WS-WM-MOBILE

1. Add a collapsible “AI 当前记住” drawer to chat.
2. Show top 10 session entries.
3. Support:
   - view source turn
   - forget
   - mark correct
4. Consolidated entries show an “已归档到长期记忆” badge.

### WS-WM-KILL

Three independent flags:

1. `SPARKLE_WORKING_MEMORY_ENABLED`
2. `SPARKLE_LLM_EXTRACTOR_ENABLED`
3. `SPARKLE_CONSOLIDATION_ENABLED`

## 2. Gate S19-FINAL

1. Rule AC guard passes with `0 violation`.
2. Working Memory contract tests pass.
3. LLM extractor dry-run precision `>= 0.85` with zero Rule Y hard violations.
4. Consolidation precision `>= 0.80`.
5. Aggregator `working_memory_snapshot` integration keeps old-field KL delta `<= 0.03`.
6. No `working_memory` SQL model or migration exists anywhere in the repo.

## 3. Audit Amendments Incorporated

1. WM-layer dedupe replaces vague “parallel compare before write”.
2. Explicit confirmation must be anchored; unscoped generic confirmation words are forbidden.
3. Aggregator integration explicitly depends on `proto/user_state.proto` regeneration.
4. TTL remains the hard fallback even if orphan cleanup misses a crash-era namespace.
