#!/bin/bash
set -euo pipefail

echo "[WS-SK-MOBILE] running skill mobile tests..."
cd mobile && flutter test \
  test/core/models/skill_models_test.dart \
  test/features/user/presentation/screens/skill_management_screen_test.dart \
  test/app/skill_management_route_test.dart
cd ..
printf '[%s] WS-SK-MOBILE accepted | commits: %s | tests: mobile green\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$(git rev-parse --short HEAD)" >> docs/product/stage21_progress.md
echo "[WS-SK-MOBILE] ✅ done"
