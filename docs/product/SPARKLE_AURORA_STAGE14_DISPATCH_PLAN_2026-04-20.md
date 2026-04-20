# SPARKLE Aurora Stage 14 Dispatch Plan (2026-04-20)

> **Status**: Stage 14 dispatch baseline v0 after Stage 13 final-accept
> **Authority**: [SPARKLE_AURORA_STAGE13_HANDOFF_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE13_HANDOFF_2026-04-20.md) is the only Stage 13 truth source; this plan starts from that frozen baseline and must not reopen completed Stage 5 through Stage 13 work.
> **Depends on**:
> - [SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md)
> - [SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md)
> - [SPARKLE_AURORA_STAGE13_HANDOFF_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE13_HANDOFF_2026-04-20.md)
> - [SPARKLE_AURORA_STAGE13_SIGNAL_QUALITY_AUDIT_METHOD_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE13_SIGNAL_QUALITY_AUDIT_METHOD_2026-04-20.md)
> - [SPARKLE_AURORA_STAGE13_PERSISTENT_BAYESIAN_SQAM_BASELINE_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE13_PERSISTENT_BAYESIAN_SQAM_BASELINE_2026-04-20.md)
> - [SPARKLE_AURORA_STAGE13_PERSISTENT_BAYESIAN_SQAM_RERUN_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE13_PERSISTENT_BAYESIAN_SQAM_RERUN_2026-04-20.md)
> **Scope**: Stage 14 execution design. Converts `PersistentBayesianLearner` from merely `wire-ready` under a frozen fixture into `wire-safe` under broader integration, larger-scale measurement, and zero-user-impact shadow observation.

## 0. Stage 14 Positioning

Stage 13 established something important but incomplete:

1. `PersistentBayesianLearner` is the first continuous-learning component to clear Rule W
2. that pass came from a small frozen fixture
3. one production integration path still falls back to `redis_client=None`

### One-sentence definition

**Stage 14 is the stage where Sparkle removes the last measurable pre-wire risks around `PersistentBayesianLearner` without actually turning the user-visible wire on.**

### What Stage 14 must treat as already settled

1. Stage 13 final-accept is frozen and valid
2. Stage 13 upgraded Stage 14 entry from Path C to **Path A**
3. `PersistentBayesianLearner` is the only component allowed to be considered for bounded `WS-CL1`
4. other continuous-learning components do **not** inherit the Bayesian learner's pass
5. Rule W remains the gate for any future user-visible wiring
6. `practice_outcome` evidence is already landed and must not be used as a backdoor learning claim

### Stage 14 starting problem

The remaining problem is no longer "can one component pass SQAM at all?" The remaining problem is:

> **can the only wire-ready component remain trustworthy once we remove its integration seams, enlarge the measurement scale, and observe it in production-shaped shadow mode?**

### Explicit non-goals

1. no actual wire-on
2. no work on `PromptBandit`, `distiller`, `multi_dimensional_learner`, or `strategy_store`
3. no new user-visible WS
4. no evidence-type expansion beyond what Stage 13 already landed
5. no Aurora write-boundary expansion
6. no prompt-context rendering expansion
7. no new governance rule

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

Stage 14 does **not** add a new rule. `Rule X` ("Shadow-before-Wire") is explicitly rejected at this stage because the workflow gap is procedural, not constitutional.

### Explicit rejection of Rule X

Stage 14 considered but rejects a new rule such as "Shadow-before-Wire."

Reasons:

1. Rule W already blocks user-visible wiring until quality is proven
2. Stage 14 shadow mode is an execution step inside the bounded `WS-CL1` preparation path, not a governance vacuum
3. shadow requirements can be enforced through Stage 14 and Stage 15 accept criteria without increasing rule density
4. if future pressure appears to skip shadow after passing SQAM, that is the point to revisit formal rule creation

## 2. Stage 14 Scope

