#!/bin/bash
set -euo pipefail

cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_working_memory_schema_contract.py \
  tests/unit/test_working_memory_service.py \
  tests/unit/test_llm_extractor_service.py \
  tests/unit/test_working_memory_consolidation.py \
  tests/unit/test_working_memory_aggregator_integration.py \
  tests/unit/test_user_state_schema_contract.py \
  tests/unit/test_state_aggregator_service.py \
  tests/unit/test_aggregator_backed_social_context_provider.py \
  tests/unit/test_stage19_kill_switch.py \
  tests/unit/test_memory_working_memory_api.py \
  tests/unit/test_memory_inferred_write_lane.py \
  tests/unit/test_memory_admin_api.py \
  -q
cd ..

make proto-gen
python3 scripts/check_rule_ac_working_memory.py
python3 scripts/check_rule_ab_aggregator_integrity.py
./backend/.venv/bin/python scripts/check_rule_k_write_paths.py
test -f docs/product/SPARKLE_AURORA_STAGE19_RULE_AC_DEFINITION_2026-04-21.md
test -f docs/product/SPARKLE_AURORA_STAGE19_LLM_EXTRACT_DRY_RUN_2026-04-21.md
test -f docs/product/SPARKLE_AURORA_STAGE19_HANDOFF_2026-04-21.md
! rg -n "working_memory" backend/app/models backend/alembic
! rg -n "llm_extractor_prompt.v1.md" backend/app | rg -v "llm_extractor_service.py"
! rg -n "consolidat.*push|push.*consolidat" backend/app
cd mobile && flutter test \
  test/features/chat/presentation/widgets/working_memory_drawer_test.dart \
  test/features/chat/presentation/widgets/working_memory_badge_test.dart
cd ..
echo "[Gate S19-FINAL] ✅ ALL CHECKS PASSED"
