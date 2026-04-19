# SPARKLE Aurora Stage 7 Dispatch Plan (2026-04-19)

> **Status**: Stage 7 dispatch baseline v0.1 after Stage 6 closeout
> **Authority**: `SPARKLE_AURORA_STAGE6_HANDOFF_2026-04-19.md` is the only Stage 6 truth source; this plan starts from that frozen baseline and must not reopen completed Stage 5 / Stage 6 work.
> **Depends on**:
> - `SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md`
> - `SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE5_DISPATCH_PLAN_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE5_HANDOFF_2026-04-19.md`
> - `SPARKLE_USER_MODEL_SOURCE_AUDIT_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE6_HANDOFF_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE6_PROFILE_EVAL_BASELINE_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE6_PROFILE_TRANSPARENCY_LOOP_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE6_INTERVENTION_VERIFICATION_LOOP_2026-04-19.md`
> **Scope**: Stage 7 execution design. Converts the four residual gaps named in Stage 6 handoff §7 into dispatchable workstreams, ownership boundaries, acceptance rules, and closeout gates.

## 0. Stage 7 Positioning

Stage 6 proved that the user-model stack is real, canonical prompt rendering is landed, backend transparency/correction is functional, and intervention verification is explicit enough to inspect.

Stage 7 must not relitigate that.

### One-sentence definition

**Stage 7 is the stage where the remaining Stage 6 residuals become auditable production paths rather than partial scaffolds, inert surfaces, or adjacent compiler seams.**

### What Stage 7 must treat as already settled

The following are frozen baseline facts unless new evidence proves a regression:

1. the user-model stack is `pipeline + projection cache`, not a second source-of-truth store
2. canonical `UserInsightState` can reach prompt rendering
3. the backend transparency/correction loop exists and is test-backed
4. intervention verification is explicit at the record level

### Stage 7 starting gaps

Per `SPARKLE_AURORA_STAGE6_HANDOFF_2026-04-19.md` §7, Stage 7 starts from exactly four carry-forwards:

1. deeper `M1` data quality and source coverage
2. frontend consumption of transparency/correction surfaces
3. a real evaluation runner on top of the `WS-E1` skeleton
4. cleaner ownership between the canonical profile compiler and the situation-brief compiler

## 1. Stage 7 Principles

### Principle A: No Stage 5 / Stage 6 Reopen

Stage 7 may tighten, connect, or normalize the landed system.
It may not reframe completed Stage 5 / Stage 6 work as unfinished just to justify larger rewrites.

### Principle B: One Residual Gap, One Workstream

Each of the four Stage 7 entry gaps maps to one primary workstream.
Cross-gap edits require explicit seam extraction or dispatcher approval.

### Principle C: Consumer Proof Beats Capability Proof

Backend capability is not enough for:

- frontend transparency/correction
- profile-aware evaluation

Acceptance must prove a real consumer or runner path, not only a latent API or fixture.

### Principle D: Rule K Stays Hard

Stage 7 continues the layered write-path discipline:

- `L0` writes raw evidence only
- `L1` writes projection cache only
- `L2` writes inference/evaluation artifacts only
- `L3` writes only white-listed parameters, with audit
- user correction remains the only direct override lane for profile-facing truth

No Stage 7 task may sneak fact writes into evaluation, frontend, or compiler-normalization work.

### Principle E: Normalize via Adapter First

The dual-compiler gap should be closed by reducing duplicated interpretation logic and clarifying ownership.
Stage 7 should prefer adapter consolidation over schema churn or a big-bang rewrite.

## 2. Explicitly Out of Scope

The following are not Stage 7 scope unless a later amendment says otherwise:

1. redesign of `L0` storage or event schemas
2. a new user-model source-of-truth database
3. Aurora write authority over fact data
4. shadow activation or rollout expansion beyond current readiness limits
5. intervention-verification schema redesign beyond the landed explicit payload
6. broad mobile IA / design-system rewrites unrelated to transparency consumption
7. replacing the current bounded inline snapshot with tokenizer-perfect budget enforcement as a stage headline

## 3. Workstream Overview

