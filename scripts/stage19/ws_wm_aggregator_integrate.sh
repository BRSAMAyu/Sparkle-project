#!/bin/bash
set -euo pipefail

echo "[WS-WM-AGGREGATOR-INTEGRATE] running aggregator integration tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_working_memory_aggregator_integration.py \
  tests/unit/test_user_state_schema_contract.py \
  tests/unit/test_state_aggregator_service.py \
  tests/unit/test_aggregator_backed_social_context_provider.py \
  -q
cd ..
make proto-gen
test -f proto/user_state.proto
echo "[WS-WM-AGGREGATOR-INTEGRATE] ✅ done"
