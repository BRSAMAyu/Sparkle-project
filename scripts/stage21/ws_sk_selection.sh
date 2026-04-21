#!/bin/bash
set -euo pipefail

echo "[WS-SK-SELECTION] running selection and aggregator tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_skill_selection_service.py \
  tests/unit/test_skill_selection_aggregator_integration.py \
  tests/unit/test_user_state_schema_contract.py \
  tests/unit/test_working_memory_aggregator_integration.py \
  tests/unit/test_route_history_service.py \
  tests/unit/test_route_history_performance.py \
  -q
cd ..
python3 scripts/check_rule_ab_aggregator_integrity.py
python3 scripts/check_route_history_skill_field.py
printf '[%s] WS-SK-SELECTION accepted | commits: %s | tests: selection green\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$(git rev-parse --short HEAD)" >> docs/product/stage21_progress.md
echo "[WS-SK-SELECTION] ✅ done"
