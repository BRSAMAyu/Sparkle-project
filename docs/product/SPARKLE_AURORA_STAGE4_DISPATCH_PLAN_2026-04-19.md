# SPARKLE Aurora Stage 4 Dispatch Plan (2026-04-19)

> **Status**: Draft v3
> **Depends on**:
> - `SPARKLE_AURORA_STAGE4_VISION_ALIGNMENT_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE4_ENGINEERING_STRUCTURE_2026-04-19.md`
> - `SPARKLE_AURORA_WSM_CUTOVER_RUNBOOK_2026-04-19.md`
> **Scope**: Stage 4 execution plan. Defines workstream task cards, interrupt semantics, file ownership, and validation gates.

### Revision History

| Version | Changes | Source |
| --- | --- | --- |
| v1 | First Stage 4 dispatch plan with 6 rules, 4 corpora, file ownership, and 11 agents across 4 waves | Codex |
| v2 | Incorporate Claude + GLM dispatch review: keep Wave 1a at 3 agents via narrower Agent B, add Agent K hard boundaries, clarify Corpus V1 plumbing/content ownership, harden Gate S4-4, make Agent E scope explicit, add mobile flag mechanism, define interrupt semantics, and record 5-gate split from engineering structure into dispatch control gates | Codex |
| v3 | Add Rule G after the retroactive audit of commit `cd2f844b`, explicitly banning cross-workstream batch commits without dispatcher approval and making revert the default consequence | Codex |

---

## 0. Dispatch Rules

### Rule A: Vision Authority

Stage 4 work executes against the signed vision alignment and engineering structure documents.

No worker may:

- reopen Q1-Q5
- reinterpret Gap1 / Gap3
- reframe Stage 4 as "continue trigger-point takeover"

Any proposal that changes Stage 4 vision must return as a doc amendment, not as a code change.

### Rule B: File Ownership

No two workers may own the same hotspot file.

If a hotspot must be shared:

- one workstream owns the file
- other workstreams may only consume imports or request seam extraction through that owner

### Rule C: Frozen Schema Discipline

Gate 0 frozen Aurora schemas remain frozen.

Stage 4 may add:

- new sidecar objects
- task guidance persistence
- task assistant state helpers

But may not stealth-edit:

- Aurora primitives
- frozen enums
- Gate 0 ownership semantics

### Rule D: Interrupt Semantics

Every task card must declare one of:

- `deployable`
- `behind_flag`
- `atomic`

Definitions:

- `deployable`: may be merged incomplete if it remains correct and does not destabilize downstream users
- `behind_flag`: code may land incomplete as long as it is inert behind a safe default flag
- `atomic`: partial landings are not acceptable; the task must be completed as one coherent unit

No task card without interrupt semantics may be dispatched.

### Rule E: Default-Safe Flags

All Stage 4 behavior changes must default to existing stable behavior.

In particular:

- `routing_mode` path changes default to current `direct`-equivalent behavior when flags are off
- TaskGuidance generation does not replace existing task flows until explicitly enabled
- task assistant dormant mode does not intercept current task chat flows by default
- mobile-side flagging uses the existing `AppFeatureFlags` pattern in `mobile/lib/core/constants/app_constants.dart` unless a later signed amendment declares a different mechanism

### Rule F: WS-M Phase 1 Freeze

During Stage 4 engineering:

- WS-M Phase 1 remains frozen at current allowlist posture
- no percentage rollout expansion is allowed
- no real-user activation widening is allowed

Until:

- Gate S4-3 passes
- `>=100` production-replay corpus gate passes

### Rule G: Single-WS-per-Agent Commit Discipline

A single agent commit must not touch more than one workstream's primary write zone unless the dispatcher explicitly authorizes a cross-WS batch.

If this rule is violated:

- revert is the default outcome
- retroactive accept is an exception path
- the exception path requires independent review and per-workstream justification

---

## 1. Stage 4 Workstreams

This dispatch plan keeps the six workstreams defined in the engineering structure:

- `WS-A` Aurora Async Core
- `WS-B` Routing-Mode Split and Workflow Escalation
- `WS-C` TaskGuidance System
- `WS-D` Task Assistant Dormant Mode
- `WS-E` Closed-Loop UX and Product Surface
- `WS-F` Budgeting, Evaluation, and Activation Prep

---

## 2. Wave Overview