| Workstream | Focus | Primary lane | Breakpoint advanced | Anchor signal | Priority |
| --- | --- | --- | --- | --- | --- |
| `WS-M1c` | `M1` source coverage + data-quality hardening | `L1` over `L0` evidence | source inventory -> usable profile quality | `A1`, `A4`, `A5` | highest |
| `WS-V2` | mobile transparency/correction consumption | `User Correction` + `L1` read surfaces | backend loop -> visible user loop | `A1`, `A2`, `A5` | highest |
| `WS-E2` | real read-only evaluation runner | `L2` evaluation surface | skeleton -> runnable evaluation path | `A1`, `A3`, `A4` | high |
| `WS-C1` | dual-compiler normalization | `L1 -> L3` projection boundary | adjacent compilers -> owned adapter seam | `A1`, `A5` | high |

### Wave Order

Stage 7 keeps the four-workstream scope, but the accept order is not fully parallel:

1. `WS-C1` must close before `WS-M1c`, `WS-V2`, and `WS-E2` reach final accept.
2. `WS-C1` design output may run in parallel with the others' implementation prep, but downstream accept gates depend on its ownership decision.
3. after `WS-C1` settles the canonical adapter boundary, `WS-M1c`, `WS-V2`, and `WS-E2` may close in parallel.

### Concrete judgment baked into Stage 7

1. `WS-V2` means binding a real frontend surface, not adding more backend-only tests.
2. `WS-E2` means attaching a real runner, not expanding fixture prose.
3. `WS-C1` means reducing parallel interpretation logic, not building a third compiler.
4. `WS-M1c` improves coverage and signal quality inside the existing profile pipeline; it does not redesign raw evidence infrastructure.

## 4. Dispatch Rules

Stage 7 inherits `Rule G`, `Rule H`, `Rule I`, `Rule J`, and `Rule K`.

### Rule L · Consumer / Runner Closure Requirement

Any Stage 7 task claiming closure for transparency or evaluation must show:

1. a real consuming surface or runner entrypoint
2. an acceptance test that exercises that path
3. no new hidden fallback that leaves the old inert path effectively unchanged

### Rule M · No Third Compiler

Stage 7 may edit `ProfileTruthCompiler`, `UserInsightCompiler`, adapters, and contracts.
It may not introduce a third long-lived profile interpretation path.

Hard interpretation:

- canonical profile facts still originate in `UserInsightCompiler -> UserInsightState`
- `ProfileTruthCompiler` may project or adapt, but should not re-grow a competing fact pipeline
- any new raw-dict-only render path must stop and escalate

## 5. Review Lanes

High-risk lane:

`GLM-exec -> Codex initial review -> GLM-observer pre-accept -> Claude final-accept -> User sign-off`

Low-risk lane:

`GLM-exec -> Codex initial review -> User spot-check / sign-off`

### Stage 7 high-risk triggers

Any task touching one of the following is automatically high-risk:

1. `backend/app/services/user_insight_compiler.py`
2. `backend/app/services/profile_truth_compiler.py`
3. `backend/app/orchestration/situation_brief.py`
4. `backend/app/orchestration/prompts.py`
5. `backend/app/api/v1/profile_transparency.py`
6. `mobile/lib/features/user/presentation/providers/ws6_profile_mirror_provider.dart`
7. `mobile/lib/features/user/presentation/screens/profile_transparent.dart`
8. any new Stage 7 evaluation runner entrypoint under `backend/app/services/` or `backend/tests/profile/eval/`

## 6. Hotspot Ownership

| File / Zone | Owner | Reason |
| --- | --- | --- |
| `backend/app/services/user_insight_compiler.py` | `WS-M1c` | source-family coverage and projection-quality hardening |
| `backend/app/profile/projection_contract.py` | `WS-M1c` | compiled source registry and projection contract discipline |
| `backend/app/api/v1/profile_transparency.py` | `WS-V2` | canonical transparency payload / correction endpoints consumed by frontend |
| `mobile/lib/features/user/data/repositories/user_repository.dart` | `WS-V2` | mobile read/write binding for transparency and corrections |
| `mobile/lib/features/user/presentation/providers/ws6_profile_mirror_provider.dart` | `WS-V2` | current inert adapter path and gating seam |
| `mobile/lib/features/user/presentation/screens/profile_transparent.dart` | `WS-V2` | visible transparency surface |
| `backend/tests/profile/eval/` | `WS-E2` | fixture-backed evaluation contract and runner acceptance |
| `backend/app/services/profile_truth_compiler.py` | `WS-C1` | normalization of canonical-to-situation projection ownership |
| `backend/app/orchestration/situation_brief.py` | `WS-C1` | downstream consumer of compiled profile truth |
| `docs/product/*STAGE7*` | `Codex` | integration, sequencing, and closeout governance |

