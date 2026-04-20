# SPARKLE Aurora Stage 13 Handoff (2026-04-20)

> **Status**: engineering closeout baseline after autonomous Stage 13 execution
> **Purpose**: record the final landed Stage 13 workstreams, verification evidence, carried-forward limits, and the frozen Stage 14 entry path.

## 1. Final Accept Matrix

| Workstream | Status | Branch-tip commit | Notes |
| --- | --- | --- | --- |
| `Gate S13-0` | accept | `96344522` | Stage 12 frozen baseline, Rule V suite, and Rule K guard were replayed and recorded before Stage 13 work began |
| `WS-SQ-METHOD` | accept | `99c6324a` | SQAM now defines four computable dimensions, fixed thresholds, fallback rules, and a worked example |
| `WS-SQ-MEASURE` | accept | `96e73e74` | `PersistentBayesianLearner` baseline measured at `ID1=1.00`, `ST1=1.00`, `DP1=0.33`, `SM1=0.33`; top shortfall locked to reward-label fidelity |
| `Wave 2 artifacts` | accept | `9aa55158` | `WS-SQ-FEED` and `WS-EVD3-LITE` scope locks landed before any code changes |
| `WS-SQ-FEED` | accept | `92f4ad07` | tool-preference learning now prefers `was_helpful` / `user_satisfaction` over raw execution success |
| `WS-EVD3-LITE` | accept | `bf84f891` | `practice_outcome` memory evidence now exists end to end: review write, resolve payload, front-door legibility, and widget route proof |
| `Gate S13-FINAL` | accept | `pending this handoff commit` | frozen baseline remains green, Rule V / Rule K remain green, SQAM rerun upgrades `PersistentBayesianLearner` to `wire-ready` under Rule W |

## 2. What Stage 13 Actually Achieved

Stage 13 is the first stage that turned "should this learning component ever become user-visible?" into a measurable governance question. Instead of adding another shiny surface on top of weak learning signals, it defined SQAM, measured one repaired component against it, and forced the repair to answer the measured shortfall rather than intuition.

From the product side, Stage 13 still shipped one bounded user-visible improvement: reviewed error-book items can now surface as `practice_outcome` evidence cards that route back into the existing error-book detail flow. That kept momentum without pretending continuous learning was already front-door ready.

## 3. Verification Evidence

### Stage 12 frozen baseline re-run

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

- Stage 12 frozen baseline: `144 passed`

### Rule V regression suite re-run

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_persistent_bayesian_learner_contract.py \
  tests/unit/test_multi_dimensional_learner_contract.py \
  tests/unit/test_distilled_strategy_store_contract.py \
  -q
```

- Rule V regression suite: `8 passed`

### Rule K guard

```bash
./backend/.venv/bin/python scripts/check_rule_k_write_paths.py
```

- Rule K guard: `✅ Rule K write-path guard passed (35 files scanned)`

### Stage 13 backend sweep

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_tool_preference_router.py \
  tests/unit/test_evidence_resolve.py \
  tests/tools/test_growth_tools.py \
  -q
```

- Stage 13 backend sweep: `23 passed`

### Stage 13 mobile sweep

```bash
cd mobile && flutter test \
  test/widget/evidence_card_navigation_test.dart \
  test/features/memory/presentation/widgets/evidence_cards_test.dart
```

- Stage 13 mobile sweep: `50 tests passed`

### SQAM rerun

Locked in:

- `ID1 = 1.00`
- `ST1 = 1.00`
- `DP1 = 1.00`
- `SM1 = 1.00`

Rerun authority:

- `SPARKLE_AURORA_STAGE13_PERSISTENT_BAYESIAN_SQAM_RERUN_2026-04-20.md`

## 4. Representative Samples

### 4.1 SQAM baseline vs rerun

```json
{
  "baseline": {"ID1": 1.0, "ST1": 1.0, "DP1": 0.33, "SM1": 0.33},
  "rerun": {"ID1": 1.0, "ST1": 1.0, "DP1": 1.0, "SM1": 1.0},
  "top_shortfall": "reward_label_fidelity_collapse"
}
```

### 4.2 `practice_outcome` payload

Representative evidence-resolve output now looks like:

