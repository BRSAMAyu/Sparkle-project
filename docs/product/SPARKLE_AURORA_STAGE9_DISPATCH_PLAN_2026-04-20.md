# SPARKLE Aurora Stage 9 Dispatch Plan (2026-04-20)

> **Status**: Stage 9 dispatch baseline v0 after Stage 8 final-accept
> **Authority**: `SPARKLE_AURORA_STAGE8_HANDOFF_2026-04-20.md` is the only Stage 8 truth source; this plan starts from that frozen baseline and must not reopen completed Stage 5 / Stage 6 / Stage 7 / Stage 8 work.
> **Depends on**:
> - `SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md`
> - `SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE8_HANDOFF_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE9_MET1_UTILIZATION_DEFINITION_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE9_IC2_CORRECTION_CHANNEL_2026-04-20.md`
> **Scope**: Stage 9 execution design. Converts the post-Stage-8 "user front door" gap into dispatchable workstreams, ownership boundaries, acceptance rules, and closeout gates.

## 0. Stage 9 Positioning

Stage 8 closed the drifting daily-loop breakpoints and hardened governance.
That means Stage 9 is not another loop-closure stage.

### One-sentence definition

**Stage 9 is the stage where the already-closed profile loop becomes a real user front door: the user can ask the system what it believes, correct it inside chat through the proper lane, and the system can evaluate these behaviors with stronger diagnostic signals.**

### What Stage 9 must treat as already settled

The following are frozen baseline facts unless new evidence proves a regression:

1. Rule K has a real local/CI hard stop.
2. breakpoints `#3 / #4 / #5` are closed and must not be reopened as unfinished work.
3. bounded dual-core steering is limited to the current 5-field whitelist and remains a session strategy lane, not a profile-truth lane.
4. mobile transparency/correction can consume canonical Stage 6/7/8 payloads.
5. the profile evaluator remains read-only with `write_scope = evaluation_records_only`.

### Stage 9 starting gaps

Per Stage 8 handoff and accepted Stage 9 design review notes, Stage 9 starts from exactly four work items:

1. `WS-MET1` prompt / inference utilization metric definition and collection baseline
2. `WS-IC1` in-chat profile query path with canonical read-only evidence-backed answers
3. `WS-IC2` in-chat profile correction path through the User Correction lane only
4. `WS-EV2` evaluator upgrade from deterministic fixture scoring to rubric / LLM-attached scoring while keeping evaluation-record-only writes

## 1. Stage 9 Principles

### Principle A: Front Door Beats New Plumbing

Stage 9 exists to expose already-landed system value to the user, not to create another backend-only closure.

Hard interpretation:

1. `WS-IC1` must produce a user-visible in-chat behavior, not just another profile API.
2. `WS-IC2` must let the user correct profile claims inside chat, not merely deep-link to existing settings.
3. `WS-EV2` must improve the trustworthiness of diagnosis and evaluation signals, not only refactor runner internals.

### Principle B: User Correction Is a Sovereign Lane

Any user-initiated correction remains a first-class user action and must not be normalized into Aurora control writes, dual-core steering, or strategy-lane side effects.

### Principle C: Evidence Must Stay Legible

If the system answers "this is how I currently see you," it must be able to distinguish:

1. raw evidence
2. projected / compiled claim
3. inferred / predictive conclusion
4. user correction

Stage 9 must not blur these categories in the user-facing answer surface.

### Principle D: Metrics Before Claims About Value

Stage 9 may not claim improved prompt / inference utilization without a formal metric definition and collection boundary.

`WS-MET1` therefore freezes the measurement contract before broader rollout claims are allowed.

### Principle E: Evaluator Upgrades Stay Read-Only

A better evaluator is valuable, but it must not become a hidden write channel back into the profile system.

### Principle F: Prefer Existing Product Seams Over Greenfield Surfaces

Stage 9 must stand on already-landed seams whenever possible:

