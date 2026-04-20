#!/bin/bash
set -euo pipefail

echo "[WS-WM-MOBILE] running mobile working-memory tests..."
cd mobile && flutter test \
  test/features/chat/presentation/widgets/working_memory_drawer_test.dart \
  test/features/chat/presentation/widgets/working_memory_badge_test.dart
cd ..
echo "[WS-WM-MOBILE] ✅ done"