### Shared-file rule

If one workstream needs information from another hotspot:

1. request a seam extraction or adapter handoff
2. do not silently co-edit the other workstream's hotspot

## 7. Workstream Cards

## 7.1 `WS-M1c` — M1 Data Quality and Source-Coverage Deepening

**Goal**

Strengthen `M1` from “source families are present” to “source coverage and signal quality are explicit, auditable, and useful for downstream compilation.”

**Why this exists**

Stage 6 named the real gap precisely:

- source families are already present in `UserInsightCompiler`
- `UserProjectionContract` already exposes a source-family inventory
- but coverage depth, freshness quality, motivation-pattern quality, anti-pattern quality, and cognitive-tendency quality remain uneven

**Stage 7 in-scope**

- add an explicit coverage/quality registry derived from the existing `signal_evidence` families and key projections
- audit and harden undercompiled `M1` domains:
  - motivation patterns
  - anti-patterns / blockers
  - cognitive tendencies
- add data-quality markers that downstream layers can inspect without inventing a new source-of-truth
- expand tests so source-family presence and minimum quality invariants are verified

**Stage 7 out-of-scope**

- redesigning `L0` storage
- moving raw evidence ownership out of existing services
- migrating `M1` into a separate platform

**Acceptance target**

At accept time, we should be able to point to:

1. a stable, test-backed source-coverage artifact in the compiled profile contract
2. visibly improved compile quality for previously thin `M1` domains
3. no Rule K violations and no new raw-evidence writes outside existing `L0` paths

## 7.2 `WS-V2` — Transparency / Correction Frontend Consumption

**Goal**

Turn the Stage 6 backend transparency loop into a real user-facing read/write surface on mobile.

**Why this exists**

The repo already contains mobile scaffolding:

- `ProfileTransparentScreen`
- `ws6_profile_mirror_provider.dart`
- `kWs6ProfileSurfaceEnabled = false`
- repository calls for `/profile/context` and `/profile/corrections`

But the current surface remains gated/inert and still leans on the legacy `/profile/transparent` provider path.

**Stage 7 in-scope**

- bind the mobile transparency surface to the canonical Stage 6 payloads:
  - `user_insight_transparency` from `/profile/context`
  - `/profile/insights`
  - existing correction/control endpoints
- remove or reduce the inert WS6 gating once the live path is proven
- prove that a correction or control action is reflected in the visible mobile flow
- add provider / widget / integration coverage for the visible path

**Stage 7 out-of-scope**

- inventing a brand-new transparency product surface
- redesigning the transparency payload contract
- widening write lanes beyond existing correction/control endpoints

**Acceptance target**

At accept time, we should be able to show:

1. a live mobile read path for transparency claims/calibration/unknowns
2. a live mobile correction or control submission path
3. tests proving the visible frontend loop rather than only the backend API

## 7.3 `WS-E2` — Real Read-Only Profile Evaluation Runner

**Goal**

Attach a real runner to the `WS-E1` evaluation skeleton while preserving the Stage 6 read-only boundary.

**Why this exists**

Stage 6 landed:

- fixture families
- schema checks
- a documented write scope of `evaluation_records_only`

But there is still no runnable evaluation path beyond pytest fixture validation.

**Stage 7 in-scope**

- implement a real runner entrypoint over the existing fixture families
- keep the runner read-only with respect to `L0`, `L1`, and `L3`
- emit evaluation artifacts or records only inside the evaluation lane
- add acceptance tests proving the runner can execute the baseline fixtures end-to-end

**Stage 7 out-of-scope**

- fact writes
- Aurora parameter writes
- cohort analytics platform work
- pretending fixture-shape tests alone satisfy Stage 7

**Acceptance target**

At accept time, we should be able to run a concrete evaluation command or test path that:

1. consumes the Stage 6 baseline fixtures
2. executes a real runner
3. produces read-only evaluation output
4. leaves profile facts and control state untouched

## 7.4 `WS-C1` — Dual-Compiler Normalization

**Goal**

Reduce the split between `UserInsightCompiler -> UserInsightState` and `ProfileTruthCompiler -> CompiledInsightState` into a clearly owned adapter boundary instead of two adjacent interpretation paths.

