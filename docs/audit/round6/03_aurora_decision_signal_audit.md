# Aurora Decision Loop & Signal Processing Audit (R6-03)

> Agent: Opus | Scope: decision_loop.py, l0_rules.py, l1_light_aurora.py, signal_aggregator.py, engine.py, l2_intervention.py, l3_full_core.py, kill_switch.py, privacy.py, state.py, control_surface.py, energy_controller.py, state_aggregator/service.py
> Lines covered: ~5,100 | Date: 2026-05-15

---

## Part 1: Architecture Analysis

### 1.1 Decision Loop Architecture

The Aurora system operates a four-layer escalation hierarchy:

**L0 (l0_rules.py, 182 lines)** -- Pure deterministic rules, no LLM, no state mutation beyond StateRegister upserts. Evaluates `deadline_pressure` and `quiet_hours` at each turn. Outputs `ActionableSignal` objects to Redis-backed `StateRegister`.

**L1 (l1_light_aurora.py, 158 lines)** -- Per-turn lightweight sensing. Composes L0 rule evaluation + `RetrievalIntentClassifier` + `EnergyLevelDecider` into an `L1TurnResult`. The `should_escalate` flag is set when energy level is L2 or L3. This module is intentionally LLM-free.

**L2 (decision_loop.py, 1,834 lines)** -- The core LLM-driven cognitive decision loop. Receives a `DashboardReadout`, builds a structured prompt, calls LLM for JSON decision, then applies deterministic post-processing via `validate_decision()` and `_stabilize_decision()`. Also handles the `Standard Layer Contract` that constrains downstream chat generation.

**L2 Intervention (l2_intervention.py, 182 lines)** -- Pattern-based escalation detector. Checks `StateRegister` entries against four escalation patterns (`knowledge_crisis`, `execution_collapse`, `exam_underwater`, `burnout_risk`) with a 1-hour cooldown per pattern.

**L3 (l3_full_core.py, 498 lines)** -- Interactive modeling session engine. Entry guarded by 8 wake conditions, daily quota (1-3 depending on sprint mode), cooldown (1-6 hours). Executes structured agenda items and produces `SessionClosure` with `StatePatch` and `PolicyChange`.

**L4 (l4_async.py)** -- Background analysis (not audited in this round).

Two parallel paths exist:
- **SpineOrchestrator path**: Event-driven, runs L0 -> L1 -> optionally L2Intervention
- **AuroraRuntimeService path**: Chat-driven, builds DashboardReadout -> L2 DecisionLoop

These paths share state via Redis `StateRegister` but have no programmatic bridge for L1 escalation signals.

### 1.2 Signal Aggregation Pipeline

`SignalAggregator` (signal_aggregator.py, 439 lines) collects from 10 signal sources across three tiers:
- **CORE**: memory_service, focus_service, error_book_service (stale threshold: 1 day)
- **ENHANCED**: companion_state, strategy_state, persona, plan_state (stale threshold: 3 days)
- **OPTIONAL**: achievement_engine, predictive, analytics (stale threshold: 7 days)

Budget enforcement (default 4000 tokens) trims OPTIONAL first, then ENHANCED, then CORE. Achievement engine payload is exempted from `_compact_payload()` compression. Signal collection is sequential (not parallel despite having no dependencies between sources).

`StateAggregatorService` (state_aggregator/service.py, 1,190 lines) is a separate, larger aggregation layer that collects 21 user state fields directly from PostgreSQL. It has its own TTL-based cache, kill switch integration (Stage 18 + Stage 33 for social signals), and shadow mode support.

### 1.3 Privacy & Safety Boundaries

**PII redaction (privacy.py, 149 lines)**: Implements regex-based redaction for emails, Chinese phone numbers, CN IDs, bank cards, and names (Chinese label/self-reference and English). Uses a kill-switch-gated `pii_redaction_mode()` that supports off/shadow/live. Includes `laplace_noise()` for differential privacy on numeric values.

**Critical gap**: `redact_pii()` is never called from `decision_loop.py`, `dashboard.py`, or any `runtime_v1` module. The `user_message` flows into the LLM prompt without PII stripping. Privacy filtering relies solely on `AuroraHardBounds.privacy_boundaries` which blocks specific domains, not PII content within messages.

**Forbidden domain guard (decision_loop.py:1162-1166)**: `_contains_forbidden_domain()` checks LLM output against `FORBIDDEN_MODELING_DOMAINS` (16 entries) with `ALLOWED_DOMAIN_GUARD_TERMS` (6 whitelist entries). Runs twice -- in `validate_decision()` and `_revalidate_stabilized_decision()`.