| ID | Goal | Boundary | Exit condition |
| --- | --- | --- | --- |
| `Gate S14-0` | frozen baseline replay before any Stage 14 work | verification-only | Stage 12 baseline, Rule V suite, Rule K guard, and Stage 13 sweeps all replay green |
| `WS-CL1-INTEG` | eliminate `redis_client=None` production fallbacks | integration repair only; no learner-formula changes | all known call sites inject redis cleanly, with Rule V proof for the fallback symptom |
| `WS-CL1-SCALE` | rerun SQAM on a production-scale proxy fixture | fixture expansion and measurement only; same frozen SQAM method | `>=10` real source states, `>=200` observations, and all 4 dimensions stay green or Path A auto-downgrades |
| `WS-CL1-SHADOW` | run learner decisions in shadow while user-visible routing stays on fallback | L2 inference-cache-only recording, zero user-visible path | shadow recorder lands, divergence is queryable, and no prompt/push/evidence surface consumes it |
| `WS-CL1-SS-AUDIT` | assess whether `state_{tool_category}` compression blocks Stage 15 wire-on | audit-only, docs-only | explicit verdict: `blocking` or `non-blocking`, plus Stage 15 implication |
| `Gate S14-FINAL` | close Stage 14 with reruns and Stage 15 fork lock | verification-only | all Stage 14 verification evidence lands and Stage 15 fork is explicitly locked |

### Explicitly deferred beyond Stage 14

1. `WS-CL1` actual user-visible wire-on
2. measuring the other four continuous-learning components under SQAM
3. any graph diagnostic deepening
4. any new evidence type
5. any dual interaction mode formalization

## 3. Wave Order

`Gate S14-0 -> WS-CL1-INTEG -> (WS-CL1-SCALE || WS-CL1-SS-AUDIT) -> WS-CL1-SHADOW -> Gate S14-FINAL`

Hard interpretation:

1. `WS-CL1-INTEG` must land before `WS-CL1-SHADOW`; a partial integration makes shadow results misleading
2. `WS-CL1-SCALE` must land before `WS-CL1-SHADOW`; if scale rerun degrades, shadow does not proceed
3. `WS-CL1-SS-AUDIT` may run in parallel with `WS-CL1-SCALE` because it is doc-only and measures a different risk
4. if `WS-CL1-SCALE` shows any one dimension below threshold, Stage 14 automatically exits Path A and locks Path B
5. `Gate S14-FINAL` must state whether Stage 15 is `Path A-on`, `Path A-blocked`, or `Path B`

## 4. Gate S14-0 Requirements

Stage 14 may not enter `WS-CL1-INTEG` until the following are replayed and recorded:

1. Stage 12 frozen baseline:
   - `144 passed`
2. Rule V regression suite:
   - `8 passed`
3. Rule K guard:
   - `35 files / 0 violation`
4. Stage 13 backend sweep:
   - `23 passed`
5. Stage 13 mobile sweep:
   - `50 tests passed`

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

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_tool_preference_router.py \
  tests/unit/test_evidence_resolve.py \
  tests/tools/test_growth_tools.py \
  -q
```

```bash
cd mobile && flutter test \
  test/widget/evidence_card_navigation_test.dart \
  test/features/memory/presentation/widgets/evidence_cards_test.dart
