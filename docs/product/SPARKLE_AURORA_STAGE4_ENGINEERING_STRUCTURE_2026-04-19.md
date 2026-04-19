# Sparkle Aurora Stage 4 Engineering Structure (2026-04-19)

> **Status**: Draft v2
> **Depends on**:
> - `SPARKLE_AURORA_STAGE4_VISION_ALIGNMENT_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE3_CHECKPOINT_2026-04-19.md`
> - `SPARKLE_AURORA_WSM_CUTOVER_RUNBOOK_2026-04-19.md`
> **Scope**: Engineering structure only. No task cards, no agent dispatch, no schema amendment yet.

### Revision History

| Version | Changes | Source |
| --- | --- | --- |
| v1 | First engineering structure translation from Stage 4 vision alignment | Codex |
| v2 | Incorporate Claude must-fix items (P5 budgets, upgrade criteria, WS-D injection list, WS-M Phase 1 freeze) + GLM structure fixes (WS-A/WS-B ownership split, Wave 1a/1b split, DORMANT handling, routing_mode flagging, time anchors) | Codex |

---

## 0. Why This Document Exists

Stage 4 vision has now been aligned at the strategy layer:

- Aurora is one external control core with three internal time tiers
- conversation handling is split by complexity, not by user-facing mode choice
- TaskGuidance becomes the closed-loop delivery artifact for task cards
- task assistant becomes a lighter "dormant" Aurora preset instead of a second full core

This document translates those strategic decisions into an engineering structure:

- which subsystems exist
- where they land in the codebase
- what order they should be built in
- what is explicitly deferred
- which gates must pass before deeper Aurora takeover work resumes

It is intentionally **one step before dispatch**. The goal is to prevent Stage 4 from drifting back into "just keep taking over more trigger points."

---

## 1. Stage 4 Engineering Decisions Already Locked

These are no longer open questions.

### 1.1 Aurora Time-Tier Model

Aurora remains one external control surface, with three internal execution tiers:

- `inline`
- `nearline`
- `long_horizon`

These tiers are budget- and latency-defined, not user-visible mode switches.

### 1.2 Complexity Routing Model

Stage 4 does **not** introduce a standalone `ConversationComplexityRouter` service.

Instead:

- `BackboneRoutingDecision` gains `routing_mode`
- `routing_mode` is computed inside `decide_backbone_route()`
- `routing_mode` selects one of:
  - `direct`
  - `workflow`
  - `task_assistant`

### 1.3 TaskGuidance Status

`TaskGuidance` is approved as a **Stage 4 candidate primitive**, but it is **not yet a Gate 0 primitive**.

Engineering implication:

- Stage 4 may implement `TaskGuidance` as a new app-level persisted object
- this object lives outside the frozen Gate 0 schema set
- if Stage 4 proves it is stable and structurally necessary, it can later be proposed through a controlled schema amendment

### 1.4 Nearline Queue Choice

Nearline execution will **reuse Celery**.

Engineering implication:

- no new queueing stack
- no new service split
- no second async orchestration substrate

Celery responsibilities in Stage 4:

- nearline Aurora optimization tasks
- TaskGuidance generation tasks
- deferred claim/probe/guide enrichment tasks
- long-horizon scheduled aggregation tasks

---

## 2. Target Engineering Shape

Stage 4 is not one workstream. It is a coordinated reshaping of the current Stage 3 repo-side architecture.

### 2.1 High-Level Target

```text
user request
  -> inline Aurora decision (cheap, bounded)
  -> routing_mode decides direct / workflow / task_assistant
  -> immediate response path continues without waiting for full Aurora reflection

after response / idle / explicit submit
  -> nearline Aurora job runs in Celery
  -> writes TDR / InsightClaim / ProbeOutcome / TaskGuidance
  -> influences next-turn quality instead of blocking current turn

scheduled / batch / growth cycle
  -> long-horizon aggregation
  -> updates FocusContract evolution / IdentityEvidence / WindowState drift
```

### 2.2 Code-Level Placement

Proposed landing zones:

- `backend/app/aurora/`
  - inline decision functions remain here
  - tier dispatch helpers and Celery task entrypoints land here
- `backend/app/task_guidance/`
  - candidate `TaskGuidance` schema, persistence, generation, adapters
- `backend/app/task_assistant/`
  - dormant-mode injection assembly and outcome capture
- `backend/app/orchestration/`
  - only minimal seams for `routing_mode` consumption and workflow escalation
- `mobile/lib/features/tasks/` and related UI surfaces
  - guide rendering, audience toggle, workflow entry affordances

### 2.3 Data Ownership Principle

Stage 4 keeps the same governance line as Stage 3:

- frozen Gate 0 primitives remain untouched unless a formal amendment is approved
- new Stage 4 objects are introduced as **adjacent app-level objects**, not stealth edits to the Gate 0 core
- cross-tier communication continues through:
  - `prior_outputs`
  - persisted primitives and approved Stage 4 sidecar objects such as `TaskGuidance`

---

## 3. Workstream Structure

Stage 4 engineering should be organized around **six workstreams**.

## 3.1 WS-A: Aurora Async Core

**Purpose**

Turn Stage 3's synchronous Aurora surface into the first true three-tier control system.

**Owns**

- inline / nearline / long-horizon dispatch boundaries
- Celery task entrypoints for Aurora nearline work
- tier tagging
- tier miss / tier failure semantics
- Wave 3 budget enforcement hooks

**Likely write zones**

- `backend/app/aurora/engine.py`
- `backend/app/aurora/tasks.py` or equivalent
- `backend/app/aurora/context.py`
- `backend/app/aurora/observability/`

**Key outputs**

- inline path stays under budget
- nearline jobs consume `prior_outputs` and `SignalSnapshot` references
- long-horizon jobs only consume persisted state
- tier miss semantics are explicit: downstream sees `None` / absence without alert
- tier failure semantics are explicit: failure emits fallback telemetry and alerting without breaking downstream flow

**Non-goal**

- this workstream does not own product UX
- this workstream does not introduce new trigger-point takeovers yet
- this workstream does not own `decide_backbone_route()` internals or `routing_mode` logic

## 3.2 WS-B: Routing-Mode Split and Workflow Escalation

**Purpose**

Make `routing_mode` a real orchestration boundary rather than a field that exists only on paper.

**Owns**

- `routing_mode` productionization
- conversation escalation from `direct` to `workflow`
- task-assistant entry routing
- conversation mid-flight upgrade triggers
- the three approved upgrade criteria only:
  - explicit user request for planning / task decomposition / plan-making
  - 2+ consecutive turns on the same structural topic
  - frustration / blockage signal detection

**Likely write zones**

- `backend/app/orchestration/`
- `backend/app/aurora/decision_fns/`
- `backend/tests/aurora/`
- `backend/tests/unit/orchestrator/`

**Key outputs**

- simple questions can stay on a short path
- planning-heavy questions enter workflow automatically
- wrong initial routing can escalate without forcing the user to restart

**Non-goal**

- this is not yet pre-tool-selection takeover
- this is not yet pre-response-formatting takeover
- this workstream may not invent new upgrade criteria without first updating the Stage 4 vision alignment consensus

## 3.3 WS-C: TaskGuidance System

**Purpose**

Replace "task guide as generic filler text" with a structured, Aurora-informed closed-loop artifact.

**Owns**

- `TaskGuidance` candidate schema implementation
- persistence and retrieval
- human-guide default generation
- AI-guide on-demand generation
- attachment to task cards / task execution surfaces

**Likely write zones**

- `backend/app/task_guidance/`
- `backend/app/tasks/` or existing task-card service seam
- `mobile/lib/features/tasks/`
- `backend/tests/aurora/`

**Minimum schema (approved for Stage 4 engineering use)**

- `id`
- `task_card_ref`
- `audience`
- `content`
- `generated_by`
- `policy_version`

**Key outputs**

- every task card can have a usable human-facing guide
- AI-facing guide is generated lazily, not precomputed blindly
- guide generation is grounded in actual workflow/task context
- `TaskGuidance` references existing Aurora/task objects by UUID rather than embedding whole primitive payloads

**Non-goal**

- do not amend Gate 0 yet
- do not generate external-AI handoff prompts as the primary experience

## 3.4 WS-D: Task Assistant Dormant Mode

**Purpose**

Create the lighter assistant preset that preserves closed-loop value without paying full Aurora cost on every turn.

**Owns**

- one-shot session-start injection
- the 5 approved initial injection inputs:
  - `FocusContract` summary
  - current `TaskGuidance` AI version, or human-summary fallback
  - latest `TransitionDecisionRecord` `UXIntent + AuroraPresenceLevel`, or cold-start fallback
  - projection-allowed active `InsightClaim`
  - recent relevant `ProbeOutcome`
- strong-signal refresh rules
- outcome capture for next-turn optimization
- dormant-mode sidecar expression of candidate `DORMANT` presence semantics

**Likely write zones**

- `backend/app/task_assistant/`
- `backend/app/aurora/`
- `mobile/lib/features/tasks/assistant/`
- task-assistant specific tests

**Key outputs**