| Wave | Duration | Parallel Agents | Primary Scope |
| --- | --- | --- | --- |
| `Wave 1a` | `5-7` working days | `3` | async substrate + guidance skeleton |
| `Wave 1b` | `4-6` working days | `1` | routing-mode seam |
| `Wave 2` | `7-10` working days | `4` | task guidance UX + task assistant + workflow escalation |
| `Wave 3` | `5-7` working days | `3` | budgets, eval, stabilization, activation prep |

**Total estimate**

- `21-30` working days before any activation decision

### Why Wave 1 Uses 3 Agents

Wave 1 deliberately uses `3` agents, not `4`.

Reason:

- `WS-A` and `WS-B` now have carefully split hotspots, but `WS-B` is still logically cleaner as its own narrow seam wave (`1b`) instead of running concurrently with all substrate work
- `WS-C` skeleton can proceed in parallel with `WS-A`
- a separate Wave 1 validation agent would create avoidable overlap with `WS-A` and `WS-F`

So:

- `Wave 1a`: Agents `A / B / C`
- `Wave 1b`: Agent `D`

---

## 3. Validation Corpus Definitions

These corpora are the minimum shared evaluation surfaces for Stage 4.

### Corpus V1 — Inline Benchmark Harness

Used in `Wave 1a`.

- size: `>=20` representative cases
- purpose: confirm inline latency budget and routing seam stability
- coverage:
  - casual direct question
  - workflow-eligible planning request
  - task-assistant-eligible request
  - escalation-trigger cases
  - no-op / fallback / miss cases

Ownership split:

- Agent A owns the harness infrastructure:
  - runner
  - timers
  - tier-tagged result capture
  - CI integration
- Agent C owns the corpus content:
  - `>=20` fixtures
  - expected assertions
  - category distribution coverage

### Corpus V2 — Routing Split Evaluation

Used in `Wave 2`.

- size: `>=30` cases
- distribution:
  - `10` direct
  - `10` workflow
  - `10` task_assistant
- purpose:
  - verify `routing_mode` assignment
  - verify mid-flight upgrade behavior
  - verify flags-off behavior remains stable

### Corpus V3 — TaskGuidance Quality Set

Used in `Wave 2` and `Wave 3`.

- size: `>=15` tasks
- distribution across task types:
  - learning
  - training
  - error_fix
  - reflection
  - planning
- purpose:
  - verify human-guide usefulness
  - verify AI-guide density/structure
  - detect filler / empty / generic guidance regressions

### Corpus V4 — Activation Prep Replay Set

Used only in `Wave 3` / activation-prep.

- size: `>=100` production-replay cases
- distribution:
  - `direct >= 30`
  - `workflow >= 30`
  - `task_assistant >= 30`
  - boundary / mixed / failure cases `>= 10`
- purpose:
  - satisfy Stage 3 / Stage 4 activation-prep gate
  - validate no regression against current Phase 1 cutover assumptions

---

## 4. File Ownership Matrix

This section resolves the two soft problems explicitly:

- `SOFT-1`: mobile task-area overlap
- `SOFT-2`: backend task-card seam ambiguity

### 4.1 Backend Hotspots

| Path | Owner | Notes |
| --- | --- | --- |
| `backend/app/aurora/engine.py` | `WS-A` | async dispatch boundary only |
| `backend/app/aurora/tasks.py` | `WS-A` | Celery nearline / long-horizon entrypoints |
| `backend/app/aurora/context.py` | `WS-A` | tier context / miss-failure semantics |
| `backend/app/aurora/observability/` | `WS-A` / `WS-F` | `WS-A` writes instrumentation hooks, `WS-F` owns eval/dashboard files |
| `backend/app/aurora/decision_fns/` | `WS-B` | owns `routing_mode` computation and upgrade criteria |
| `backend/app/orchestration/` selected routing seam files | `WS-B` | routing-mode consumption and workflow escalation |
| `backend/app/services/task_guide_service.py` | `WS-C` | primary backend seam for guide generation |
| `backend/app/services/task_service.py` | `WS-C` | task-card attachment / guide persistence seam |
| `backend/app/api/v1/tasks.py` | `WS-C` | guide endpoints / task-guide request flow |
| `backend/app/task_guidance/` | `WS-C` | new Stage 4 sidecar module |
| `backend/app/task_assistant/` | `WS-D` | new task-assistant dormant-mode module |
| `backend/tests/aurora/` | `WS-F` by default | behavior-specific tests may be added by owner WS, but eval corpus ownership is WS-F |

### 4.2 Mobile Hotspots