1. `WS-IC1` should build on canonical transparency / insight payloads and tool runtime context.
2. `WS-IC2` should build on the existing profile write / override services as the User Correction lane, not on strategy state or Aurora writes.
3. `WS-EV2` should extend the Stage 7 runner rather than replacing it.
4. `WS-MET1` should build on current token-usage and client-observability foundations instead of inventing a separate telemetry stack.

## 2. Explicitly Out of Scope

The following are not Stage 9 scope unless a later amendment says otherwise:

1. graph-as-diagnostic productization
2. continuous-learning / distillation user-facing integration
3. dual interaction mode rollout
4. broader transparency redesign outside the in-chat profile front door
5. expanding the Stage 8 bounded-steering whitelist
6. any write path that merges User Correction into Aurora / L3 / strategy state
7. evaluator-triggered writes outside `evaluation_records_only`

## 3. Workstream Overview

| Workstream | Focus | Primary lane | User value | Priority | Risk |
| --- | --- | --- | --- | --- | --- |
| `WS-MET1` | utilization metric contract + collection baseline | observability | indirect | highest | low |
| `WS-IC1` | in-chat profile query with evidence-backed canonical answer | read-only profile front door | high | highest | medium |
| `WS-IC2` | in-chat profile correction via User Correction lane only | user correction | very high | highest | very high |
| `WS-EV2` | rubric / LLM-attached evaluator upgrade | evaluation | medium | high | medium |

### Wave Order

Stage 9 keeps the four-workstream scope, but the close order is intentionally staged:

1. `WS-MET1` must freeze the utilization definition before other Stage 9 value claims rely on it.
2. `WS-IC1` must reach final accept before `WS-IC2` enters implementation.
3. `WS-IC2` is the highest-risk user-facing lane and must not start from a vague write path.
4. `WS-EV2` is decoupled from the user front door and may implement in parallel after `WS-MET1` scope freezes, but its closeout must still preserve `evaluation_records_only`.

### Concrete judgments baked into Stage 9

1. `WS-IC1` means "the user can ask in chat what Sparkle currently believes and why," not "another profile screen payload."
2. `WS-IC2` means "the user can say this is wrong in chat and the correction goes through the User Correction lane," not "the assistant writes a strategy knob."
3. `WS-EV2` means stronger scoring semantics than hardcoded fixture rules, but still no profile writes.
4. `WS-MET1` means formalizing utilization so later stages can talk about prompt / inference usage with real denominators.

## 4. Dispatch Rules

Stage 9 inherits Rule G, Rule H, Rule I, Rule J, Rule K, Rule L, Rule M, Rule N, and Rule O.

### Rule P · User Correction Lane Sovereignty

Any in-chat profile correction must flow through the User Correction lane only.

Hard interpretation:

1. `WS-IC2` must not write through Aurora, dual-core, `UserStrategyStateService`, `CapabilityKnobGovernor`, or `adaptive_adjustments`.
2. `WS-IC2` must not reuse Stage 8 bounded-steering functions as a shortcut.
3. if a correction needs to update user-facing truth, it must go through direct correction / preference / override services that are already part of the profile-truth lane.

### Rule Q · Evidence Legibility

Any in-chat profile answer that presents a claim must make its evidence class explicit.

Hard interpretation:

1. raw evidence must be marked as raw evidence
2. projected / compiled conclusions must be marked as such
3. inferred predictions must be marked as inference / projection, not fact
4. user corrections must remain visibly attributable to the user

### Rule R · Evaluator Read-Only Discipline

Any `WS-EV2` upgrade must keep `write_scope = evaluation_records_only`.

Hard interpretation:

1. no evaluator result may write L1/L2/L3 profile state
2. rubric / LLM scoring artifacts may only land in evaluation records and runner outputs
3. a better score is not permission to mutate user truth

## 5. Review Lanes

High-risk lane:

`Codex design freeze -> implementation -> internal pre-accept -> user sign-off`

Medium-risk lane:

`Codex design freeze -> implementation -> internal pre-accept -> user sign-off`

Low-risk lane:

`Codex design freeze -> implementation -> internal pre-accept -> user sign-off`

### Stage 9 workstream lane assignment

| Workstream | Review lane | Reason |
| --- | --- | --- |
| `WS-MET1` | low-risk | observability definition and collection only |
| `WS-IC1` | medium-risk | user-facing read path without new write authority |
| `WS-IC2` | high-risk | user-facing correction path with strict Rule P boundary |
| `WS-EV2` | medium-risk | scoring-model upgrade with evaluation-only writes |

### Stage 9 high-risk triggers

Any task touching one of the following is automatically high-risk:

1. `backend/app/api/v1/profile_transparency.py`
2. any new in-chat correction handler / tool
3. `backend/app/services/personalization/profile_write_service.py`
4. any code path that writes explicit or inferred preferences from chat-originated correction flows
5. any attempted reuse of Stage 8 strategy-lane write helpers for `WS-IC2`

## 6. Hotspot Ownership

| File / Zone | Owner | Reason |
| --- | --- | --- |
| `backend/app/services/user_insight_transparency_service.py` | `WS-IC1` | canonical profile claims currently lack user-front-door evidence legibility |
| `backend/app/profile/projection_contract.py` | `WS-IC1` | canonical transparency payload seam |
| `backend/app/tools/` new profile-front-door tool module | `WS-IC1` / `WS-IC2` | chat-native query / correction tool surface |
| `backend/app/orchestration/prompts.py` | `WS-IC1` / `WS-IC2` | tool-use guidance for in-chat profile ask/correct flows |
| `backend/app/api/v1/profile_transparency.py` | `WS-IC2` | current explicit profile update / correction surface |
| `backend/app/services/personalization/profile_write_service.py` | `WS-IC2` | direct profile-truth write lane, distinct from L3 steering |
| `backend/app/services/profile_eval_runner.py` | `WS-EV2` | current deterministic runner seam |
| `backend/tests/profile/eval/fixtures/` | `WS-EV2` | rubric / runner fixture baseline |
| `backend/app/orchestration/response_builder.py` | `WS-MET1` | current prompt/completion token recording seam |
| `backend/app/orchestration/orchestrator_production.py` | `WS-MET1` | model/runtime token recording seam |
| `mobile/lib/core/services/client_observability_service.dart` | `WS-MET1` | client-side observability carrier |
| `mobile/lib/features/chat/` | `WS-IC1` / `WS-IC2` | user-front-door chat presentation and interaction |
| `docs/product/*STAGE9*` | `Codex` | sequencing, governance, metric definition, and closeout integration |

## 7. Workstream Cards

## 7.1 `WS-MET1` — Utilization Metric Definition

**Goal**

Freeze the formal metric definition and collection baseline for prompt / inference utilization.

**Why this exists**

Stage 8 closed loop plumbing, but future stages still lack a hard metric for whether profile/context data is actually being used by prompt rendering and final inference.

**Stage 9 in-scope**

- define prompt utilization numerator / denominator
- define inference utilization numerator / denominator
- define sampling window, aggregation cadence, and degradation behavior
- land a minimal collection scaffold on top of existing token-usage and observability surfaces

**Stage 9 out-of-scope**

- forcing Stage 9 product features to optimize the metric immediately
- introducing a new telemetry stack
- turning the metric into a merge-blocking production SLO

**Accept requires**

1. the metric-definition artifact is committed before implementation
2. collection code exists for backend and, where needed, client-side companion events
3. the handoff can show how numerator / denominator are derived

## 7.2 `WS-IC1` — In-Chat Profile Query

**Goal**

Let the user ask in chat what Sparkle currently believes about them and get a canonical, evidence-backed answer.

**Why this exists**

Stage 7 / 8 made the profile loop visible and governable, but the user still has to visit a profile surface to see it.

**Stage 9 in-scope**

