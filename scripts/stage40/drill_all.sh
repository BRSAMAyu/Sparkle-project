#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export SECRET_KEY="${SECRET_KEY:-stage40-drill-secret-0123456789abcd}"
export JWT_SECRET="${JWT_SECRET:-stage40-drill-jwt-0123456789abcde}"
cd "$ROOT_DIR/backend"
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/opt/python@3.11/bin/python3.11}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi
export PYTHON_BIN

echo "[stage40] running consolidated Stage 18-31 + Stage 40 drills"
"$PYTHON_BIN" ../scripts/stage40/run_kill_switch_drills.py

cd "$ROOT_DIR"
echo "[stage40] replaying Stage 33-35 legacy drills"
bash "$ROOT_DIR/scripts/stage33/drill_transitions.sh"
bash "$ROOT_DIR/scripts/stage34/drill_transitions.sh"
bash "$ROOT_DIR/scripts/stage35/drill_transitions.sh"

echo "[stage40] replaying Stage 37-39 drills"
bash "$ROOT_DIR/scripts/stage37/drill_transitions.sh"
bash "$ROOT_DIR/scripts/stage38/drill_transitions.sh"
bash "$ROOT_DIR/scripts/stage39/drill_transitions.sh"

echo "[stage40] PASS"
