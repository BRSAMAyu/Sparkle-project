#!/bin/bash
set -euo pipefail

cd backend && ./.venv/bin/python -m pytest \
  tests/test_context_manager.py \
  tests/unit/test_prompt_signal_closure.py \
  tests/unit/test_state_aggregator_service.py \
  tests/unit/test_user_state_schema_contract.py \
  tests/unit/test_working_memory_aggregator_integration.py \
  tests/unit/test_error_replan_bridge.py \
  tests/unit/test_intervention_strategy_learner.py \
  tests/unit/test_seed_library_stage22.py \
  tests/unit/test_persistent_bayesian_learner_contract.py \
  tests/unit/test_multi_dimensional_learner_contract.py \
  tests/unit/test_distilled_strategy_store_contract.py \
  -q
cd ../mobile && flutter test \
  test/features/achievement/data/repositories/achievement_repository_test.dart \
  test/features/achievement/presentation/providers/achievement_provider_test.dart \
  test/features/calendar/data/models/calendar_event_model_test.dart \
  test/features/seed_library/presentation/providers/seed_library_provider_test.dart
cd ..

python3 scripts/check_prompt_render_coverage.py --write
python3 scripts/check_error_replan_trigger_purity.py
python3 scripts/check_rule_ab_aggregator_integrity.py
python3 scripts/render_stage22_precheck.py

test -f docs/product/stage22_precheck.md
test -f docs/product/stage22_prompt_coverage_baseline.md

if rg -n "achievement_summary|calendar_context" backend/app/orchestration/routing_engine.py backend/app/agents 2>/dev/null; then
  echo "[Gate S22-FINAL] forbidden router read detected"
  exit 1
fi
if rg -n "openai|anthropic|llm" backend/app/services/error_replan_bridge.py; then
  echo "[Gate S22-FINAL] forbidden trigger impurity detected"
  exit 1
fi
if rg -n "achievement_engine" backend/app | rg "tool_call|tool call"; then
  echo "[Gate S22-FINAL] forbidden AI->achievement write path detected"
  exit 1
fi

echo "[Gate S22-FINAL] ✅ ALL CHECKS PASSED"
