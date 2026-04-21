#!/bin/bash
set -euo pipefail

echo "[WS-RH-CORE] running route history tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_route_history_service.py \
  tests/unit/test_route_history_performance.py \
  -q
cd ..
echo "[WS-RH-CORE] ✅ done"
