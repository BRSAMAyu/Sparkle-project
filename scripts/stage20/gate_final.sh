#!/bin/bash
set -euo pipefail

cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_sufficiency_judge_schema.py \
  tests/unit/test_sufficiency_judge_service.py \
  tests/unit/test_conflict_resolver_service.py \
  tests/unit/test_sufficiency_aggregator_integration.py \
  tests/unit/test_router_sufficiency_branch.py \
  tests/unit/test_follow_up_question_templates.py \
  tests/unit/test_route_history_service.py \
  tests/unit/test_route_history_performance.py \
  tests/unit/test_memory_unresolved_conflicts_api.py \
  -q
cd ..

make proto-gen
python3 scripts/check_rule_k_write_paths.py
python3 scripts/check_rule_ab_aggregator_integrity.py
python3 scripts/check_rule_ac_working_memory.py
python3 scripts/check_rule_ad_sufficiency_split.py
python3 scripts/check_rule_ae_conflict_audit.py
test -f docs/product/SPARKLE_AURORA_STAGE20_RULE_AD_AE_DEFINITION_2026-04-21.md
test -f docs/product/SPARKLE_AURORA_STAGE20_HANDOFF_2026-04-21.md

echo "[Gate S20-FINAL] ✅ ALL CHECKS PASSED"
