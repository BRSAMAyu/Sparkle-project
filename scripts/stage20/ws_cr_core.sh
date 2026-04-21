#!/bin/bash
set -euo pipefail

echo "[WS-CR-CORE] running conflict resolver tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_conflict_resolver_service.py \
  tests/unit/test_memory_inferred_write_lane.py \
  -q
cd ..
echo "[WS-CR-CORE] ✅ done"
