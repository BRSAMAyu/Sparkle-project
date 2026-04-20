# SPARKLE Aurora Stage 12 Gate S12-0 Baseline Report (2026-04-20)

> **Status**: Gate S12-0 baseline replay artifact
> **Purpose**: freeze the exact Stage 11 validation baseline that Stage 12 must preserve before any substrate repair work begins.

## 1. Frozen Baseline Commands

### 1.1 Stage 11 frozen baseline

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

- Result: `144 passed in 10.53s`

### 1.2 Stage 11 backend sweep

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/profile/eval/test_profile_eval_runner.py \
  tests/profile/eval/test_profile_eval_llm_judge.py \
  tests/unit/test_ai_ops_dashboard.py \
  tests/unit/test_stage9_utilization_metrics.py \
  -q
```

- Result: `14 passed in 2.59s`

### 1.3 Stage 11 mobile sweep

```bash
cd mobile && flutter test \
  test/widget/evidence_card_navigation_test.dart \
  test/features/memory/presentation/widgets/evidence_cards_test.dart \
  test/widget/profile_front_door_action_card_test.dart \
  test/widget/ai_ops_analysis_screen_test.dart
```

- Result: `51 tests passed`

### 1.4 Rule K guard

```bash
backend/.venv/bin/python scripts/check_rule_k_write_paths.py
```

- Result: `✅ Rule K write-path guard passed (35 files scanned)`

## 2. Gate Verdict

`Gate S12-0` baseline is replayed and clean.

Stage 12 may start only if all subsequent work preserves:

1. frozen baseline `144 passed`
2. Stage 11 backend sweep `14 passed`
3. Stage 11 mobile sweep `51 tests passed`
4. Rule K guard `35 / 0`
