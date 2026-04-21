#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/backend"

pytest \
  tests/unit/test_route_history_read_api.py \
  tests/unit/test_reflection_agent_user_id.py \
  tests/unit/test_reflection_trigger_extension.py \
  tests/unit/test_reflection_context_injection.py \
  tests/unit/test_aggregator_schema_v1_6.py \
  tests/unit/test_reflection_kill_switch.py \
  tests/unit/test_rule_aj_user_id_isolation.py \
  tests/unit/test_reflection_rule_y_gate.py \
  tests/unit/test_state_aggregator_service.py \
  tests/unit/test_user_state_schema_contract.py

cd "$ROOT/mobile"
flutter test test/widget/reflection_recent_summary_test.dart
