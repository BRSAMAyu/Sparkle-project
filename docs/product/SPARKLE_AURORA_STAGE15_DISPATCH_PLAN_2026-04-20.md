# SPARKLE Aurora Stage 15 Dispatch Plan (2026-04-20)

> **Status**: Stage 15 dispatch baseline v0 after Stage 14 final-accept
> **Authority**: [SPARKLE_AURORA_STAGE14_HANDOFF_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE14_HANDOFF_2026-04-20.md) is the only Stage 14 truth source; this plan starts from that frozen baseline and must not reopen completed Stage 5 through Stage 14 work.
> **Depends on**:
> - [SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md)
> - [SPARKLE_AURORA_STAGE14_HANDOFF_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE14_HANDOFF_2026-04-20.md)
> - [SPARKLE_AURORA_STAGE14_CL1_SS_AUDIT_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE14_CL1_SS_AUDIT_2026-04-20.md)
> - [SPARKLE_AURORA_STAGE14_PERSISTENT_BAYESIAN_SQAM_SCALE_RERUN_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE14_PERSISTENT_BAYESIAN_SQAM_SCALE_RERUN_2026-04-20.md)
> **Scope**: Stage 15 execution design. Resolves `Path A-blocked` by taking the narrowest reversible fork: a claim-narrowed, within-category preference wire-on candidate for `PersistentBayesianLearner` only.

## 0. Stage 15 Positioning

Stage 14 ended with an intentionally asymmetric conclusion:

1. `PersistentBayesianLearner` is integrated cleanly
2. the Stage 13 SQAM pass survives a much larger frozen proxy fixture
3. zero-user-impact shadow plumbing now exists
4. but current `state_{tool_category}` compression remains too lossy for the broader Stage 15 wire-on claim that would normally follow

### One-sentence definition

**Stage 15 is the stage where Sparkle tries to turn `Path A-blocked` into one bounded, truthfully narrower user-visible path by shrinking the product claim to within-category tool preference and proving the disclosure + rollback contract before any wider claim is allowed.**

### Why Stage 15 takes the narrow fork

Stage 14 left three logical exits:

1. wide route: source-state redesign
2. narrow route: claim-scope narrowing
3. downgrade route: return to Path B / other components

Stage 15 takes the **narrow route** because it is:

1. the smallest reversible fork
2. the only fork that preserves the validated Stage 14 integration / scale / shadow work without pretending SS-AUDIT disappeared
3. the least likely to reopen architecture already frozen by Stage 14

### What Stage 15 must treat as already settled

1. Stage 14 final-accept is frozen and valid
2. `PersistentBayesianLearner` remains the only component eligible for bounded user-visible consideration
3. `WS-CL1-SS-AUDIT` remains `blocking` unless the claim itself is formally narrowed
4. Stage 14 shadow plumbing exists but does not yet define a production observation window
5. no other continuous-learning component inherits any Stage 14 pass

### Orphan Product-Doc Adjudication

The untracked file:

- `docs/product/SPARKLE_ADVANCED_CONCEPTS_INTEGRATION_ANALYSIS_2026-04-19.md`

is explicitly adjudicated as:

- **out-of-band user-local scratch analysis**

Hard interpretation:

1. it is **not** a Stage 15 truth source
2. it is **not** a Stage 15 artifact
3. it will not be cited by Stage 15 closure claims
4. Stage 15 proceeds without adopting, deleting, or rewriting it

This satisfies the Stage 14 final-accept requirement that the file's ownership be made explicit before Stage 15 begins.

### Explicit non-goals

1. no source-state redesign in Stage 15
2. no reinterpretation of SS-AUDIT as a soft suggestion
3. no work on `PromptBandit`, `distiller`, `multi_dimensional_learner`, or `strategy_store`
4. no evidence-type expansion
5. no prompt-language overclaim about workflow understanding
6. no new governance rule

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

Stage 15 does **not** add a new rule. The narrow claim is enforced through Stage 15 artifacts, UI disclosure, tests, and handoff wording, not through a new constitutional letter.

### Semantic-gate interpretation

Stage 15 inherits a new practical doctrine from Stage 14:

> passing the quantitative gate is necessary but not sufficient if the surviving signal cannot truthfully support the user-visible claim being made.

Hard interpretation:

1. SQAM still governs signal quality
2. the narrowed claim amendment governs what Stage 15 is even allowed to say
3. any code path that implies more than "within-category preference" is automatically out of scope

## 2. Stage 15 Scope

