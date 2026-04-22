#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/backend/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

echo "[Stage 37 Drill] switch on"
PYTHONPATH="${ROOT_DIR}/backend" "${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage37/assert_llm_safety_transition.py" --enabled on

echo "[Stage 37 Drill] switch off"
PYTHONPATH="${ROOT_DIR}/backend" "${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage37/assert_llm_safety_transition.py" --enabled off

echo "[Stage 37 Drill] switch on again"
PYTHONPATH="${ROOT_DIR}/backend" "${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage37/assert_llm_safety_transition.py" --enabled on
