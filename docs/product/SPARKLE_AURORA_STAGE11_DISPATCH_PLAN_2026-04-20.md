# SPARKLE Aurora Stage 11 Dispatch Plan (2026-04-20)

> **Status**: Stage 11 dispatch baseline v0 after Stage 10 final-accept
> **Authority**: `SPARKLE_AURORA_STAGE10_HANDOFF_2026-04-20.md` is the only Stage 10 truth source; this plan starts from that frozen baseline and must not reopen completed Stage 5 / Stage 6 / Stage 7 / Stage 8 / Stage 9 / Stage 10 work.
> **Depends on**:
> - `SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md`
> - `SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE10_HANDOFF_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE11_GATE_S11_BASELINE_REPORT_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE11_MOBILE_TRIAGE_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE11_CL0_AUDIT_SKELETON_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE11_EVD2_ROUTE_CONTRACT_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE11_EV4_CONFIG_SCHEMA_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE11_MET2_DASHBOARD_FIELDS_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE11_CL0_AUDIT_METHOD_2026-04-20.md`
> **Scope**: Stage 11 execution design. Tightens the trust chain around Stage 10's already-landed seams without widening truth-write authority.

## 0. Stage 11 Positioning

Stage 10 made Sparkle evidence-clickable, evaluator-backed, and graph-diagnostic.
Stage 11 exists to close the remaining "claimed" versus "operable" gaps around those surfaces.

### One-sentence definition

**Stage 11 is the stage where Sparkle's Stage 10 trust seams become actually operable, configurable, observable, and auditable.**

### What Stage 11 must treat as already settled

1. Stage 9 / 10 frozen baseline remains `144 passed`
2. Rule K guard remains merge-blocking and must stay `35 files / 0 violation`
3. `WS-EVD1` already upgraded evidence payloads to `l0_clickable_refs`
4. `WS-EV3` already attached a real judge path with graceful fallback
5. `WS-G2D` already landed a read-only graph diagnostic surface

### Stage 11 starting gaps

1. evidence drawer is single-layer only; it does not yet route the user into the corresponding product surface
2. judge weighting / timeout / budget / prompt versioning remain hard-coded
3. MET1 utilization carrier exists, but developer-facing dashboard surfaces are still thin
4. continuous-learning components still lack a production-grade trust verdict and must not be wired into the user front door on hope alone

## 1. Governance Rule Layering

| Category | Rules |
| --- | --- |
| write | `K / N / P / S / T` |
| evaluation | `L / R` |
| closure | `G / I / J` |
| boundary | `H / M / O` |
| readability | `Q` |
| operability | `U` |

No rule merge is attempted in Stage 11. Stage 11 keeps layered labels only.

### Rule U · User Operability Verification

Any Stage 11 deliverable that claims a user can click, route, or operate an interaction must prove that path with a frontend component-level verification, or must explicitly declare the missing secondary navigation in known limits.

Hard interpretation:

1. widget coverage must exercise the path's `onTap`, `Navigator`, or `GoRouter` call
2. if a secondary route is intentionally absent, the handoff must list that exact limit in `known limits`
3. silent UI dead-ends are final-accept blockers

## 2. Stage 11 Scope

| ID | Goal | Nature | Depends on |
| --- | --- | --- | --- |
| `Gate S11-0` | frozen baseline replay + mobile debt triage + CL0 skeleton occupancy | entry gate | none |
| `WS-EVD2` | evidence drawer secondary routing: error -> error book, concept -> galaxy, session -> chat history | defect closure | `WS-EVD1` |
| `WS-EV4` | judge engineering: weight config, timeout / budget config, prompt versioning, graceful fallback | Stage 10 tail-closure | `WS-EV3` |
| `WS-MET2` | utilization metric carrier -> dashboard / export visibility | observability closure | `WS-MET1` |
| `WS-CL0` | continuous-learning signal quality audit only, no user wiring | audit-only | none |

### Explicitly deferred beyond Stage 11

1. `WS-CL1` user-facing continuous-learning wiring
2. `WS-EVD3` evidence type expansion beyond current safe set
3. `WS-DI1` dual interaction mode formalization

## 3. Wave Order

`Gate S11-0 -> (WS-EVD2 || WS-MET2) -> WS-EV4 -> WS-CL0`

Hard interpretation:

1. `Gate S11-0` must land before Wave 1 implementation starts
2. `WS-EVD2` and `WS-MET2` may implement in parallel once their artifacts are frozen
3. `WS-EV4` may not land before its config schema artifact is committed
4. `WS-CL0` may not write, mutate, or wire any user-facing surface

## 4. Gate S11-0 Requirements

Stage 11 may not enter Wave 1 until the following artifacts are committed:

1. baseline replay report with `144 passed` and Rule K `35 / 0`
2. mobile old-debt triage report with explicit `fix / isolate / defer` classification per failure
3. CL0 skeleton artifact covering five learning components and four audit fields each

## 5. Workstream Artifacts That Must Land Before Code

1. `WS-EVD2`
   - `SPARKLE_AURORA_STAGE11_EVD2_ROUTE_CONTRACT_2026-04-20.md`
