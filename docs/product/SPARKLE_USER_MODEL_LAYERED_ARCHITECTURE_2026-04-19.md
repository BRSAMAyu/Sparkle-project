# SPARKLE User Model Layered Architecture (2026-04-19)

> **Status**: Architecture baseline for Stage 5 v1.2 and Stage 6 planning
> **Purpose**: define the layered user-model architecture in terms of current code reality, remaining gaps, and the boundary conditions for Stage 6.
> **Scope**: user-model data flow, write-path discipline, Aurora shadow-state positioning, and stage-level workstream boundaries.

---

## 1. Layered Responsibilities

Sparkle's user-model stack is treated as five cooperating lanes:

| Lane | Responsibility | Current role |
| --- | --- | --- |
| `L0 Infrastructure` | collect and retain raw evidence from product interaction loops | source of truth for raw events |
| `L1 Profile System / Fact Layer` | clean, normalize, aggregate, and project evidence into typed user-model views | projection pipeline + projection cache |
| `L2 AI System / Inference Layer` | derive bounded inferences, predictions, and higher-order patterns from fact-layer outputs | inference cache, not source of truth |
| `L3 Aurora / Control Layer` | maintain a small independent shadow state for control decisions and parameter steering | control state + parameter governance |
| `User Correction` | directly correct raw or calibration-facing records without going through inference/control layers | explicit correction lane |

### Source-of-truth rule

- `L0 Infrastructure` is the only long-lived source of truth for raw evidence.
- `L1` is a pipeline plus projection/cache layer, **not** a second source-of-truth store.
- `L2` is an inference cache, **not** a fact store.
- `L3` is a control-state layer, **not** a mirror database of the user.

### Why this split exists

This layering preserves two things at once:

1. user evidence stays auditable and traceable
2. Aurora can keep a small independent control-state summary instead of blindly trusting the same projection layer it consumes

That second point is the architectural reason for `L3`: without an independent control-state shadow, the system has no internal reference point for detecting drift between “what the profile pipeline says” and “what Aurora experiences as the current control problem.”

---

## 2. Current State vs Gaps

The current repository already contains a substantial portion of the user-model pipeline. The right interpretation is **not** “build a new subsystem,” but “name, discipline, and harden the one that already exists.”

### 2.1 `L0 Infrastructure`

**Current state**

- multiple evidence sources already exist across the product:
  - calendar events
  - error/mastery data
  - achievements
  - workflow/tool history
  - curiosity capsule activity
  - accountability signals
  - user corrections and intervention outcomes
- the repo already shows 7+ read paths being consumed by `UserInsightCompiler`

**Gap**

- the system still lacks explicit “information gap discovery” as a first-class concern
- event completeness is uneven across product surfaces

**Stage 6 boundary**

- Stage 6 does **not** redesign infrastructure storage
- Stage 6 may only add inventory, coverage checks, and signal-trigger wiring needed by downstream layers

### 2.2 `L1 Profile System / Fact Layer`

**Current state**

The following code already forms a real projection pipeline:

- [user_insight_compiler.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_insight_compiler.py)
- [user_insight_state.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/user_insight_state.py)
- [user_insight_calibration_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_insight_calibration_service.py)
- [user_insight_transparency_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_insight_transparency_service.py)

This means Sparkle already has:

- a typed canonical user-model snapshot
- projection of multiple source families into one state object
- calibration against user corrections and intervention outcomes
- a transparency surface with claims, predictions, and user controls

**Observed strengths**

- `M5`-like calibration is already materially implemented
- evidence freshness/confidence is already modeled
- the transparency surface already exposes user-facing controls rather than hiding the profile

**Gap**

- `M1` is still thin: stable preferences exist, but motivation patterns / anti-patterns / cognitive tendencies are undercompiled
- there is no strict `to_inline_snapshot()` with a hard token budget
- `format_user_context()` still normalizes from raw dict input first, which leaks value between compiled state and rendered prompt
- projection cache / version discipline is not yet hardened as a first-class layer concern

