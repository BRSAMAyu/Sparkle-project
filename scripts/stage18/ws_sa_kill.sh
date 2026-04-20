#!/bin/bash
set -euo pipefail

echo "[WS-SA-KILL] running kill-switch tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_stage18_kill_switch.py \
  tests/unit/test_memory_admin_api.py \
  -q
cd ..
echo "[WS-SA-KILL] ✅ done"
