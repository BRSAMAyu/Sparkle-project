#!/bin/bash
set -euo pipefail

echo "[WS-WM-AGGREGATOR-INTEGRATE] running aggregator integration tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_working_memory_aggregator_integration.py \
  tests/unit/test_user_state_schema_contract.py \
  -q
cd ..
test -f proto/user_state.proto
echo "[WS-WM-AGGREGATOR-INTEGRATE] ✅ done"
