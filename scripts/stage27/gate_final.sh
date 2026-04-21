#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

python3 scripts/stage27/check_rule_al_foresight_not_router.py
python3 scripts/stage27/check_foresight_no_llm_import.py
python3 scripts/stage27/check_persdyn_user_isolation.py
python3 scripts/stage27/check_jitai_template_registry.py

backend/.venv/bin/python -m pytest \
  backend/tests/unit/test_foresight_snapshot_schema.py \
  backend/tests/unit/test_predictive_service_extension.py \
  backend/tests/unit/test_persdyn_attractor_service.py \
  backend/tests/unit/test_attractor_cold_start.py \
  backend/tests/unit/test_deviation_detector.py \
  backend/tests/unit/test_jitai_trigger.py \
  backend/tests/unit/test_jitai_budget_cooldown.py \
  backend/tests/unit/test_jitai_template_no_llm.py \
  backend/tests/unit/test_aggregator_schema_v1_8.py \
  backend/tests/unit/test_foresight_kill_switch.py \
  backend/tests/unit/test_rule_al_not_router.py \
  backend/tests/unit/test_foresight_router_zero_hit.py \
  backend/tests/unit/test_persdyn_user_isolation.py \
  -q

(
  cd mobile
  flutter test test/widget/foresight_hint_display_test.dart
)
