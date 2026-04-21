#!/bin/bash
set -euo pipefail

echo "[WS-SK-KILL] running kill-switch tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_stage21_kill_switch.py \
  tests/unit/test_memory_admin_api.py \
  -q
cd ..
printf '[%s] WS-SK-KILL accepted | commits: %s | tests: kill green\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$(git rev-parse --short HEAD)" >> docs/product/stage21_progress.md
echo "[WS-SK-KILL] ✅ done"