**Stage 6 boundary**

- Stage 6 should strengthen `L1`, not rebuild it
- Stage 6 may add:
  - `M1` source inventory and quality review
  - a bounded inline snapshot
  - tighter projection cache discipline
  - render-pipeline integration that prefers `UserInsightState`

### 2.3 `L2 AI System / Inference Layer`

**Current state**

There are already early inference-oriented services:

- [user_insight_analysis_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_insight_analysis_service.py)
- [insight_prediction_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/insight_prediction_service.py)

These provide:

- multi-span analysis
- contradiction-aware analysis
- bounded forward-looking predictions

**Observed strengths**

- inference logic is already separated from raw evidence collection
- prediction outputs are bounded and typed

**Gap**

- the repo does not yet treat `fact -> inference` as an explicit named layer
- there is no explicit judge/arbitration mechanism for competing inferences
- behavior-pattern extraction remains partial
- inference caching boundaries are implicit rather than governed

**Stage 6 boundary**

- Stage 6 may define the boundary and evaluation skeleton for `L2`
- Stage 6 should not yet try to extract a fully independent “AI System platform”
- Stage 7 is the better point to make `L2` a fully explicit standalone layer

### 2.4 `L3 Aurora / Control Layer`

**Current state**

- Aurora already consumes profile-derived signals through orchestration and prompt paths
- Aurora already acts as the adaptive control hub for routing, replanning, prompt policy, and shadow comparison

**Gap**

- Aurora does **not** yet maintain an explicit independent shadow state for control arbitration
- there is no explicit drift protocol between Aurora's internal control state and the profile projection
- parameter steering is not yet white-listed or audited as a first-class mechanism

**Stage 6 boundary**

- Stage 6 should introduce a **small shadow-state model**, not a duplicate user database
- the shadow state should cover:
  - friend/identity posture anchors
  - target routing stance
  - execution-readiness / control posture
  - control-side uncertainty markers

### 2.5 `User Correction`

**Current state**

- user-facing transparency controls already exist in `UserInsightTransparencyService`
- user corrections are already consumed by calibration logic

**Gap**

- the Flutter/UI consumption path for the transparency controls still needs confirmation and hardening
- the correction lane is semantically present, but not yet treated as a named architecture lane in governance docs

**Stage 6 boundary**

- Stage 6 should harden the correction UI and ingestion loop
- user correction remains the only path that may directly override profile-facing truth without passing through inference or Aurora control logic

---

## 3. Rule K · User Model Write-Path Discipline

All writes that touch the user-model system must fall into exactly one of these five lanes:

| Lane | Allowed writes | Forbidden writes |
| --- | --- | --- |
| `L0 Infrastructure` | raw evidence events | projection or inference results |
| `L1 Profile System` | projection cache | raw events in `L0`, inference data in `L2` |
| `L2 AI System` | inference cache | `L1` facts, `L0` raw events |
| `L3 Aurora` | white-listed `L1/L2` parameters with audit logging | any data field in `L0/L1/L2` |
| `User Correction` | raw/correction/calibration entries | inference or control-layer writes masquerading as user truth |

### Hard interpretation

- Aurora may write **parameters**, not **data**
- the AI system may write **inference cache**, not **facts**
- the profile system may write **projection cache**, not **raw evidence**
- user corrections bypass `L2` and `L3`; they are absorbed by `L1` on the next compilation cycle

### White-list rule for Aurora

Aurora parameter adjustments must be explicitly white-listed in the relevant dispatch plan.

Allowed adjustment families are limited to:

- numeric weights
- thresholds
- sampling cadence / windows
- response-policy selection
- budget allocation ratios

Aurora may **not** change:

- source selection
- algorithm logic
- evidence-chain structure
- user-correction records

