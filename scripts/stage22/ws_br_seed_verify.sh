#!/bin/bash
set -euo pipefail

cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_seed_library_stage22.py \
  tests/unit/test_seed_library_service.py \
  tests/aurora/test_seed_bridge.py \
  -q
cd ../mobile && flutter test \
  test/features/seed_library/presentation/providers/seed_library_provider_test.dart
cd ..
printf '[%s] WS-BR-SEED-VERIFY accepted | head=%s | tests=seed adoption + withdrawal green\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$(git rev-parse --short HEAD)" >> docs/product/stage22_progress.md
echo "[WS-BR-SEED-VERIFY] ✅ done"
