#!/bin/bash
set -euo pipefail

echo "[WS-WM-KILL] running stage19 kill-switch tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_stage19_kill_switch.py \
  -q
cd ..
echo "[WS-WM-KILL] ✅ done"
