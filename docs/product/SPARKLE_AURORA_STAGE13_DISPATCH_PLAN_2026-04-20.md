# SPARKLE Aurora Stage 13 Dispatch Plan (2026-04-20)

> **Status**: Stage 13 dispatch baseline v0 after Stage 12 final-accept
> **Authority**: `SPARKLE_AURORA_STAGE12_HANDOFF_2026-04-20.md` is the only Stage 12 truth source; this plan starts from that frozen baseline and must not reopen completed Stage 5 through Stage 12 work.
> **Depends on**:
> - `SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md`
> - `SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE12_HANDOFF_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE12_CL0_RERUN_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE11_CL0_AUDIT_METHOD_2026-04-20.md`
> **Scope**: Stage 13 execution design. Converts continuous-learning front-door readiness from subjective judgment into a measured gate, while allowing one bounded user-visible evidence expansion that does not depend on `WS-CL1`.

## 0. Stage 13 Positioning

Stage 12 proved two things at once:

1. the learning substrate can be repaired without widening write authority
2. repairing substrate defects still does **not** make any continuous-learning component eligible for user-facing wiring

### One-sentence definition

**Stage 13 is the stage where Sparkle defines and applies a formal signal-quality gate so "can this learning component go user-visible?" stops being a vibe and becomes a measurable decision.**

### What Stage 13 must treat as already settled

1. Stage 12 final-accept is frozen and valid
2. Stage 12 `CL0` rerun triggered **Path C**
3. `WS-CL1` remains blocked
4. `strategy_store` is already a durable **L2 inference cache**
5. Stage 12 mobile debt is terminally resolved as `fix / isolate / delete`
6. Rule K remains `35 files / 0 violation`

### Stage 13 starting problem

The remaining problem is no longer "there is a broken seam." The remaining problem is:

> **we still do not have a formal, reusable definition of what makes a continuous-learning signal trustworthy enough to wire into the front door.**

Stage 13 therefore prioritizes the root:

- define the quality gate
- measure at least one repaired component against it
- fix the highest-leverage upstream signal-fidelity problem that the measurement reveals
- ship one small user-visible evidence improvement that stays independent of the continuous-learning wire decision

### Explicit non-goals

1. no `WS-CL1`
2. no graph diagnostic deepening
3. no dual interaction mode formalization
4. no Aurora parameter-write expansion
5. no new learner, no new strategy-store role, no new compiler

## 1. Governance Layering

### Rule Families

| Alias | Rules | Meaning |
| --- | --- | --- |
| `[Write-K Family]` | `K / N / P / S / T` | write-lane isolation and merge-blocking safeguards |
| `[Eval Family]` | `L / R` | consumer / runner closure and evaluation read-only discipline |
| `[Close Family]` | `G / I / J` | single-WS commit chain, handoff integrity, user-value closure |
| `[Boundary Family]` | `H / M / O` | allowlists, no third compiler, no silent bounded-steering expansion |
| `[Legibility]` | `Q` | evidence legibility and no fact masquerading |
| `[Verification]` | `U / V` | operability proof and audit-regression proof |
| `[Quality Family]` | `W` | measurement-before-wire discipline |

Stage 13 does not rewrite existing rules. It adds one new quality rule because Path C needs a formal answer to "what would count as wire-ready?"

### Rule W · Measurement-before-Wire

Any continuous-learning component must not enter a user-visible decision path unless a formal signal-quality audit gives it all four required dimensions and all four meet the declared wire-ready thresholds.

Hard interpretation:

1. the measurement method must be committed before measurement code or measurement reports
2. every measured component must report four dimensions:
   - information density
   - stability
   - discriminative power
   - safety margin
3. if a dimension cannot yet be computed, it must be explicitly marked `unmeasurable` with a reason
4. wire-ready thresholds may not be silently lowered inside a single WS
5. threshold changes require an explicit audit-method revision rather than an implementation-side convenience tweak

## 2. Stage 13 Scope

