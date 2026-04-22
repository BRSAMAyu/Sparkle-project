#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/backend/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

echo "[Stage 37] Backend targeted tests"
cd "${ROOT_DIR}/backend"
PYTHONPATH="${ROOT_DIR}/backend" "${PYTHON_BIN}" -m pytest \
  tests/api/test_achievement_api.py \
  tests/api/test_visual_elements_api.py \
  tests/api/test_internal_api_fail_closed.py \
  tests/unit/test_llm_service_security.py \
  tests/unit/test_stage37_llm_safety_kill_switch.py \
  tests/unit/test_tool_executor_observability.py

echo "[Stage 37] Gateway targeted tests"
cd "${ROOT_DIR}/backend/gateway"
go test ./internal/middleware ./internal/handler ./cmd/server
