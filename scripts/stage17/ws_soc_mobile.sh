#!/bin/bash
set -euo pipefail

WS_NAME="WS-SOC-MOBILE"
echo "[$WS_NAME] starting..."

cd mobile
flutter test \
  test/features/memory/presentation/widgets/subject_type_filter_test.dart \
  test/widget/memory_settings_screen_test.dart \
  test/widget/memory_panel_screen_test.dart || {
  echo "$WS_NAME tests FAIL"
  exit 1
}

cd ..
echo "[$WS_NAME] ready for atomic commit"