| ID | Goal | Boundary | Exit condition |
| --- | --- | --- | --- |
| `Gate S13-0` | frozen baseline replay before any Stage 13 work | verification-only | Stage 12 frozen baseline, Rule V tests, and Rule K guard all replay green |
| `WS-SQ-METHOD` | define the formal Signal Quality Audit Method (`SQAM`) | docs and worked example only | method artifact lands with metrics, thresholds, and one worked example |
| `WS-SQ-MEASURE` | run `SQAM` on `PersistentBayesianLearner` | measurement-only, no learner redesign | audit report lands with 4 dimensions, scores or `unmeasurable`, and one ranked shortfall |
| `WS-SQ-FEED` | fix the #1 upstream signal-fidelity shortfall identified by `WS-SQ-MEASURE` | input-data fidelity only; do not change learner semantics | rerun of the affected SQAM dimension improves, with Rule V regression proof |
| `WS-EVD3-LITE` | add one new safe evidence type to the current evidence-card route system | display + route only; no continuous-learning write path | widget tests prove display and route for the new type |

### Explicitly deferred beyond Stage 13

1. `WS-CL1` user-facing continuous-learning wiring
2. graph diagnostic deepening beyond the current Stage 10 / 11 surface
3. dual interaction mode formalization
4. prompt-context rendering expansion as a proxy for continuous-learning readiness
5. any new learner or new strategy-store field expansion

## 3. Wave Order

`Gate S13-0 -> WS-SQ-METHOD -> WS-SQ-MEASURE -> (WS-SQ-FEED || WS-EVD3-LITE) -> Gate S13-FINAL`

Hard interpretation:

1. `WS-SQ-METHOD` must land before `WS-SQ-MEASURE`
2. `WS-SQ-MEASURE` must land before `WS-SQ-FEED`
3. `WS-SQ-FEED` may repair only the **top-ranked** signal-fidelity shortfall from the measurement report
4. `WS-EVD3-LITE` may run in parallel with `WS-SQ-FEED` because it is explicitly decoupled from continuous-learning wire decisions
5. `Gate S13-FINAL` must rerun the same frozen Stage 12 baseline plus the new SQAM evidence

## 4. Gate S13-0 Requirements

Stage 13 may not enter `WS-SQ-METHOD` until the following are replayed and recorded:

1. Stage 12 frozen baseline:
   - `144 passed`
2. Rule V regression suite:
   - `8 passed`
3. Rule K guard:
   - `35 files / 0 violation`

Recommended replay commands:

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/aurora \
  tests/api/test_profile_transparency_api.py \
  tests/profile/eval/test_profile_eval_skeleton.py \
  tests/profile/test_intervention_verification_loop.py \
  tests/unit/test_situation_brief.py \
  tests/unit/test_phase2_intervention_pipeline.py \
  -q
```

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_persistent_bayesian_learner_contract.py \
  tests/unit/test_multi_dimensional_learner_contract.py \
  tests/unit/test_distilled_strategy_store_contract.py \
  -q
```

```bash
./backend/.venv/bin/python scripts/check_rule_k_write_paths.py
```

## 5. Workstream Artifacts That Must Land Before Code

### 5.1 `WS-SQ-METHOD`

Artifact must lock:

1. the four dimensions:
   - information density
   - stability
   - discriminative power
   - safety margin
2. one computable metric per dimension
3. one wire-ready threshold per dimension
4. `unmeasurable` handling rules
5. one worked example using a real Stage 12-repaired component
6. a short subsection: "how future stages cite Rule W"

### 5.2 `WS-SQ-MEASURE`

Artifact must lock:

1. the chosen component:
   - `PersistentBayesianLearner`
2. the exact production entrypoints being evaluated
3. the four reported dimension values
4. the ranked shortfall list
5. the chosen `#1` shortfall that `WS-SQ-FEED` is allowed to repair

### 5.3 `WS-SQ-FEED`

Artifact must lock:

1. the exact upstream signal-fidelity shortfall selected from `WS-SQ-MEASURE`
2. why it is upstream-data fidelity rather than learner redesign
3. the narrow repair boundary
4. the exact SQAM dimension expected to improve
5. Rule V regression assertions that reproduce the reported symptom

### 5.4 `WS-EVD3-LITE`

Artifact must lock:

1. the single new evidence type:
   - recommended: `PracticeOutcomeEvidence`
2. the display payload shape
3. the route mapping
4. why the new type is safe to expose without touching continuous-learning write lanes
5. the widget proof points required by Rule U

## 6. Non-Negotiable Constraints