- a chat-native tool / handler that reads canonical profile insight / transparency data
- answer shaping that distinguishes evidence classes
- evidence ids / refs or clear evidence-class markers in the response payload
- mobile / chat-side rendering and tests for the in-chat read path

**Stage 9 out-of-scope**

- writing profile truth
- graph visualization or graph-diagnostic surfaces
- broader transparency redesign

**Accept requires**

1. user can ask a natural-language profile question in chat and receive a canonical answer
2. response includes evidence refs or explicit evidence-class labels per Rule Q
3. answer is read-only and does not mutate profile state

## 7.3 `WS-IC2` — In-Chat Profile Correction

**Goal**

Let the user correct profile claims inside chat through the User Correction lane only.

**Why this exists**

This is the highest-value Stage 9 user-facing feature and the highest governance-risk feature.

**Stage 9 in-scope**

- chat-native correction intent / tool
- correction handler that maps to the User Correction lane
- feedback path that confirms what was corrected and what evidence / truth surface was updated
- tests proving chat-originated correction does not touch L3 steering

**Stage 9 out-of-scope**

- Aurora-side correction writes
- dual-core / strategy-lane writes
- broad auto-reconciliation logic that hides user agency

**Accept requires**

1. the correction-channel architecture artifact is committed before implementation
2. chat-originated correction writes avoid L3 / strategy-lane paths
3. a real end-to-end example shows user input -> correction write -> updated canonical read path
4. mobile / chat-side tests cover the user-visible correction flow

## 7.4 `WS-EV2` — Stronger Evaluator Runner

**Goal**

Upgrade the evaluator from hardcoded deterministic scoring to rubric and, where appropriate, LLM-attached scoring without breaking read-only discipline.

**Why this exists**

Stage 7 / 8 left `P2-2` as an explicit tail: current scoring is useful but too rigid to serve as the long-term evaluator surface.

**Stage 9 in-scope**

- rubric-driven evaluation structure
- optional LLM-attached scoring mode with explicit runner metadata
- fixture / baseline coverage for richer evaluation outputs
- preserved `evaluation_records_only` discipline

**Stage 9 out-of-scope**

- evaluator-triggered profile writes
- silent mutation of canonical truth

**Accept requires**

1. runner metadata clearly states whether scoring is deterministic, rubric-only, or LLM-attached
2. `write_scope = evaluation_records_only` stays true
3. fixtures and tests show richer diagnostic outputs than Stage 7

## 8. Stage 9 Mandatory Pre-Implementation Artifacts

Before any code lands for the listed workstreams, the following docs must exist:

1. `SPARKLE_AURORA_STAGE9_MET1_UTILIZATION_DEFINITION_2026-04-20.md`
2. `SPARKLE_AURORA_STAGE9_IC2_CORRECTION_CHANNEL_2026-04-20.md`

Hard interpretation:

1. `WS-MET1` may not implement collection before the metric-definition artifact freezes the contract.
2. `WS-IC2` may not implement correction code before the correction-channel architecture freezes the write boundary.
3. `WS-IC1` may start after `WS-MET1` is frozen.
4. `WS-IC2` may not start implementation until `WS-IC1` reaches final accept.

## 9. Entry Baseline

Stage 9 starts from the Stage 8 verified baseline:

- backend compatibility baseline: `144 passed`
- Stage 8 backend sweep: `50 passed`
- mobile user-surface sweep: `13 tests passed`
- Rule K guard: `35 files scanned`, pass

Any Stage 9 work that regresses this baseline fails entry and must stop.

## 10. Gate S9-Close

Stage 9 is closed only when all of the following are true:

1. all 4 workstreams are final-accepted
2. Stage 8 baseline stays green
3. the handoff contains at least one real in-chat profile query sample with evidence refs / class markers
4. the handoff contains at least one real in-chat correction sample showing the User Correction lane
5. `WS-EV2` runner metadata still declares `evaluation_records_only`
6. full post-close verification sweep is recorded, not just per-WS subsets
