#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/backend"

pytest \
  tests/services/test_policy_ir_schema.py \
  tests/services/test_policy_compiler.py \
  tests/services/test_policy_scheduler.py \
  tests/services/test_policy_scheduler_budget.py \
  tests/services/test_policy_scheduler_partner_consent.py \
  tests/unit/test_aggregator_schema_v1_5.py \
  tests/unit/test_policy_kill_switch.py \
  tests/unit/test_rule_ai_policy_purity.py

cd "$ROOT/mobile"
flutter test test/widget/commitment_detail_screen_policy_test.dart