| Path | Owner | Notes |
| --- | --- | --- |
| `mobile/lib/features/task/presentation/screens/task_execution_screen.dart` | `WS-D` | hotspot file; task assistant owner controls edits |
| `mobile/lib/features/task/presentation/widgets/task_chat_panel.dart` | `WS-D` | task assistant UI |
| `mobile/lib/features/task/presentation/providers/task_chat_provider.dart` | `WS-D` | dormant-mode task assistant state |
| `mobile/lib/features/task/presentation/screens/task_detail_screen.dart` | `WS-C` | guide rendering / guide audience UI |
| `mobile/lib/features/task/presentation/providers/task_provider.dart` | `WS-C` | guide fetch / generate / persistence wiring |
| `mobile/lib/features/task/data/repositories/task_repository.dart` | `WS-C` | backend guide endpoint integration |
| `mobile/lib/features/plan/presentation/screens/plan_create_screen.dart` | `WS-C` | plan-created task guide defaults |
| `mobile/lib/features/plan/data/services/plan_guide_generator.dart` | `WS-C` | existing plan-guide seam |
| `mobile/lib/features/chat/` | `WS-E` | workflow entry affordances / direct-vs-workflow UX |
| `mobile/lib/features/task/presentation/widgets/` (excluding `task_chat_panel.dart`) | `WS-C` then `WS-E` by file | new guidance widgets under WS-C; workflow-entry UX widgets under WS-E |
| `mobile/lib/features/task/presentation/screens/task_list_screen.dart` | `WS-E` | workflow entry affordances only, no assistant logic |

### 4.3 Shared-Hotspot Policy

The following hotspot rules are mandatory:

1. `task_execution_screen.dart` is owned by `WS-D`
   - if `WS-C` needs new guide UI there, it must add new importable guide widgets in a non-hotspot file
   - `WS-D` performs the final screen integration
2. `task_service.py` and `task_guide_service.py` are owned by `WS-C`
   - `WS-D` may consume their outputs but not edit their guide-generation logic
3. `decision_fns/decide_backbone_route()` is owned by `WS-B`
   - `WS-A` may not modify the function internals

---

## 5. Task Cards

## 5.1 Wave 1a — Agents A / B / C

### Agent A — WS-A.1 Async Substrate

**Goal**

Build the minimum async substrate for Stage 4 without changing user-visible routing behavior.

**Write scope**

- `backend/app/aurora/engine.py`
- `backend/app/aurora/tasks.py`
- `backend/app/aurora/context.py`
- selected `backend/app/aurora/observability/` files

**Tasks**

1. Add tier tagging for `inline / nearline / long_horizon`
2. Define Celery task entrypoints for nearline Aurora jobs
3. Define explicit `tier miss` vs `tier failure` semantics
4. Add inline benchmark harness plumbing for Corpus V1
5. Ensure all behavior is `behind_flag`

**Interrupt**

- `behind_flag`

**Acceptance**

- Celery nearline path exists and is testable
- inline benchmark harness exists with `>=20` representative cases
- no current Stage 3 routing path changes when flags are off

### Agent B — WS-C.1 TaskGuidance Skeleton

**Goal**

Create the backend TaskGuidance skeleton plus only the minimum mobile wiring needed to keep Wave 1a at three agents.

**Write scope**

- `backend/app/task_guidance/`
- `backend/app/services/task_guide_service.py`
- `backend/app/services/task_service.py`
- `backend/app/api/v1/tasks.py`
- `mobile/lib/features/task/data/repositories/task_repository.dart`
- `mobile/lib/features/task/presentation/providers/task_provider.dart`

**Tasks**

1. Add `TaskGuidance` sidecar schema and persistence skeleton
2. Connect existing guide generation seam to the new sidecar object model
3. Add mobile repository/provider wiring for guide fetch and create flows
4. Keep full mobile rendering and plan-surface integration deferred to Wave 2
5. Ensure all references are UUID-based, not embedded primitive payloads

**Interrupt**

- `behind_flag`

**Acceptance**

- `TaskGuidance` sidecar object can be created and retrieved
- repository/provider seams can consume the new guide object model without UI integration regressions
- no Gate 0 schema edits

### Agent C — WS-F.1 Benchmark and Guardrails Prep

**Goal**

Prepare Stage 4 evaluation and CI guardrails early so later waves do not drift.

**Write scope**

- `backend/tests/aurora/`
- observability config owned by WS-F
- Stage 4 evaluation docs if needed