### 1.4 Kill Switch Integration

**Core kill switch (kill_switch.py, 155 lines)**: Proper tri-state implementation with `KillSwitchBinding`, Redis-backed `read_mode()`/`write_mode()`, Prometheus gauge recording, and settings fallback chain.

**Aurora-specific gaps**:
- `AuroraRuntimeConfig` (config.py) uses static `aurora_flags.AURORA_SHADOW_MODE` and `AURORA_ACTIVE` -- no Redis-backed dynamic switching
- `AuroraRuntimeStore`, `AuroraEnergyStore`, `ControlSurfaceService` all use static `settings.ENABLE_AURORA_RUNTIME_V1`
- `AuroraDecisionLoop`, `L0RuleEngine`, `L1LightAurora`, `L2InterventionEngine` have zero kill switch integration
- `StateAggregatorService` properly checks Stage 18 and Stage 33 kill switches per field

### 1.5 State Management

- **AuroraRuntimeStore**: Redis-backed with `aurora:runtime:{user_id}:{surface}:{conversation_id}` keys, 24h TTL. Surface index enables latest-surface lookup.
- **AuroraEnergyStore**: Redis-backed with `aurora:energy:{user_id}` keys, 48h TTL. Tracks L3 session count and cooldown.
- **StateRegister**: Redis-backed signal store used by L0/L1/L2 to share state.
- **ControlSurfaceService**: Redis hash `aurora:control:{user_id}` with 24h TTL. Stores `ActivityProfile` with harness parameters.
- **In-memory cache**: `StateAggregatorService._cache` with per-field TTL and LRU eviction at 500 entries.

---

## Part 2: Problem Report