```

## 5. Workstream Artifacts That Must Land Before Code

### 5.1 `WS-CL1-INTEG`

Artifact must lock:

1. the full call-site inventory for `ToolPreferenceRouter(..., redis_client=None)`
2. the target injection path per call site
3. whether any site remains intentionally non-persistent and why
4. the exact fallback symptom to be guarded by Rule V
5. if call sites exceed `5`, an integration-audit appendix is mandatory before code begins

### 5.2 `WS-CL1-SCALE`

Artifact must lock:

1. fixture size floor:
   - `>=10` source states
   - `>=200` observations
2. source-state naming must reflect real production-shaped tool-category / state semantics rather than synthetic placeholders
3. target coverage expectations across source→target pairs
4. the exact frozen SQAM method reference:
   - [SPARKLE_AURORA_STAGE13_SIGNAL_QUALITY_AUDIT_METHOD_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE13_SIGNAL_QUALITY_AUDIT_METHOD_2026-04-20.md)
5. the explicit anti-cheating statement:
   - fixture may not be tuned after reading the rerun scores
6. the downgrade rule:
   - any dimension regression below threshold means Stage 14 exits Path A

### 5.3 `WS-CL1-SHADOW`

Artifact must lock:

1. the recorder schema:
   - `timestamp`
   - `fallback_choice`
   - `learner_choice`
   - `source_state`
   - `eventual_outcome` when available
2. the storage location as L2 inference-cache-side only
3. a clear statement that shadow outputs do **not** enter prompt, push, evidence, or any user-visible path
4. a clear statement that Stage 14 builds the pipe only; observation-window policy belongs to Stage 15
5. the query surface for divergence-rate inspection

### 5.4 `WS-CL1-SS-AUDIT`

Artifact must lock:

1. the exact compression under review:
   - `state_{tool_category}`
2. the evaluation criteria for `blocking` vs `non-blocking`
3. which production paths use the compressed state today
4. what Stage 15 must do if the result is `blocking`
5. explicit statement that this WS writes no runtime code

## 6. Non-Negotiable Constraints

1. Stage 14 inherits Rule G through Rule W
2. Stage 14 may not turn on any user-visible routing decision from `PersistentBayesianLearner`
3. `WS-CL1-INTEG` may not "also fix" learner formula semantics
4. `WS-CL1-SCALE` must use the frozen Stage 13 SQAM method without threshold drift
5. `WS-CL1-SCALE` may not shrink into a cosmetic fixture expansion
6. `WS-CL1-SHADOW` may write only inside the existing L2 inference-cache side; no new write lane may be invented
7. `WS-CL1-SHADOW` may not emit prompt, push, evidence, or user-facing recommendation side effects
8. `WS-CL1-SS-AUDIT` may not silently become an implementation WS
9. no Stage 14 change may touch the other four continuous-learning components as rollout candidates
10. no Stage 14 change may widen Aurora write authority or dual-core write semantics

## 7. Critical Design Notes

### 7.1 `WS-CL1-INTEG` — Production Integration Coverage

This WS exists because Stage 13 left one explicit known limit:

> one router integration path still falls back to `ToolPreferenceRouter(..., redis_client=None)`

That makes any future wire-on claim structurally incomplete even if SQAM stays green.

Design rules:

1. fix injection coverage, not learner math
2. if the grep audit reveals more than `5` call sites, land a separate inventory artifact before code
3. prove the pre-fix symptom with Rule V
4. do not use this WS to justify broader router refactors

### 7.2 `WS-CL1-SCALE` — Production-Scale Proxy Rerun

This is the most important Stage 14 WS.

The Stage 13 pass is real, but it came from a small frozen fixture. Stage 14 must answer whether that pass survives a production-shaped proxy.

Design rules:

1. fixture scale must be meaningful, not padded:
   - `>=10` source states
   - `>=200` observations
   - coverage should reflect real tool-category distribution
2. use the exact same SQAM method and thresholds from Stage 13
3. freeze the fixture-expansion artifact before measurement
4. if **any** dimension falls below threshold, Path A collapses to Path B automatically
5. if all dimensions remain green, Path A survives into Stage 15

### 7.3 `WS-CL1-SHADOW` — Shadow Without User Impact

Shadow mode exists to let the system observe divergence before the first user-visible wire-on decision.

Design rules:

1. learner computes, fallback still decides
2. recorder writes only in the L2 inference-cache neighborhood
3. divergence is queryable
4. there is zero user-visible impact in Stage 14
5. Stage 14 builds the pipe, not the observation policy

### 7.4 `WS-CL1-SS-AUDIT` — Source-State Compression Audit

The secondary known limit from Stage 13 is:

> source-state compression to `state_{tool_category}` may still be too lossy for safe wire-on

This WS must answer only one thing:

> **does that compression block Stage 15 wire-on, yes or no?**

It is intentionally doc-only because the point is to make the risk explicit before Stage 15, not to smuggle a redesign into Stage 14.

## 8. Workstream Cards

### 8.1 `WS-CL1-INTEG` — Integration Repair

**Goal**

Remove the remaining `redis_client=None` production seam so the learner can actually participate across the intended integration surface.

**In-scope**

- call-site grep and inventory
- redis injection repair
- integration tests
- Rule V regression proof for fallback symptom

**Out-of-scope**

- learner formula changes
- router redesign
- shadow logic
- user-visible wiring

**Accept requires**

1. all known production call sites are classified
2. intended persistent call sites inject redis correctly
3. Rule V regression reproduces the old fallback symptom
4. integration tests cover the repaired path
5. Rule K remains green

### 8.2 `WS-CL1-SCALE` — SQAM Rerun At Production-Scale Proxy

**Goal**

Prove that the Stage 13 Rule W pass survives broader, more production-shaped measurement conditions.

**In-scope**

- fixture expansion artifact
- measurement rerun using frozen SQAM method
- explicit dimension-by-dimension reporting
- explicit Path A survival or downgrade

**Out-of-scope**

- threshold tuning
- learner redesign
- shadow runtime
- user-visible wire-on

**Accept requires**

1. artifact lands before rerun
2. fixture satisfies `>=10` source states and `>=200` observations
3. all four dimensions are reported
4. no threshold moves after seeing data
5. if any dimension regresses below threshold, handoff explicitly locks Path B

### 8.3 `WS-CL1-SHADOW` — Runtime Divergence Capture

**Goal**

Build a zero-user-impact shadow path so Stage 15 can evaluate divergence before any wire-on decision.

**In-scope**

- shadow recorder
- divergence schema
- queryability
- L2-side storage only

**Out-of-scope**

- user-visible routing
- prompt injection
- push behavior
- evidence generation
- observation policy beyond Stage 14

**Accept requires**

1. fallback still owns user-visible routing
2. learner decisions are recorded in shadow
3. divergence can be inspected
4. no user-visible path consumes shadow data
5. Rule K remains green

### 8.4 `WS-CL1-SS-AUDIT` — Source-State Compression Audit

**Goal**

Explicitly decide whether `state_{tool_category}` compression blocks Stage 15 wire-on.

**In-scope**

- audit of current compressed-state semantics
- blocking / non-blocking verdict
- Stage 15 implication text

**Out-of-scope**

- runtime implementation
- source-state redesign
- new learner logic

**Accept requires**

1. verdict is explicit: `blocking` or `non-blocking`
2. rationale cites real call paths and state semantics
3. Stage 15 implication is written clearly
4. no code changes are hidden inside this WS

## 9. Gate S14-FINAL

Stage 14 may close only if all of the following are true:

1. Stage 12 frozen baseline still replays green
2. Rule V regression suite still replays green
3. Rule K guard remains `35 / 0`
4. Stage 13 backend and mobile sweeps still replay green unless intentionally superseded by tighter Stage 14 suites
5. `WS-CL1-INTEG` proves the old fallback symptom and its removal
6. `WS-CL1-SCALE` reports all four dimensions under the frozen Stage 13 SQAM method
7. `WS-CL1-SHADOW` proves zero user-visible impact and queryable divergence capture
8. `WS-CL1-SS-AUDIT` lands with an explicit verdict
9. handoff locks the exact Stage 15 fork: `Path A-on`, `Path A-blocked`, or `Path B`

## 10. Stage 15 Entry Logic

Stage 14 must leave Stage 15 with one of three explicit forks:

| Condition | Stage 15 entry |
| --- | --- |
| `WS-CL1-SCALE` stays green, `WS-CL1-INTEG` is repaired, `WS-CL1-SHADOW` is ready, and `WS-CL1-SS-AUDIT` is `non-blocking` | **Path A-on**: bounded `WS-CL1` wire-on design may begin |
| `WS-CL1-SCALE` regresses on any dimension | **Path B**: return to root repair; no wire-on design |
| `WS-CL1-SCALE` stays green but `WS-CL1-SS-AUDIT` is `blocking` | **Path A-blocked**: wire-on remains deferred until source-state redesign is handled |

## 11. Explicit Non-Goals Reminder

1. do not actually wire the learner into user-visible decisions
2. do not broaden to the other four continuous-learning components
3. do not add a user-facing WS for Stage 14
4. do not expand evidence types
5. do not modify prompts.py rendering
6. do not widen Aurora write semantics
7. do not create a new rule
8. do not let `WS-CL1-SHADOW` leak into any user-facing signal