```json
{
  "type": "practice_outcome",
  "id": "err-reviewed",
  "status": "ok",
  "practice_outcome": {
    "error_id": "err-reviewed",
    "subject_code": "math",
    "review_performance": "remembered",
    "mastery_level": 0.7,
    "review_count": 1,
    "summary": "错题复习结果：remembered，掌握度 0.00 → 0.15。"
  }
}
```

### 4.3 Front-door legibility sample

Representative profile front door evidence structure now includes:

```json
{
  "evidence_legend": [
    {"id": "compiled_claim"},
    {"id": "prediction"},
    {"id": "practice_outcome"},
    {"id": "user_correction"}
  ],
  "claim_evidence_refs": [
    {"type": "practice_outcome", "id": "err-reviewed", "schema_version": "practice_outcome.v1"},
    {"type": "error", "id": "err-reviewed", "schema_version": "error.v1"}
  ]
}
```

## 5. Rule-G Chain

- `42682d1c` `docs(stage13): add dispatch plan for signal quality gating`
- `689cde3d` `docs(stage13): dispatch plan v1 incorporate review addenda`
- `96344522` `docs(stage13): record Gate S13-0 baseline replay`
- `99c6324a` `docs(stage13): land WS-SQ-METHOD signal quality audit method`
- `96e73e74` `docs(stage13): land WS-SQ-MEASURE persistent learner baseline`
- `9aa55158` `docs(stage13): add Wave 2 fix and evidence artifacts`
- `92f4ad07` `feat(stage13): land WS-SQ-FEED reward label fidelity repair`
- `bf84f891` `feat(stage13): land WS-EVD3-LITE practice outcome evidence`

## 6. Known Limits Carried Forward

1. Only `PersistentBayesianLearner` was measured under SQAM in Stage 13; the other four continuous-learning components remain outside any wire-ready claim.
2. `WS-SQ-FEED` repaired reward-label fidelity only; source-state compression to `state_{tool_category}` remains a secondary shortfall.
3. One router integration path still falls back to `ToolPreferenceRouter(..., redis_client=None)`, so persistent learner usage is not yet universal across the codebase.
4. `practice_outcome` is intentionally a lite evidence addition: it routes into the existing error detail surface and does not deepen graph or learning behavior.
5. tokenizer-aware inline budget precision (`RB1`) remains deferred.
6. graph diagnostic deepening beyond the current Stage 10 / 11 surface remains deferred.
7. dual interaction mode formalization remains deferred.

## 7. Hard Constraints Inherited Forward

1. Rule K remains hard: no fact writes outside the allowed layered lanes.
2. Rule L remains hard: closure claims require a real consumer or runner path.
3. Rule M remains hard: no third compiler may emerge.
4. Rule N remains hard: a failing Rule K CI guard is merge-blocking.
5. Rule O remains hard: bounded steering allowlists must not expand silently.
6. Rule P remains hard: chat-originated profile correction must stay in the User Correction lane.
7. Rule Q remains hard: evidence class must remain legible.
8. Rule R remains hard: evaluator outputs stay inside `evaluation_records_only`.
9. Rule S remains hard: LLM-judge outputs remain isolated and gracefully degradable.
10. Rule T remains hard: graph-as-diagnostic must remain read-only unless explicitly reauthorized.
11. Rule U remains hard: any claimed clickable path requires widget-level proof or explicit known-limit disclosure.
12. Rule V remains hard: audit-driven repairs require regression tests that reproduce the audited symptom.
13. Rule W remains hard: no continuous-learning component may enter a user-visible decision path unless all four SQAM dimensions meet threshold.

## 8. Stage 14 Entry Path

Stage 13 upgrades the next-stage fork from Stage 12 Path C to a more precise Rule W outcome:

1. `PersistentBayesianLearner` is now `wire-ready` under the frozen Stage 13 SQAM method
2. therefore Stage 14 may take **Path A**:
   - propose a bounded `WS-CL1` candidate for `PersistentBayesianLearner` only
3. no such claim is made for `PromptBandit`, `distiller`, `multi_dimensional_learner`, or `strategy_store`
4. if Stage 14 wants broader continuous-learning wiring, it must measure those components under SQAM first instead of inheriting the Bayesian learner's pass
