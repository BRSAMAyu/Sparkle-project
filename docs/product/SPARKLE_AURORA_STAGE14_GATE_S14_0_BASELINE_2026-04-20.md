# SPARKLE Aurora Stage 14 Gate S14-0 Baseline (2026-04-20)

> **Purpose**: freeze the replay checks required before any Stage 14 workstream may start.
> **Authority**: `SPARKLE_AURORA_STAGE14_DISPATCH_PLAN_2026-04-20.md`

## 1. Replay Results

| Check | Command Scope | Result |
| --- | --- | --- |
| Stage 12 frozen baseline | Stage 12 carry-forward backend subset | `144 passed in 13.21s` |
| Rule V regression suite | continuous-learning contract guards | `8 passed in 3.46s` |
| Rule K guard | write-path static guard | `35 files scanned / 0 violation` |
| Stage 13 backend sweep | Stage 13 carry-forward backend surface | `23 passed in 7.39s` |
| Stage 13 mobile sweep | Stage 13 carry-forward widget routing proof | `50 tests passed` |

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
cd mobile && flutter test \
  test/widget/evidence_card_navigation_test.dart \
  test/features/memory/presentation/widgets/evidence_cards_test.dart
```

## 3. Interpretation

1. Stage 14 starts from the accepted Stage 13 freeze without reopening Stage 13 defects.
2. Rule V remains green before Stage 14 touches the only allowed continuous-learning component.
3. Rule K remains stable at `35 / 0`, so Stage 14 begins with no write-lane regression debt.
4. The Stage 13 backend and mobile proof points still hold before any Stage 14 integration or shadow work starts.

## 4. Gate Verdict

`Gate S14-0` is open. Stage 14 may proceed to `WS-CL1-INTEG`.
