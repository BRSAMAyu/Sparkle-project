#!/bin/bash
set -euo pipefail

WS_NAME="WS-ACCT-MVP"
echo "[$WS_NAME] starting..."

cd backend
./.venv/bin/python -m pytest tests/services/test_accountability_mvp_service.py -q || {
  echo "$WS_NAME backend tests FAIL"
  exit 1
}

cd ../mobile
flutter test test/features/memory/ test/widget/memory_panel_screen_test.dart || {
  echo "$WS_NAME mobile tests FAIL"
  exit 1
}

cd ..
echo "[$WS_NAME] ready for atomic commits"