In short: Aurora may turn **knobs**, not rewrite the **circuit**.

---

## 4. Aurora Shadow-State Model

Aurora's independent model should use the **shadow-model** approach, not a full duplicate profile system.

### Definition

Aurora shadow state is a compact control-state summary that lets Aurora compare:

- what the profile pipeline currently projects
- what Aurora believes is the right control posture for this user and moment

### Intended contents

- stable friend-posture anchors
- identity/aesthetic self-state relevant to interaction consistency
- target routing stance
- execution-readiness/control stance
- local uncertainty and conflict markers

### Explicit non-goal

Aurora shadow state is **not**:

- a second full `UserInsightState`
- a duplicate of raw evidence
- an alternate source of truth

### Drift protocol

When `L1` projection and `L3` shadow state materially diverge:

1. Aurora does **not** silently overwrite profile output
2. Aurora records the mismatch as a control-side drift signal
3. Aurora may adjust white-listed parameters
4. if the mismatch remains user-relevant, Aurora should prefer clarification with the user over silent correction

This is how the “friend” model becomes a systems rule rather than just a tone preference.

---

## 5. Control White-List Baseline

The following categories are appropriate candidates for Stage 6 white-listing:

- profile-module weighting
- inference confidence thresholds
- sampling frequency / time-window selection
- prompt budget allocation ratios
- interaction density / pacing strategy

The following are explicitly out of bounds:

- enabling/disabling a source-of-truth family
- changing inference algorithms
- editing fact-layer fields directly
- altering raw evidence or correction history

---

## 6. Stage 6 Workstream Boundaries

This document sets the architectural boundary for the Stage 6 workstreams now under discussion.

| Workstream | Boundary |
| --- | --- |
| `WS-M1a` | inventory `M1`-relevant sources, assess data quality, do not write production code |
| `WS-M1b` | improve `M1` projection using already-available sources; no new subsystem build |
| `WS-RP1` | fix render-pipeline leakage by making `format_user_context()` prefer `UserInsightState` and by introducing inline-cache/token discipline |
| `WS-V1` | harden user-facing transparency/correction UI consumption for the existing `L1` pipeline |
| `WS-E1` | introduce profile-aware evaluation boundaries for `L1/L2`, not a full new AI platform |
| `WS-VR1` | connect intervention effects back into calibration and verification without violating write-path discipline |

---

## 7. Stage 7 / Stage 8 Path

### Stage 7 direction

- make `L2 AI System` more explicit as an independent inference layer
- strengthen difference-vector and evaluation machinery
- improve judge/arbitration behavior for competing inferences

### Stage 8+ direction

- move from configuration-style module boundaries toward a stronger registered-module architecture if justified by accumulated complexity
- expand Aurora's shadow-state and control mechanisms only after parameter white-lists and audit patterns are proven stable

This means:

- Stage 6 hardens the existing pipeline
- Stage 7 extracts the inference layer more clearly
- Stage 8+ revisits deeper module-system abstraction

---

## 8. Constraint Mapping

This architecture is intended to remain compatible with the signed constraints already in force:

| Constraint | Mapping |
| --- | --- |
| anchor v3 “friend” relationship | enforced by the correction-first drift protocol and Aurora shadow-state posture |
| `P1-P5` discipline | preserved by keeping raw truth, projections, inference, and control writes separate |
| `Rule G/H/I/J` | still apply to all stage dispatch and closeout work |
| Stage 5 achievement one-way rule | preserved by keeping achievement writes outside Aurora authority |
| Stage 5 shadow-only discipline | preserved by keeping control-layer activation separate from prep hooks and caches |

---

## 9. Immediate Planning Consequence

The practical outcome of this document is:

- Sparkle does **not** need a new user-model subsystem from zero
- Sparkle does need to formalize the layered boundaries around the subsystem it already has
- Stage 6 should prioritize the last-mile leakage and governance issues before expanding architectural breadth again
