#!/bin/bash
set -euo pipefail

cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_skill_schema_contract.py \
  tests/unit/test_skill_store_service.py \
  tests/unit/test_skill_extract_service.py \
  tests/unit/test_skill_selection_service.py \
  tests/unit/test_skill_selection_aggregator_integration.py \
  tests/unit/test_skill_share_service.py \
  tests/unit/test_stage21_kill_switch.py \
  tests/unit/test_skills_api.py \
  tests/unit/test_memory_admin_api.py \
  tests/unit/test_route_history_service.py \
  tests/unit/test_route_history_performance.py \
  tests/unit/test_user_state_schema_contract.py \
  tests/unit/test_working_memory_aggregator_integration.py \
  -q
cd ../mobile && flutter test \
  test/core/models/skill_models_test.dart \
  test/features/user/presentation/screens/skill_management_screen_test.dart \
  test/app/skill_management_route_test.dart
cd ..

make proto-gen
python3 scripts/check_rule_k_write_paths.py
python3 scripts/check_rule_ab_aggregator_integrity.py
python3 scripts/check_rule_ac_working_memory.py
python3 scripts/check_rule_af_skill_share_isolation.py
python3 scripts/check_rule_af_skill_pii_pipeline.py
python3 scripts/check_skill_extract_trigger_purity.py
python3 scripts/check_route_history_skill_field.py
test -f docs/product/SPARKLE_AURORA_STAGE21_RULE_AF_DEFINITION_2026-04-21.md
test -f docs/product/SPARKLE_AURORA_STAGE21_HANDOFF_2026-04-21.md

echo "[Gate S21-FINAL] ✅ ALL CHECKS PASSED"