2. `WS-EV4`
   - `SPARKLE_AURORA_STAGE11_EV4_CONFIG_SCHEMA_2026-04-20.md`
3. `WS-MET2`
   - `SPARKLE_AURORA_STAGE11_MET2_DASHBOARD_FIELDS_2026-04-20.md`
4. `WS-CL0`
   - `SPARKLE_AURORA_STAGE11_CL0_AUDIT_METHOD_2026-04-20.md`

## 6. Non-Negotiable Constraints

1. Stage 11 inherits Rule G through Rule U
2. `WS-EVD2` must satisfy Rule U with widget-level routing verification per new route
3. `WS-EV4` may not allow `judge_weight` at `0.0` or `1.0`; valid range is `[0.1, 0.9]`
4. `WS-EV4` must preserve `write_scope = evaluation_records_only`
5. `WS-CL0` is read-only and may not open any write lane
6. any skipped mobile old-debt test must be listed explicitly in Stage 11 handoff known limits

## 7. Workstream Cards

### 7.1 `WS-EVD2` — Evidence Drawer Secondary Routing

**Goal**

Turn Stage 10 evidence drill-down from a readable drawer into an operable bridge.

**In-scope**

- route from `concept` evidence to `/galaxy/node/:id`
- route from `error` evidence to `/errors/:id`
- route from `event` / session evidence to `/chat?session_id=...` when a safe session id is present
- explicit non-routable rendering for unsupported or redacted refs
- widget coverage per route to satisfy Rule U

**Out-of-scope**

- expanding backend evidence types
- creating a new evidence write lane
- hiding unsupported paths behind fake buttons

**Accept requires**

1. route contract artifact lands before code
2. each supported route type has widget proof of tap -> route dispatch
3. unsupported items stay visibly non-routable
4. no Rule U dead-end remains for supported evidence kinds

### 7.2 `WS-EV4` — Judge Engineering Closure

**Goal**

Make Stage 10's attached judge path configurable, versioned, and operationally explicit.

**In-scope**

- configurable rubric / judge weight with safe bounded range
- configurable timeout and budget fields
- committed prompt versioning surfaced in payload
- graceful fallback sample retained and test-covered

**Out-of-scope**

- any write outside `evaluation_records_only`
- letting the judge dominate or disappear through `0/100` or `100/0` weights
- runtime mutation of uncommitted prompt text

**Accept requires**

1. config schema artifact lands before code
2. live payload declares applied weight, timeout, budget, and prompt version
3. fallback still degrades to `rubric_only` semantics without crashing
4. Rule S remains structurally true

### 7.3 `WS-MET2` — Utilization Dashboard Visibility

**Goal**

Lift MET1 utilization carrier fields into the developer / operator surfaces.

**In-scope**

- backend dashboard payload adds utilization aggregates / counts / health summaries
- export surface includes the same fields in a stable shape
- mobile developer-facing panel renders prompt / inference utilization visibility
- tests prove no silent loss between tracker -> API -> mobile

**Out-of-scope**

- redefining MET1 formulas
- building a new standalone dashboard product
- changing prompt / inference capture semantics

**Accept requires**

1. dashboard field artifact lands before code
2. backend tests prove API payload includes utilization sections
3. mobile tests prove fields render on developer-facing surfaces
4. known / unknown / not_applicable states remain legible

### 7.4 `WS-CL0` — Continuous-Learning Signal Quality Audit

**Goal**

Produce a hard trust verdict for the five existing continuous-learning components before any user-facing wiring is allowed.

**In-scope**

- audit-only artifact with filled verdicts for:
  - `PromptBandit`
  - `PersistentBayesianLearner`
  - `distiller`
  - `multi_dimensional_learner`
  - `strategy_store`
- production state / signal quality / known defects / Stage 12 recommendation per component
- explicit pass / fail / do-not-wire recommendations

**Out-of-scope**

- wiring any component into IC1 or other user front doors
- adding write paths
- optimistic claims without code evidence

**Accept requires**

1. audit method artifact lands before any CL0 code or scripts
2. final artifact fills all five components and all four verdict fields
3. any low-trust component is explicitly marked `do_not_wire`
4. Stage 12 decision tree is driven by the artifact, not by optimism

## 8. Validation Baseline

Stage 11 must preserve:

1. Stage 9 / 10 frozen baseline: `144 passed`
2. Rule K guard: `35 files / 0 violation`

Stage 11 closeout is expected to add:

1. backend Stage 11 sweep covering `EVD2 / EV4 / MET2 / CL0`
2. mobile sweep covering new evidence routing and dashboard rendering
3. Rule U proof snippets in handoff verification evidence

## 9. Stage 12 Decision Lock

`WS-CL0` must conclude with one of these frozen paths:

1. if at least one component is trusted and user-perceptible -> Stage 12 may open `WS-CL1` only for those components
2. if only `PromptBandit` is production-worthy but not user-perceptible -> Stage 12 skips `CL1` and prioritizes `EVD3`
3. if no component is ready -> Stage 12 becomes infrastructure repair first

This decision tree is frozen by the Stage 11 handoff artifact and must not be improvised later.