| ID | Goal | Boundary | Exit condition |
| --- | --- | --- | --- |
| `Gate S15-0` | replay frozen baseline and lock the narrow-claim fork before code | verification + dispatch truth-lock only | Stage 14 baseline replay is recorded and Stage 15 narrow-claim amendment is frozen before code |
| `WS-CL1-CLAIM` | define the exact user-visible claim Stage 15 is allowed to make | docs-only amendment | claim text is explicit, narrower than Stage 14 blocking scope, and names what is still **not** claimed |
| `WS-CL1-DISCLOSE` | define the user-facing caveat and rollout surface contract | docs + UX contract only | user-facing wording, placement, fallback wording, and no-overclaim red lines are frozen |
| `WS-CL1-WIRE-NARROW` | implement one bounded within-category preference read path for `PersistentBayesianLearner` | one user-visible path only; fallback remains available | feature-flagged wire-on lands with rollback posture and no overclaim beyond the narrowed contract |
| `WS-CL1-OBSERVE` | define and use a bounded observation/rollback gate over the Stage 14 shadow pipe | observation + rollout guard only | divergence guard, rollback trigger, and inspection path are wired to the narrow rollout |
| `Gate S15-FINAL` | close Stage 15 with reruns and next fork lock | verification-only | Stage 15 proof is green and next-stage fork is explicitly locked |

### Explicitly deferred beyond Stage 15

1. source-state redesign
2. broader "workflow understanding" learner claims
3. measuring the other four continuous-learning components under SQAM
4. graph diagnostic deepening
5. evidence-type expansion

## 3. Wave Order

`Gate S15-0 -> WS-CL1-CLAIM -> WS-CL1-DISCLOSE -> (WS-CL1-WIRE-NARROW || WS-CL1-OBSERVE) -> Gate S15-FINAL`

Hard interpretation:

1. `WS-CL1-CLAIM` must land before any code because it is the semantic fence for Stage 15
2. `WS-CL1-DISCLOSE` must land before wire-on because the user-visible wording is part of the safety contract
3. `WS-CL1-OBSERVE` may run in parallel with bounded wire-on implementation once the disclosure contract is frozen
4. if implementation pressure widens the claim beyond "within-category preference," Stage 15 collapses back to the wide route and stops

## 4. Gate S15-0 Requirements

Stage 15 may not enter `WS-CL1-CLAIM` until the following are replayed and recorded:

1. Stage 12 frozen baseline:
   - `144 passed`
2. Rule V regression suite:
   - `8 passed`
3. Rule K guard:
   - `35 files / 0 violation`
4. Stage 13 backend sweep:
   - `24 passed`
5. Stage 13 mobile sweep:
   - `50 tests passed`
6. Stage 14 targeted backend sweep:
   - `23 passed`

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
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_router_node_learning_integration.py \
  tests/unit/test_tool_preference_router.py \
  tests/unit/test_persistent_bayesian_sqam_scale.py \
  tests/unit/test_persistent_bayesian_learner_contract.py \
  tests/unit/test_multi_dimensional_learner_contract.py \
  tests/unit/test_distilled_strategy_store_contract.py \
  -q
