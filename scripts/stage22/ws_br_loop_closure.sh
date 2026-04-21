#!/bin/bash
set -euo pipefail

python3 scripts/check_error_replan_trigger_purity.py
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_error_replan_bridge.py \
  tests/unit/test_intervention_strategy_learner.py \
  -q
cd ..
printf '[%s] WS-BR-LOOP-CLOSURE accepted | head=%s | tests=error bridge + learner green\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$(git rev-parse --short HEAD)" >> docs/product/stage22_progress.md
echo "[WS-BR-LOOP-CLOSURE] ✅ done"
