# SPARKLE Aurora Stage 14 Handoff (2026-04-20)

> **Status**: engineering closeout baseline after autonomous Stage 14 execution
> **Purpose**: record the final landed Stage 14 workstreams, verification evidence, carried-forward limits, and the locked Stage 15 entry fork.

## 1. Final Accept Matrix

| Workstream | Status | Notes |
| --- | --- | --- |
| `Gate S14-0` | accept | frozen baseline replay, Rule V, Rule K, Stage 13 backend sweep, and Stage 13 mobile sweep were replayed before code |
| `WS-CL1-INTEG` | accept | `RouterNode` no longer hardcodes `ToolPreferenceRouter(..., redis_client=None)`; regression proof now guards the old fallback symptom |
| `WS-CL1-SCALE` | accept | frozen Stage 14 proxy fixture (`11` states / `220` observations) keeps all four SQAM dimensions green under the same Stage 13 method |
| `WS-CL1-SS-AUDIT` | accept | source-state compression verdict is explicitly `blocking` for current Stage 15 wire-on |
| `WS-CL1-SHADOW` | accept | shadow recorder lands in L2-side Redis namespace, divergence is queryable, and fallback still owns user-visible routing under shadow mode |
| `Gate S14-FINAL` | accept | frozen baseline remains green, Rule V / Rule K remain green, and Stage 15 fork is explicitly locked |

## 2. What Stage 14 Actually Achieved

Stage 14 did exactly what Path A was allowed to do and no more.

It proved that:

1. the surviving Bayesian learner path is now integrated cleanly at the remaining broken seam
2. the Stage 13 SQAM pass survives a much larger frozen proxy fixture
3. learner-vs-fallback divergence can be captured without changing the user-visible route

It also proved something equally important:

4. current `state_{tool_category}` compression is still too lossy for a truthful Stage 15 wire-on claim

So Stage 14 ends with better evidence and cleaner plumbing, but still with a blocked wire-on fork.

## 3. Verification Evidence

### Gate S14-0 replay

- Stage 12 frozen baseline: `144 passed in 13.21s`
- Rule V regression suite: `8 passed in 3.46s`
- Rule K guard: `35 files scanned / 0 violation`
- Stage 13 backend sweep: `23 passed in 7.39s`
- Stage 13 mobile sweep: `50 tests passed`

### Gate S14-FINAL replay

- Stage 12 frozen baseline: `144 passed in 13.40s`
- Rule V regression suite: `8 passed in 5.42s`
- Rule K guard: `35 files scanned / 0 violation`
- Stage 13 backend sweep: `24 passed in 8.56s`
- Stage 13 mobile sweep: `50 tests passed`

### Stage 14 targeted backend sweep

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

- Stage 14 targeted backend sweep: `23 passed`

### Scale rerun

Locked in:

- `ID1 = 1.00`
- `ST1 = 1.00`
- `DP1 = 1.00`
- `SM1 = 1.00`

Authority:

- `SPARKLE_AURORA_STAGE14_PERSISTENT_BAYESIAN_SQAM_SCALE_RERUN_2026-04-20.md`

## 4. Representative Samples

### 4.1 Scale rerun top-1 sample

```json
{
  "source_state": "state_plan",
  "top_choice": "generate_tasks_for_plan",
  "probability": 0.923,
  "effective_user_outcome": true
}
```

### 4.2 Shadow divergence sample

```json
{
  "source_state": "state_plan",
  "fallback_choice": "fallback_tool",
  "learner_choice": "learner_tool",
  "diverged": true
}
```

## 5. Known Limits Carried Forward

1. `state_{tool_category}` compression remains a blocking limit for wire-on.
2. Stage 14 lands shadow plumbing only; it does not define a production observation window.
3. Stage 14 still does not wire `PersistentBayesianLearner` into a new user-visible decision path.
4. The other four continuous-learning components remain outside any wire-ready or wire-safe claim.
5. `practice_outcome` remains the last user-visible evidence addition; Stage 14 intentionally adds no new evidence type.

## 6. Hard Constraints Inherited Forward

1. Rule K remains hard: no fact writes outside the allowed layered lanes.
2. Rule U remains hard: any claimed clickable path requires widget-level proof or known-limit disclosure.
3. Rule V remains hard: audit-driven repairs require regression tests that reproduce the audited symptom.
4. Rule W remains hard: no continuous-learning component may enter a user-visible decision path unless all four SQAM dimensions meet threshold.
5. Stage 15 may not reinterpret the Stage 14 `blocking` audit as a soft suggestion.

## 7. Stage 15 Entry Path

Stage 14 locks the Stage 15 fork as:

- `Path A-blocked`

Why:

1. `WS-CL1-SCALE` stays green
2. `WS-CL1-INTEG` is repaired
3. `WS-CL1-SHADOW` is ready
4. but `WS-CL1-SS-AUDIT` is explicitly `blocking`

That means Stage 15 may not start bounded wire-on design yet.

It must first resolve one of:

1. source-state redesign
2. or a separately accepted Stage 15 narrowing that truthfully limits the user claim to within-category preference only
