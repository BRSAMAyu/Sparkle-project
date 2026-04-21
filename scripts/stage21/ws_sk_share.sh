#!/bin/bash
set -euo pipefail

echo "[WS-SK-SHARE] running share pipeline tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_skill_share_service.py \
  -q
cd ..
python3 scripts/check_rule_af_skill_share_isolation.py
python3 scripts/check_rule_af_skill_pii_pipeline.py
printf '[%s] WS-SK-SHARE accepted | commits: %s | tests: share green\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$(git rev-parse --short HEAD)" >> docs/product/stage21_progress.md
echo "[WS-SK-SHARE] ✅ done"