**Tasks**

1. Materialize Corpus V1 content and hook it into Agent A's benchmark harness runner
2. Add P1 guardrail checks for cross-tier communication discipline in report-only mode first
3. Add placeholders for Corpus V2 / V3 / V4
4. Wire dashboards/tests to understand tier-tagged events

**Interrupt**

- `deployable`

**Acceptance**

- Corpus V1 runnable in CI
- P1 enforcement exists in lint/test/CI form, starting in report-only mode until WS-A.1 seam work lands
- Stage 4 eval placeholders are ready before Wave 1b

## 5.2 Wave 1b — Agent D

### Agent D — WS-B.1 Routing-Mode Seam

**Goal**

Make `routing_mode` real without yet implementing full conversation escalation.

**Write scope**

- `backend/app/aurora/decision_fns/`
- `backend/app/orchestration/`
- selected routing tests

**Tasks**

1. Add `routing_mode` computation to `decide_backbone_route()`
2. Support the three modes:
   - `direct`
   - `workflow`
   - `task_assistant`
3. Keep all path changes behind feature flags
4. Preserve current `direct` behavior when flags are off
5. Do **not** implement full escalation yet

**Interrupt**

- `behind_flag`

**Acceptance**

- `routing_mode` is computed and consumed cleanly
- flags-off behavior is stable
- no pre-tool-selection or pre-response-formatting takeover begins

## 5.3 Wave 2 — Agents E / F / G / H

### Agent E — WS-C.2 TaskGuidance Productization

**Goal**

Finish dual-audience guide generation and product-ready guide lifecycle.

**Write scope**

- `mobile/lib/features/task/presentation/screens/task_detail_screen.dart`
- `mobile/lib/features/plan/presentation/screens/plan_create_screen.dart`
- `mobile/lib/features/plan/data/services/plan_guide_generator.dart`
- `mobile/lib/features/task/presentation/widgets/guidance/` (new)
- any additional non-hotspot guide-rendering files explicitly created under `mobile/lib/features/task/presentation/`

**Tasks**

1. Human-guide default generation path
2. AI-guide on-demand generation path
3. Guide version retrieval and refresh rules
4. Guide quality hooks for Corpus V3
5. Mobile render integration for human/AI guide surfaces deferred out of Wave 1a

**Interrupt**

- `behind_flag`

### Agent F — WS-D Task Assistant Dormant Mode

**Goal**

Implement single-shot Aurora injection and next-turn optimization for task assistant.

**Write scope**

- `backend/app/task_assistant/`
- `mobile/lib/features/task/presentation/screens/task_execution_screen.dart`
- `mobile/lib/features/task/presentation/widgets/task_chat_panel.dart`
- `mobile/lib/features/task/presentation/providers/task_chat_provider.dart`

**Tasks**

1. Implement 5-item initial injection set
2. Implement cold-start fallback:
   - `UXIntent.ROUTINE`
   - `AuroraPresenceLevel.AMBIENT`
3. Implement strong-signal refresh rules only
4. Capture assistant outcome for nearline next-turn optimization
5. Keep DORMANT as sidecar/candidate semantics, not frozen enum mutation

**Interrupt**

- `behind_flag`

### Agent G — WS-E Closed-Loop UX

**Goal**

Make the direct/workflow/task-assistant split legible and usable without exposing internal mode complexity.

**Write scope**

- `mobile/lib/features/chat/`
- `mobile/lib/features/task/presentation/screens/task_list_screen.dart`
- selected task/plan UX files outside WS-D hotspot ownership

**Tasks**

1. Add workflow-entry affordances
2. Add direct-vs-workflow continuity UX
3. Add AI-guide vs human-guide switching affordances where appropriate
4. Add capability-ceiling referral UX treatment
5. If capability-ceiling UX requires backend adapter seam, raise a coordination request before implementation; the seam assignment must be explicitly granted and may not be invented ad hoc in mobile code

**Interrupt**

- `behind_flag`

### Agent H — WS-B.2 Escalation Completion

**Goal**

Implement conversation mid-flight escalation using the three approved trigger criteria only.

**Write scope**

- `backend/app/orchestration/`
- `backend/app/aurora/decision_fns/`
- related tests

**Tasks**

1. Implement mid-flight `direct -> workflow` escalation
2. Use only approved triggers:
   - explicit planning request
   - `2+` structural-topic turns
   - frustration/blockage signal
3. Add Corpus V2 validation

**Interrupt**

- `behind_flag`

