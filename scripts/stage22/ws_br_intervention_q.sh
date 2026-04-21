#!/bin/bash
set -euo pipefail

cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_intervention_strategy_learner.py \
  tests/unit/test_error_replan_bridge.py \
  -q
cd ..
printf '[%s] WS-BR-INTERVENTION-Q accepted | head=%s | tests=cohort fallback green\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$(git rev-parse --short HEAD)" >> docs/product/stage22_progress.md
echo "[WS-BR-INTERVENTION-Q] ✅ done"