1. Stage 13 inherits Rule G through Rule W
2. `WS-SQ-FEED` must satisfy Rule V with a regression test that directly reproduces the measured shortfall symptom
3. `WS-EVD3-LITE` must remain pure display + route; it may not add a write path
4. `WS-EVD3-LITE` may not use the new type as a backdoor to claim continuous-learning wire readiness
5. `WS-SQ-FEED` may not "also fix" a second shortfall
6. no Stage 13 change may introduce a new learner, a new strategy-store role, or a new compiler
7. no Stage 13 change may widen Aurora write authority or dual-core write semantics
8. `evidence_cards.dart` may gain a narrow type branch for `WS-EVD3-LITE`, but it must not become a broad refactor

## 7. Workstream Cards

### 7.1 `WS-SQ-METHOD` — Signal Quality Audit Method

**Goal**

Define a formal, reusable measurement method so future "can this component go user-visible?" decisions stop relying on intuition.

**In-scope**

- formal definition of the four dimensions
- metric and threshold declaration
- worked example
- Rule W reference guidance

**Out-of-scope**

- measuring multiple components
- changing any runtime code
- lowering any pre-existing gate by prose

**Accept requires**

1. artifact lands before measurement code
2. all four dimensions are defined
3. thresholds are explicit
4. worked example is included

### 7.2 `WS-SQ-MEASURE` — PersistentBayesianLearner Baseline

**Goal**

Run `SQAM` against one repaired component and produce a baseline scorecard that exposes the real remaining problem.

**In-scope**

- evaluate `PersistentBayesianLearner`
- report four dimensions
- rank shortfalls
- freeze one top shortfall for `WS-SQ-FEED`

**Out-of-scope**

- component redesign
- silent threshold changes
- claiming wire readiness from a partial result

**Accept requires**

1. report lands after `WS-SQ-METHOD`
2. each dimension has either a score or `unmeasurable`
3. the top shortfall is explicit
4. no runtime mutation is hidden inside the measurement step

### 7.3 `WS-SQ-FEED` — Upstream Signal-Fidelity Repair

**Goal**

Respond directly to the highest-value upstream shortfall found in `WS-SQ-MEASURE`, without redesigning the learner itself.

**In-scope**

- upstream input-data fidelity repair
- narrow, single-shortfall remediation
- SQAM rerun on the affected dimension
- Rule V regression proof

**Out-of-scope**

- learner redesign
- front-door wiring
- second-shortfall opportunism

**Accept requires**

1. fix-design artifact names the exact shortfall
2. regression test reproduces the reported symptom
3. rerun shows improvement on the targeted dimension
4. Rule K remains untouched

### 7.4 `WS-EVD3-LITE` — One New Safe Evidence Type

**Goal**

Keep product momentum with one bounded evidence-surface improvement that is independent of continuous-learning wire decisions.

**In-scope**

- add one safe evidence type
- render it in the existing evidence-card system
- route it using the existing `onRouteTap` pattern
- widget proof for display and route

**Out-of-scope**

- any write path
- any graph deepening
- any broad evidence-card refactor
- any claim that the new type reflects user-facing continuous-learning readiness

**Accept requires**

1. one new evidence type only
2. widget proof covers display and route
3. route follows the existing safe evidence-card pattern
4. no new write lane exists

## 8. Gate S13-FINAL

Stage 13 may close only if all of the following are true:

1. Stage 12 frozen baseline still replays green
2. Rule V regression suite still replays green
3. Rule K guard remains `35 / 0`
4. `WS-SQ-METHOD` artifact exists and is cited by `WS-SQ-MEASURE`
5. `WS-SQ-MEASURE` report exists with four dimensions
6. `WS-SQ-FEED` rerun shows improvement on the chosen dimension
7. `WS-EVD3-LITE` has widget-level Rule U proof
8. handoff explicitly states whether any component moved closer to `wire`, without overstating readiness

## 9. Stage 14 Entry Logic

Stage 13 should leave Stage 14 with a more precise fork than Stage 12 had:

1. if one component clears all Rule W thresholds:
   - Stage 14 may propose a bounded `WS-CL1` candidate for that component only
2. if one component improves but still misses threshold:
   - Stage 14 continues root repair, not wire decisions
3. if no component becomes measurable enough:
   - Stage 14 treats continuous learning as an architecture rethink rather than a rollout question