- task assistant is better than plain single-core chat
- Aurora does not continuously inject context mid-session
- nearline can still learn from session outcome and improve the next round
- cold-start sessions fall back to `UXIntent.ROUTINE + AuroraPresenceLevel.AMBIENT`

**Non-goal**

- no mid-session Aurora steering except explicit strong-signal exceptions
- no second full dual-core system inside task assistant
- do not directly modify the frozen Gate 0 `AuroraPresenceLevel` enum; `DORMANT` remains a Stage 4 candidate expressed via sidecar/state-layer semantics until a controlled schema amendment is approved

## 3.5 WS-E: Closed-Loop UX and Product Surface

**Purpose**

Make the new split visible and usable without exposing internal complexity to the user.

**Owns**

- workflow entry affordances
- task guide audience switching
- direct vs workflow continuity
- explicit handling of capability-ceiling referral UX

**Likely write zones**

- `mobile/lib/features/chat/`
- `mobile/lib/features/tasks/`
- `mobile/lib/features/user/`
- backend response adapters only where necessary

**Key outputs**

- user stays inside Sparkle for normal growth flows
- "AI version" vs "human version" of guides becomes a product surface
- external referral, where allowed, is clearly framed as an exception

**Non-goal**

- no large-scale redesign unrelated to the four pillars
- no new visible "mode picker"
- no new WebSocket message type or response delta metadata field without explicit WS-A + product review

## 3.6 WS-F: Budgeting, Evaluation, and Activation Prep

**Purpose**

Turn Stage 4 from "interesting architecture" into something we can safely validate and eventually activate.

**Owns**

- tier-level latency and cost dashboards
- direct/workflow/task-assistant path evaluation
- TaskGuidance quality eval
- production-replay shadow expansion plan for future cohort activation
- P1 enforcement via lint / tests / CI (no cross-tier shared mutable state, no shared ORM session across tiers)

**Likely write zones**

- `backend/tests/aurora/`
- `docs/product/`
- observability config / dashboards
- evaluation harnesses

**Key outputs**

- inline / nearline budgets can be measured
- split-routing behavior is benchmarked
- Stage 4 does not accidentally regress Stage 3 cutover safety

**Non-goal**

- this workstream does not itself flip production cohorts
- this workstream does not reopen Stage 3 cutover semantics

---

## 4. Wave Plan

Stage 4 should be executed in **three engineering waves**, followed by an activation-prep gate.

### Wave 1a: Async Substrate and Structural Seams

**Estimated duration**

- `5-7` working days

**Goal**

Create the minimum async and persistence seams required so Stage 4 work can land without violating Stage 3 stability.

**Primary workstreams**

- WS-A
- WS-C (schema/persistence skeleton only)

**Must exit with**

- Celery nearline lane defined
- `TaskGuidance` candidate object scaffolded
- tier miss vs tier failure semantics are explicit
- inline benchmark harness exists (`>=20` representative cases)
- no change to current active cohort behavior

### Wave 1b: Routing Split Seams

**Estimated duration**

- `4-6` working days

**Goal**

Turn `routing_mode` into a real seam without yet implementing full escalation behavior.

**Primary workstreams**

- WS-B

**Must exit with**

- `routing_mode` is consumed cleanly by orchestration seams
- all routing-mode behavior changes are behind feature flags
- default behavior remains equivalent to current `direct` path when flags are off
- no change to current active cohort behavior

### Wave 2: Closed-Loop Product Paths

**Estimated duration**

- `7-10` working days

**Goal**

Make the direct/workflow/task-assistant split and TaskGuidance flows real user-facing behavior behind flags.

**Primary workstreams**

- WS-C
- WS-D
- WS-E
- WS-B (escalation completion)

**Must exit with**

- direct path and workflow path both function
- human guide default path works
- AI guide on-demand path works
- task assistant dormant mode can start, run, and feed next-turn optimization
- conversation mid-flight escalation works using only the three approved trigger criteria

### Wave 3: Budgets, Eval, and Stabilization

**Estimated duration**

- `5-7` working days

**Goal**

Verify that Stage 4 is not only architecturally correct, but also budget-safe and product-safe.

**Primary workstreams**

- WS-A
- WS-F
- targeted fixes from WS-B/C/D/E

**Must exit with**

- inline budget is met
- nearline budget is measured and stable
- split-routing eval corpus exists
- TaskGuidance quality baseline exists
- no regression to Stage 3 Phase 1 cutover safety

### Activation-Prep Gate

This is **not** a user-cohort activation yet.

It is the gate that answers:

- is Stage 4 ready for its own controlled migration plan?
- can we now design the next real cutover surface?

Only after this gate passes should we reopen:

- pre-tool-selection takeover
- pre-response-formatting takeover
- any Stage 4 user-cohort rollout plan

