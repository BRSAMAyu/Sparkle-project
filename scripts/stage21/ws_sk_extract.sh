#!/bin/bash
set -euo pipefail

echo "[WS-SK-EXTRACT] running extract tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_skill_extract_service.py \
  -q
cd ..
python3 scripts/check_skill_extract_trigger_purity.py
printf '[%s] WS-SK-EXTRACT accepted | commits: %s | tests: extract green\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$(git rev-parse --short HEAD)" >> docs/product/stage21_progress.md
echo "[WS-SK-EXTRACT] ✅ done"
