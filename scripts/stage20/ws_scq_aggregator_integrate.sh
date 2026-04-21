#!/bin/bash
set -euo pipefail

echo "[WS-SCQ-AGGREGATOR-INTEGRATE] running aggregator sufficiency integration tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_user_state_schema_contract.py \
  tests/unit/test_state_aggregator_service.py \
  tests/unit/test_sufficiency_aggregator_integration.py \
  -q
cd ..
make proto-gen
test -f proto/user_state.proto
echo "[WS-SCQ-AGGREGATOR-INTEGRATE] ✅ done"