```

## 5. Workstream Artifacts That Must Land Before Code

### 5.1 `WS-CL1-CLAIM`

Artifact must lock:

1. the one exact Stage 15 user-visible claim
2. three things Stage 15 explicitly does **not** claim
3. the one bounded path where that claim may appear
4. the fallback wording if no stable within-category preference exists

### 5.2 `WS-CL1-DISCLOSE`

Artifact must lock:

1. the user-facing caveat text
2. where the caveat appears
3. when the caveat must be hidden because the feature is not active
4. a "forbidden language" list that would imply workflow understanding, cross-step memory, or broader personalization than Stage 15 actually has

### 5.3 `WS-CL1-WIRE-NARROW`

Artifact must lock:

1. the exact read path that becomes user-visible
2. the feature-flag name and default state
3. the rollback trigger surface
4. the fallback path when the learner has no stable within-category signal
5. the Rule U proof points for any new visible affordance

### 5.4 `WS-CL1-OBSERVE`

Artifact must lock:

1. the bounded observation window shape
2. divergence thresholds that trigger rollback or auto-disable
3. the internal query surface for recent divergence inspection
4. explicit statement that shadow records remain outside prompt / push / evidence / front-door payloads

## 6. Non-Negotiable Constraints

1. Stage 15 inherits Rule G through Rule W
2. Stage 15 may not silently widen the Stage 15 claim beyond within-category preference
3. `WS-CL1-WIRE-NARROW` may not smuggle in source-state redesign
4. `WS-CL1-WIRE-NARROW` may not imply workflow understanding, recovery-state understanding, or multi-step semantic intent understanding
5. Stage 15 may not touch the other four continuous-learning components as rollout candidates
6. Stage 15 may not widen Aurora write authority or dual-core write semantics
7. Stage 15 may use the Stage 14 shadow pipe only as an observation guard, not as a user-visible evidence source
8. If caveat text is removed, hidden, or bypassed, Stage 15 is invalid

## 7. Critical Design Notes

### 7.1 `WS-CL1-CLAIM` — Narrowing By Amendment, Not By Wishful Thinking

This WS exists because Stage 14 already proved the broader claim unsafe.

The amendment must therefore do two things at once:

1. explicitly permit the narrower claim
2. explicitly prohibit the old broader inference from sneaking back in via copy, prompt text, or UI labels

### 7.2 `WS-CL1-DISCLOSE` — Caveat Text Is Part Of The Safety Mechanism

For this fork, disclosure is not marketing garnish.
It is part of the semantic safety boundary.

If the user-visible text suggests:

1. context understanding
2. workflow understanding
3. cross-step personalized orchestration

then the system is overclaiming what the current source-state encoding can support.

### 7.3 `WS-CL1-WIRE-NARROW` — One Bounded Read Path Only

Stage 15 should turn on exactly one bounded path.

Do not spread the same signal into:

1. prompt rendering
2. evidence cards
3. multiple route surfaces
4. push generation

The first goal is not "use the learner everywhere."
The first goal is "prove one truthful path can exist without semantic drift."

### 7.4 `WS-CL1-OBSERVE` — Stage 14 Shadow Becomes A Rollback Guard

Stage 14 built the pipe.
Stage 15 may define:

1. how long the pipe is watched
2. what divergence rate is acceptable
3. when the narrow path auto-disables

It still may not convert shadow data into a user-facing artifact.

## 8. Workstream Cards

### 8.1 `WS-CL1-CLAIM` — Narrow Claim Amendment

**Goal**

Define the one truthful user-visible claim that current source-state compression can support.

**In-scope**

- claim amendment doc
- positive claim text
- negative claim boundaries

**Out-of-scope**

- source-state redesign
- runtime code
- rollout logic

**Accept requires**

1. claim is explicit and testable
2. the "not claimed" list is explicit
3. Stage 14 blocking concern is addressed rather than ignored

### 8.2 `WS-CL1-DISCLOSE` — User-Facing Caveat Contract

**Goal**

Freeze the exact disclosure and no-overclaim wording for the narrow wire-on path.

**In-scope**

- user-facing wording
- placement contract
- forbidden-language list

**Out-of-scope**

- source-state redesign
- broader UX refactor

**Accept requires**

1. caveat text is explicit
2. caveat placement is explicit
3. forbidden language is explicit

### 8.3 `WS-CL1-WIRE-NARROW` — Bounded Within-Category Wire-On

**Goal**

Implement one feature-flagged user-visible path that uses `PersistentBayesianLearner` only for within-category preference.

**In-scope**

- one bounded read path
- feature flag
- fallback path
- tests for activation and fallback

**Out-of-scope**

- source-state redesign
- prompt-wide personalization
- evidence expansion
- push integration

**Accept requires**

1. only one path uses the learner user-visibly
2. feature can be disabled cleanly
3. fallback remains intact
4. no code path implies more than within-category preference

### 8.4 `WS-CL1-OBSERVE` — Rollout Observation Guard

**Goal**

Use the Stage 14 shadow infrastructure as a bounded rollback guard for the narrow path.

**In-scope**

- observation-window definition
- divergence threshold
- auto-disable / rollback rule
- inspection helpers

**Out-of-scope**

- user-visible shadow data
- new evidence or prompt behavior

**Accept requires**

1. divergence threshold is explicit
2. rollback path is explicit
3. no user-visible path consumes shadow records

## 9. Gate S15-FINAL

Stage 15 may close only if all of the following are true:

1. Stage 12 frozen baseline still replays green
2. Rule V regression suite still replays green
3. Rule K guard remains `35 / 0`
4. Stage 13 backend and mobile sweeps still replay green unless intentionally superseded by tighter Stage 15 suites
5. Stage 14 targeted backend sweep still replays green
6. `WS-CL1-CLAIM` lands with an explicit narrower claim
7. `WS-CL1-DISCLOSE` lands with explicit caveat text and forbidden-language list
8. `WS-CL1-WIRE-NARROW` proves one bounded path and one bounded fallback
9. `WS-CL1-OBSERVE` lands with explicit rollback thresholds and no user-visible leakage

## 10. Stage 16 Entry Logic

Stage 15 must leave Stage 16 with one of three explicit forks:

| Condition | Stage 16 entry |
| --- | --- |
| narrow claim holds, caveat is explicit, bounded wire-on is stable, and rollback guard stays healthy | **Path N-on**: continue bounded rollout / cohort validation under the narrow claim |
| bounded wire-on is technically stable but the caveat / claim proves too weak or too awkward to defend | **Path W**: source-state redesign route |
| bounded wire-on fails technically or semantically under its own narrowed contract | **Path B**: stop the Bayesian front-door path and return to root repair or alternative-component measurement |

## 11. Explicit Non-Goals Reminder

1. do not redesign source-state in Stage 15
2. do not pretend Stage 14 blocking vanished
3. do not broaden to the other four continuous-learning components
4. do not add evidence types
5. do not widen prompt personalization claims
6. do not create a new rule
7. do not cite the out-of-band advanced-concepts scratch doc as Stage 15 authority
