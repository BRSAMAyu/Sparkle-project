#!/bin/bash
set -euo pipefail

cd backend && ./.venv/bin/python -m pytest \
  tests/api/test_achievement_api.py \
  tests/unit/test_state_aggregator_service.py \
  tests/unit/test_user_state_schema_contract.py \
  -q
cd ../mobile && flutter test \
  test/features/achievement/data/repositories/achievement_repository_test.dart \
  test/features/achievement/presentation/providers/achievement_provider_test.dart \
  test/widget/achievement_unlock_dialog_test.dart
cd ..
printf '[%s] WS-BR-ACHIEVEMENT-WIRE accepted | head=%s | tests=achievement + aggregator green\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$(git rev-parse --short HEAD)" >> docs/product/stage22_progress.md
echo "[WS-BR-ACHIEVEMENT-WIRE] ✅ done"
