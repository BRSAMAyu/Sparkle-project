#!/bin/bash
set -euo pipefail

cd backend && ./.venv/bin/python -m pytest \
  tests/api/test_calendar_api.py \
  tests/unit/test_state_aggregator_service.py \
  tests/unit/test_prompt_signal_closure.py \
  -q
cd ../mobile && flutter test \
  test/features/calendar/data/models/calendar_event_model_test.dart
cd ..
printf '[%s] WS-BR-CALENDAR-WIRE accepted | head=%s | scope=authenticated read-only expansion\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$(git rev-parse --short HEAD)" >> docs/product/stage22_progress.md
echo "[WS-BR-CALENDAR-WIRE] ✅ done"
