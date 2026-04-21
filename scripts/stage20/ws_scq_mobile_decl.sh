#!/bin/bash
set -euo pipefail

echo "[WS-SCQ-MOBILE-DECL] running unresolved conflict mobile tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_memory_unresolved_conflicts_api.py \
  -q
cd ../mobile && flutter test \
  test/features/memory/presentation/widgets/unresolved_conflicts_section_test.dart \
  test/features/memory/presentation/screens/memory_panel_screen_test.dart
cd ..
echo "[WS-SCQ-MOBILE-DECL] ✅ done"
