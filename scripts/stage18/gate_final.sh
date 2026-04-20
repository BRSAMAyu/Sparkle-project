#!/bin/bash
set -euo pipefail

cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_user_state_schema_contract.py \
  tests/unit/test_state_aggregator_service.py \
  tests/unit/test_aggregator_backed_social_context_provider.py \
  tests/unit/test_push_policy_compiler.py \
  tests/unit/test_push_delivery_service.py \
  tests/unit/test_stage18_kill_switch.py \
  tests/unit/test_state_driven_push_service.py \
  tests/unit/test_memory_settings_api.py \
  tests/unit/test_memory_admin_api.py \
  -q
cd ..
python3 scripts/check_rule_ab_aggregator_integrity.py
./backend/.venv/bin/python scripts/check_rule_k_write_paths.py
test -f docs/product/SPARKLE_AURORA_STAGE18_RULE_AB_DEFINITION_2026-04-20.md
test -f docs/product/SPARKLE_AURORA_STAGE18_ROUTER_MIGRATE_EQUIVALENCE_2026-04-20.md
test -f docs/product/SPARKLE_AURORA_STAGE18_HANDOFF_2026-04-20.md
cd mobile && flutter test \
  test/widget/memory_settings_screen_test.dart \
  test/widget/unified_notification_push_card_test.dart \
  test/features/memory/ \
  test/features/home/
cd ..
echo "[Gate S18-FINAL] ✅ ALL CHECKS PASSED"