Hard preconditions:

- Gate S4-3 has passed
- `>=100` production-replay cases cover all three `routing_mode` values: `direct`, `workflow`, `task_assistant`
- Stage 3 WS-M Phase 1 cutover remains stable with no P1 regression
- a Stage 4 cohort rollout runbook v1 exists, even if not yet approved for execution

Estimated total for Stage 4 engineering structure represented here:

- `21-30` working days before any real-user activation decision

---

## 5. Engineering Gates

## Gate S4-0: Structure Locked

Required before dispatch:

- Stage 4 vision alignment doc signed
- Stage 4 engineering structure doc signed
- Gap1 and Gap3 resolved
- no contradiction with Stage 3 cutover runbook

## Gate S4-1: Async Substrate Ready

Required before Wave 2:

- Celery nearline path exists and is testable
- inline path still stays within Stage 4 budget target
- `routing_mode` is consumed without breaking current Stage 3 routing
- all `routing_mode` behavior changes are protected by feature flags and default to current `direct` behavior when flags are off

## Gate S4-2: Closed-Loop Paths Function

Required before Wave 3:

- direct path works
- workflow escalation works
- task assistant dormant mode works
- human guide default + AI guide on-demand both work behind flags

## Gate S4-3: Budget and Eval Stable

Required before any future activation planning:

- inline latency budget holds on realistic test corpus:
  - P95 `<= 100ms`
  - per-request Aurora cost contribution `<= 0.1x` LLM baseline
- nearline latency budget holds on realistic session corpus:
  - P95 `<= 30s`
  - P99 `<= 60s`
  - per-session Aurora cost contribution `<= 1x` LLM baseline
- long-horizon batch cost remains within initial anchor:
  - `<= 0.5x` LLM baseline / active user / day
  - any calibration against real volume must be written back to the Stage 4 vision alignment baseline
- guide generation quality is not obviously degenerate
- Stage 3 Phase 1 cutover remains stable

---

## 6. Explicit Deferrals

To prevent Stage 4 from collapsing back into trigger-point expansion, the following are **explicitly deferred** out of this engineering structure:

1. full `pre-tool-selection` takeover
2. full `pre-response-formatting` takeover
3. any new global cohort rollout
4. any "send this prompt to another AI app" primary flow
5. any new microservice split for Aurora tiers
6. any Gate 0 schema amendment before Stage 4 engineering evidence exists
7. any expansion of WS-M Phase 1 beyond the current allowlist-level posture before Gate S4-3 passes and the `>=100` case production-replay corpus gate is satisfied

These items may be revisited later, but they are **not** part of Stage 4 v1 engineering structure.

---

## 7. Provisional Ownership Boundaries

These are not task cards yet. They are pre-dispatch ownership seams to reduce future conflict.

| Workstream | Primary write zones | Shared-hotspot policy |
| --- | --- | --- |
| WS-A | `backend/app/aurora/engine.py`, `backend/app/aurora/tasks.py`, `backend/app/aurora/context.py`, `backend/app/aurora/observability/` | may expose seams, but does not own orchestrator behavior or `decision_fns/decide_backbone_route()` |
| WS-B | `backend/app/orchestration/`, `backend/app/aurora/decision_fns/`, selected tests | owns routing-mode computation and routing-mode consumption seam |
| WS-C | `backend/app/task_guidance/`, task-card adapters | does not amend frozen Aurora schemas |
| WS-D | `backend/app/task_assistant/` | consumes outputs, does not redefine Aurora core |
| WS-E | `mobile/lib/features/chat/`, `mobile/lib/features/tasks/` (excluding `assistant/`) | UI-only unless backend adapter seam is explicitly assigned |
| WS-F | `backend/tests/aurora/`, docs, observability config | may not change core behavior except through eval-driven fixes |

---

## 8. Recommended Immediate Next Step

The next artifact should **not** be a dispatch plan yet.

The next artifact should be:

> **Stage 4 Dispatch Plan v1**

That document should:

- convert WS-A through WS-F into concrete task cards
- define interrupt semantics
- define file ownership at file-level granularity
- decide whether Wave 1 is 3 agents or 4 agents
- define the first validation corpus for split-routing and TaskGuidance quality

Only after that document is signed should Stage 4 dispatch begin.

---

## 9. Final Position

Stage 4 is **not** "continue the Stage 3 takeover one trigger point deeper."

Stage 4 engineering is:

- make Aurora asynchronous
- make routing granular
- make TaskGuidance real
- make task assistant lighter but still Aurora-informed
- measure budgets before dreaming about broader activation

If engineering starts from any other framing, the project will drift back into expensive, slower, less product-coherent Aurora expansion.
