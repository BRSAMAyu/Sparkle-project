#!/bin/bash
set -euo pipefail

echo "[WS-SA-CORE] running schema and aggregator tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_user_state_schema_contract.py \
  tests/unit/test_state_aggregator_service.py \
  -q
cd ..
test -f proto/user_state.proto
echo "[WS-SA-CORE] ✅ done"