**Why this exists**

Stage 6 repaired the render leak but intentionally did not eliminate the adjacent-compiler topology.

Current reality:

- canonical facts live in `UserInsightState`
- `ProfileTruthCompiler` can coerce canonical state and project it forward
- fallback extraction logic still exists when canonical state is absent

Stage 7 must normalize ownership without destabilizing downstream consumers.

**Stage 7 in-scope**

- produce a complete call-chain diagram of `UserInsightCompiler -> UserInsightState -> ProfileTruthCompiler -> CompiledInsightState` before deciding between merge vs eliminate vs adapter-only normalization; the decision must be evidence-driven, not assumed
- make the adapter boundary explicit
- reduce duplicated extraction logic where canonical state already exists
- preserve fallback behavior where canonical state is genuinely absent
- add tests that prove prompt/situation-brief paths do not drift from canonical profile truth

**Stage 7 out-of-scope**

- a schema-breaking rewrite of `CompiledInsightState`
- removing downstream compatibility surfaces in one shot
- creating a third compiler

**Acceptance target**

At accept time, we should be able to say:

1. canonical profile truth has one clear owner
2. the situation-brief compiler is an adapter/projection seam, not a competing fact compiler
3. prompt and situation-brief consumers stay aligned on the same canonical signals

## 8. Acceptance Gates

### Gate S7-0 · Baseline Freeze

Before landing Stage 7 work, the Stage 6 post-close sweep must still reproduce:

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/aurora \
  tests/api/test_profile_transparency_api.py \
  tests/profile/eval/test_profile_eval_skeleton.py \
  tests/profile/test_intervention_verification_loop.py \
  tests/unit/test_situation_brief.py \
  tests/unit/test_phase2_intervention_pipeline.py -q
```

Baseline result on branch tip when this plan was written:

- `140 passed`
- `0 failed`

### Gate S7-1 · Per-WS Proof

Each Stage 7 workstream must land with:

1. focused automated verification for its owned hotspot
2. a short handoff note or accept artifact
3. explicit confirmation that no Stage 6 truth claim was reopened

### Gate S7-Close · Full Post-Close Sweep

Before Stage 7 can be declared closed:

1. rerun the Stage 6 baseline command above
2. run any new Stage 7 mobile / evaluation / compiler-normalization tests
3. record the full post-close result in the Stage 7 handoff artifact

Subset-only green is not sufficient.

## 9. Next Entry Condition

Stage 7 execution may start immediately from this plan if:

1. `SPARKLE_AURORA_STAGE6_HANDOFF_2026-04-19.md` remains the governing Stage 6 baseline
2. Stage 6's `140 passed` baseline remains reproducible
3. dispatchers keep scope pinned to the four residual gaps listed here

If those conditions hold, Stage 7 should spend its effort on closure and normalization rather than rediscovering architecture already settled in Stage 5 / Stage 6.

## 10. Explicit Cross-Stage Deferrals

Stage 7 intentionally does not absorb every historical residual. The following items remain explicitly deferred so they do not disappear from governance tracking:

| Item | Origin | Status | Next home | Constraint |
| --- | --- | --- | --- | --- |
| breakpoint `#3` `plan health no event` | Stage 5 handoff §6 | deferred | Stage 8 | must be explicitly assigned in the Stage 8 dispatch plan |
| breakpoint `#4` `push time-only` | Stage 5 handoff §6 | deferred | Stage 8 | must be explicitly assigned in the Stage 8 dispatch plan |
| breakpoint `#5` `cognitive_adjustments text-only` | Stage 5 handoff §6 | deferred | Stage 8 | must be explicitly assigned in the Stage 8 dispatch plan |
| `RB1` tokenizer-aware inline budget precision | post-`WS-RP1` precision tail | deferred / out of Stage 7 scope | Stage 8 candidate or later amendment | not a Stage 7 blocker unless a regression proves the bounded snapshot discipline insufficient |

Hard interpretation:

1. `#3/#4/#5` are not part of the four-workstream Stage 7 execution surface.
2. this is the last governance-safe deferral for `#3/#4/#5`; Stage 8 planning must either absorb them or explicitly justify a blocking amendment.
3. `RB1` remains tracked as a precision tail, not as a hidden Stage 7 acceptance condition.
