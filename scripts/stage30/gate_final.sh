#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${REPO_ROOT}/backend/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

cd "${REPO_ROOT}"

echo "[Stage 30] Rule guards"
"${REPO_ROOT}/scripts/run_all_rule_guards.sh" --rule AO
"${REPO_ROOT}/scripts/run_all_rule_guards.sh" --rule AQ

echo "[Stage 30] Targeted backend tests"
PYTHONPATH="${REPO_ROOT}/backend" "${PYTHON_BIN}" -m pytest \
  backend/tests/unit/test_metacognition_service.py \
  backend/tests/unit/test_rule_ao_diagnostic_ban.py \
  backend/tests/unit/test_scaffolding_combine_matrix.py \
  backend/tests/unit/test_metacognition_kill_switch.py \
  backend/tests/unit/test_aggregator_schema_v1_11.py

echo "[Stage 30] Mobile widget test"
(
  cd "${REPO_ROOT}/mobile"
  flutter test test/widget/metacognition_panel_test.dart
)