## 5.4 Wave 3 — Agents I / J / K

### Agent I — WS-A.2 Budget Enforcement

**Goal**

Turn async substrate into budget-observant production-ready infrastructure.

**Write scope**

- `backend/app/aurora/`
- budget / observability seams

**Tasks**

1. Enforce inline P95 target
2. Enforce nearline P95/P99 targets
3. Implement fallback/alert treatment for tier failures
4. Ensure calibration changes route back to signed vision baseline

**Interrupt**

- `behind_flag`

### Agent J — WS-F Evaluation and Activation Prep

**Goal**

Produce the evidence needed for any later activation decision.

**Write scope**

- `backend/tests/aurora/`
- evaluation docs
- activation-prep docs

**Tasks**

1. Materialize Corpus V2 and V3
2. Expand toward Corpus V4 (`>=100` production-replay cases)
3. Draft Stage 4 activation-prep runbook v1
4. Verify no regression to Stage 3 Phase 1 stability

**Interrupt**

- `deployable`

### Agent K — Cross-WS Stabilization

**Goal**

Absorb fix-forward work from Waves 1 and 2 without reopening structural debate.

**Write scope**

- whichever owned files are explicitly reassigned for stabilization

**Tasks**

1. Fix issues found by Corpus V2/V3/V4
2. Resolve non-structural regressions
3. Prepare Gate S4-3 evidence bundle
4. Every code change must reference a concrete failing corpus case id

**Interrupt**

- `atomic`

**Hard boundaries**

- may not modify frozen schemas
- may not add or change escalation criteria
- may not change gate conditions
- may not self-select files to edit; each reassigned file must be explicitly approved by the dispatcher
- may not touch Stage 4 seam anchor files unless the dispatcher explicitly reassigns them:
  - `backend/app/aurora/engine.py`
  - `backend/app/aurora/tasks.py`
  - `backend/app/aurora/decision_fns/`
  - `backend/app/task_guidance/` entry modules

---

## 6. Gate Conditions

## Gate S4-0 — Dispatch Start

Required before dispatching Wave 1a:

- Stage 4 vision alignment doc signed
- Stage 4 engineering structure doc signed
- this dispatch plan signed

## Gate S4-1 — Async Substrate Ready

Required before Wave 1b:

- Celery nearline path exists and is testable
- Corpus V1 exists and runs
- no Stage 3 routing regression with flags off

## Gate S4-2 — Routing Seam Ready

Required before Wave 2:

- `routing_mode` path exists
- all routing-mode changes are behind feature flags
- default behavior remains `direct`-equivalent when flags are off

## Gate S4-3 — Closed-Loop Paths Function

Required before Wave 3:

- human-guide default path works
- AI-guide on-demand path works
- task assistant dormant mode works
- conversation escalation works using only approved triggers

## Gate S4-4 — Budget and Eval Stable

Required before any future activation planning:

- inline latency budget holds:
  - P95 `<= 100ms`
  - cost `<= 0.1x` LLM baseline per request
- nearline latency budget holds:
  - P95 `<= 30s`
  - P99 `<= 60s`
  - cost `<= 1x` LLM baseline per session
- long-horizon cost anchor holds:
  - `<= 0.5x` LLM baseline / active user / day
- Corpus V4 reaches `>=100` production-replay cases
- Corpus V4 covers all three routing modes:
  - `direct`
  - `workflow`
  - `task_assistant`
- Stage 4 activation-prep runbook v1 is drafted
- Stage 3 WS-M Phase 1 remains stable

---

## 7. Explicitly Deferred in This Dispatch Plan

The following remain out of scope:

1. pre-tool-selection takeover
2. pre-response-formatting takeover
3. Stage 4 real-user rollout
4. any new queueing stack beyond Celery
5. any stealth Gate 0 schema amendment
6. any new external-AI primary path
7. any WS-M Phase 1 expansion beyond what Rule F allows

---

## 8. Immediate Recommended Next Step

If this dispatch plan is accepted, the first dispatch should be:

1. `Agent A` — WS-A.1 Async Substrate
2. `Agent B` — WS-C.1 TaskGuidance Skeleton
3. `Agent C` — WS-F.1 Benchmark and Guardrails Prep

Then, only after Gate S4-1 passes:

4. `Agent D` — WS-B.1 Routing-Mode Seam

This keeps Stage 4 aligned with its intended shape:

- async substrate first
- routing seam second
- closed-loop product paths after that

Not the other way around.
