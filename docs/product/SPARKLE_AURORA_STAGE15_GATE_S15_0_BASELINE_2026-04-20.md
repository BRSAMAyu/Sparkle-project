# SPARKLE Aurora Stage 15 Gate S15-0 Baseline (2026-04-20)

> **Purpose**: freeze the replay checks and Stage 15 entry truth-lock before any Stage 15 code work may start.
> **Authority**: `SPARKLE_AURORA_STAGE15_DISPATCH_PLAN_2026-04-20.md`

## 1. Replay Results

| Check | Command Scope | Result |
| --- | --- | --- |
| Stage 12 frozen baseline | Stage 12 carry-forward backend subset | `144 passed in 11.80s` |
| Rule V regression suite | continuous-learning contract guards | `8 passed in 2.91s` |
| Rule K guard | write-path static guard | `35 files scanned / 0 violation` |
| Stage 13 backend sweep | Stage 13 carry-forward backend surface | `24 passed in 6.05s` |
| Stage 13 mobile sweep | Stage 13 carry-forward widget routing proof | `50 tests passed` |
| Stage 14 targeted backend sweep | Stage 14 narrow pre-wire runtime prep surface | `23 passed in 3.62s` |

## 2. Commands Replayed

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

```bash
cd mobile && flutter test \
  test/widget/evidence_card_navigation_test.dart \
  test/features/memory/presentation/widgets/evidence_cards_test.dart
```

## 3. Stage 15 Entry Truth-Lock

The Stage 15 fork is explicitly frozen as:

- narrow route only

Hard interpretation:

1. Stage 15 does **not** reopen Stage 14 `Path A-blocked`
2. Stage 15 proceeds only by narrowing the user-visible claim to within-category preference
3. the untracked file `SPARKLE_ADVANCED_CONCEPTS_INTEGRATION_ANALYSIS_2026-04-19.md` remains out-of-band scratch and is not cited as Stage 15 authority

## 4. Gate Verdict

`Gate S15-0` is open. Stage 15 may proceed to `WS-CL1-CLAIM`.
