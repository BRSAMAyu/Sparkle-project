#!/bin/bash
set -euo pipefail

echo "[WS-SA-ROUTER-MIGRATE] running provider equivalence tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_aggregator_backed_social_context_provider.py \
  -q
cd ..
test -f docs/product/SPARKLE_AURORA_STAGE18_ROUTER_MIGRATE_EQUIVALENCE_2026-04-20.md
echo "[WS-SA-ROUTER-MIGRATE] ✅ done"
