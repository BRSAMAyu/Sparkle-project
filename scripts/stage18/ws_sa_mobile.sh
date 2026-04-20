#!/bin/bash
set -euo pipefail

echo "[WS-SA-MOBILE] running mobile Stage 18 tests..."
cd mobile && flutter test \
  test/widget/memory_settings_screen_test.dart \
  test/widget/unified_notification_push_card_test.dart
cd ..
echo "[WS-SA-MOBILE] ✅ done"