| ID | Severity | File:Line | Issue | Root Cause | Fix |
|----|----------|-----------|-------|------------|-----|
| P0-01 | P0 | decision_loop.py:1093; dashboard.py:339 | user_message sent to LLM without PII redaction | `build_prompt()` includes `readout.user_message` via `_slim_readout_for_surface()` which has no privacy filtering. `redact_pii()` from privacy.py exists but is never called in the decision loop path. | Call `redact_pii(readout.user_message)` in `_slim_readout_for_surface()` before including in LLM payload. Also redact any text fields in `profile_context`, `cold_start_context`, and `task_state` that may contain user-originated PII. |
| P0-02 | P0 | decision_loop.py:1093 | LLM prompt injection via user_message -- no length limit or content sanitization | `user_message` is included verbatim in the JSON payload sent to the LLM. There is no truncation, no structural isolation between user content and decision schema, and no content filtering. An attacker can craft messages to manipulate the JSON decision output (override action, set arbitrary harness_updates, bypass forbidden domains). | (1) Truncate user_message to 500 chars before inclusion. (2) Strip JSON-special characters from user_message. (3) Place user_message in a separate message from the decision schema. (4) Validate `metadata.reasoning_summary` length in output. |
| P0-03 | P0 | l0_rules.py:19-20,90-110 | Quiet hours check uses UTC time instead of user local timezone | `_utcnow()` returns UTC time, and `evaluate_quiet_hours()` compares UTC minutes directly against `quiet_start`/`quiet_end` without timezone conversion. For China (UTC+8), a 22:00-08:00 quiet window is incorrectly matched against UTC 22:00-08:00 (actual Beijing 06:00-16:00). This affects the majority user base. `AuroraHardBounds.is_within_dnd()` correctly uses `timezone_name` for conversion, creating an inconsistency. | Add `timezone: str = "UTC"` parameter to `evaluate_quiet_hours()`. Convert UTC time to local time before comparison using `ZoneInfo(timezone)`. Pass user timezone from context in `L1LightAurora.run_turn()`. |
| P1-01 | P1 | state.py:376 vs energy_controller.py:163-164 | L3 daily quota hardcoded mismatch | `AuroraEnergyState.can_user_wake` property uses hardcoded `self.l3_session_count_today < 3`. `CostController.check_l3_allowed()` uses `AuroraEnergyStore.DAILY_QUOTA` where default=1. These are the primary gate vs. the secondary gate, and they disagree on the limit for default mode. A user in default sprint mode could pass `can_user_wake` (limit 3) but be rejected by `CostController` (limit 1), or vice versa if they diverge further. | Remove hardcoded `3` from `can_user_wake`. Make it a method accepting `sprint_mode` and querying `DAILY_QUOTA`. Ensure `EnergyLevelDecider` and `CostController` use the same quota source. |
| P1-02 | P1 | signal_aggregator.py:313-315 | Signal collection exceptions silently swallowed | `_collect_readings()` catches all exceptions with `except Exception: payload = {}` with no logging. If a CORE tier source (memory_service, focus_service) fails, the system treats it as "no data available" rather than "service error", potentially leading to wrong strategy decisions based on missing-but-assumed-empty data. | Add `logger.warning("Signal collection failed for %s: %s", spec.name, exc)` in the except block. Consider adding `collection_errors` to `SignalSnapshot` to expose failures to downstream consumers. |
| P1-03 | P1 | signal_aggregator.py:317 | achievement_engine exempted from payload compression | `compacted = payload if spec.name == "achievement_engine" else _compact_payload(payload)` -- the only signal source with this exemption. As an OPTIONAL tier source, a large achievement payload can consume disproportionate budget, potentially causing CORE tier signals to be trimmed first despite the intended priority order. | Apply `_compact_payload()` to achievement_engine output with same parameters as other sources, or use slightly relaxed parameters. If full achievement data is needed, elevate it to ENHANCED tier. |
| P1-04 | P1 | signal_aggregator.py:308-329 | Signal collection is sequential, not parallel | Despite having no interdependencies, all 10 signal sources are collected sequentially in a for loop: `for spec, _service, coro in tasks: await coro`. Total latency is the sum of all source latencies rather than the max. | Use `asyncio.gather(*coros, return_exceptions=True)` to collect all sources in parallel. Process results with matching spec indices. |
| P1-05 | P1 | decision_loop.py:896-1005,1788-1790 | System prompt length unbounded while output max_tokens is only 320/600 | `_max_tokens_for_readout()` returns 320 (normal) or 600 (extended) for output, but the system prompt in `build_prompt()` has no length cap. When all conditional rules activate (sleep guard, strategy recalibration, spine rules, achievement rules, deep pattern alert, last-24h mode, stuck task), the system prompt alone can exceed 4000 characters (~1000 tokens). Combined with the user message payload, this risks exceeding API context limits and triggering the fallback path. | Add system prompt length budget (e.g., 3000 chars). When exceeded, drop lower-priority rules. Monitor and log input token counts. |
| P1-06 | P1 | engine.py:59-89 vs decision_loop.py:846-860 | AuroraEngine and AuroraDecisionLoop produce independent, potentially conflicting decisions | `AuroraEngine.decide_backbone_route()` produces a deterministic `TransitionDecisionRecord` (stay/transition). `AuroraDecisionLoop.decide()` produces an LLM-driven `AuroraDecision` (emit_message/wait/etc). These can conflict: Engine says "stay" while DecisionLoop says "emit_message". No cross-validation exists. | Establish clear precedence: if Engine decides "stay", constrain DecisionLoop actions to `wait`/`update_state`. Add cross-check before final decision output. |
| P1-07 | P1 | decision_loop.py:1096-1147 | L2 decision can override L0 quiet_hours signal | L0 generates `quiet_hours_active` signal to suppress notifications and reduce intervention intensity. However, `validate_decision()` does not check this signal. The LLM can return `schedule_wake` or high-intensity `emit_message` that passes validation despite L0 quiet hours being active. DND windows from `AuroraHardBounds` are checked for wake scheduling, but quiet_hours is a separate concept from DND. | Check `quiet_hours_active` in `validate_decision()`. If active, downgrade action from `emit_message` to `wait` (unless already in an active conversation turn) and enforce `max_response_length: brief`. |
| P1-08 | P1 | config.py:12-13; control_surface.py:164-165; state.py:398-399 | Aurora Runtime V1 uses only static config, no dynamic tri-state kill switch | `AuroraRuntimeConfig` reads from `aurora_flags.AURORA_SHADOW_MODE` and `AURORA_ACTIVE`. `ControlSurfaceService`, `AuroraRuntimeStore`, `AuroraEnergyStore` all use `settings.ENABLE_AURORA_RUNTIME_V1`. None register `KillSwitchBinding` or call `read_mode()`. This violates the project's tri-state kill switch protocol. | Register `KillSwitchBinding(stage="aurora", feature="runtime_v1", ...)` for each component. Check kill switch at entry points. Implement shadow mode (execute but don't apply side effects). |
| P1-09 | P1 | l3_full_core.py:438-452 | `_get_last_activity()` never checks agenda items for latest activity | The method retrieves `created_at` from the session but ignores activity timestamps from agenda items. It also calls `session.get("agenda", {}).get("agenda_items", [])` on line 441 without storing the result. This means `check_session_health()` always uses session creation time for idle timeout, causing premature or delayed idle detection. | Iterate agenda items to find the latest `done` or `replied` timestamp. Use that as `last_activity` instead of session `created_at`. |
| P1-10 | P1 | l3_full_core.py:187-196 | Unknown wake reasons auto-allowed with defaults | `validate_entry()` allows any unknown wake reason string, falling through to a default `strategy_recalibration` session type. This means typos or garbage strings in `wake_reasons` can trigger L3 sessions, consuming the limited daily quota. | Only allow wake reasons matching `_WAKE_CONDITIONS` keys. Return `allowed: False` for unrecognized reasons. |
| P1-11 | P1 | privacy.py:57-63 | `pii_redaction_mode()` uses `asyncio.get_event_loop().run_until_complete()` | This is a synchronous function that creates its own event loop to call an async service. If called from within an existing async context (which is the normal runtime), this can cause `RuntimeError: This event loop is already running`. The try/except falls back to settings, but silently degrades PII protection. | Refactor to `async def pii_redaction_mode()` and propagate async through callers. Or use an async-safe pattern like `asyncio.get_running_loop()`. |
| P2-01 | P2 | signal_aggregator.py:266-273 | `summary_digest` hash excludes `stale_signals` | The canonical hash for deduplication includes `snapshot_hash`, core/enhanced/optional payloads but not `stale_signals`. Two snapshots with identical payloads but different staleness produce the same digest. | Include `stale_signals` in the hash input for `summary_digest`. |
| P2-02 | P2 | l0_rules.py:77 | Deadline signal TTL uses `int()` truncation | `ttl_hours=int(nearest_hours) + 1` truncates toward zero. For `nearest_hours=0.1` (6 minutes), TTL=1 hour. For `nearest_hours=0.01` (36 seconds), TTL is still 1 hour. | Use `max(1, math.ceil(nearest_hours))` for more accurate TTL. |
| P2-03 | P2 | decision_loop.py:1162-1166 | Forbidden domain check relies on string replacement ordering | `_contains_forbidden_domain()` strips `ALLOWED_DOMAIN_GUARD_TERMS` via `str.replace()` before checking `FORBIDDEN_MODELING_DOMAINS`. The current logic is safe but fragile -- adding new terms to either set could create accidental bypasses through substring interactions. | Use word-boundary regex matching or token-level checking instead of substring replacement. |
| P2-04 | P2 | l1_light_aurora.py:83 | L1 appends L0 signal dicts to state list without type guard | `active_states.extend(signal.to_dict() for signal in l0_signals)` extends a list that may contain `StateFieldEnvelope` objects (from `_load_active_states`) with plain dicts (from L0 signals). `EnergyLevelDecider.decide()` then accesses `s.get("state_key")` and `s.get("confidence")` -- this works on dicts but would fail if `_load_active_states` returned non-dict objects. Current `_load_active_states` normalizes to dicts, so safe, but fragile. | Add explicit type annotation and normalization for `active_states` list elements. |
| P2-05 | P2 | l2_intervention.py:142-155 | `_state_matches()` uses float comparison without tolerance | `state["confidence"] < min_conf` uses direct float comparison. Float precision issues could cause a state with confidence exactly 0.7 to be rejected when `min_confidence=0.7` due to floating point representation. | Use `state["confidence"] < min_conf - 1e-9` or `not state["confidence"] >= min_conf`. |
| P2-06 | P2 | state_aggregator/service.py:228-231 | Cache eviction only triggers at >500 entries, not on TTL expiry | `if len(self._cache) > 500` triggers eviction of expired entries, but expired entries below 500 accumulate indefinitely. Long-running processes could hold stale cache entries for extended periods. | Use probabilistic eviction or time-based sweep in addition to size-based check. |

---

## Summary
- **P0**: 3 issues (PII exposure in LLM prompt, prompt injection via user_message, timezone-critical quiet hours broken for non-UTC users)
- **P1**: 11 issues (L3 quota mismatch, signal collection blind spots, system prompt budget, dual decision conflict, kill switch gaps, L3 session validation weaknesses, PII redaction async safety)
- **P2**: 6 issues (hash completeness, TTL precision, domain check robustness, type safety, float comparison, cache eviction)
- **Overall Assessment**: The Aurora decision loop has strong structural guards (forbidden domain check, hard bounds, standard layer contract) but has three critical gaps: (1) user PII flows unredacted into LLM prompts, (2) the user_message channel enables prompt injection into the JSON decision schema, and (3) the quiet hours check is broken for non-UTC users affecting the primary user base. The complete absence of dynamic kill switches for the runtime V1 layer is a significant operational risk. The L3 quota hardcoding discrepancy between `can_user_wake` and `CostController` could lead to either unexpected session denials or quota overruns.
