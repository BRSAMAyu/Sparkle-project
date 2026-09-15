#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export SECRET_KEY="${SECRET_KEY:-stage35-journey-secret-0123456789abcd}"
export JWT_SECRET="${JWT_SECRET:-stage35-journey-jwt-0123456789abcde}"
export PYTHONPATH="${ROOT_DIR}:${ROOT_DIR}/backend${PYTHONPATH:+:$PYTHONPATH}"
PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/opt/python@3.11/bin/python3.11}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

TARGET="${1:-all}"

run_main() {
  "$PYTHON_BIN" -m pytest \
    backend/tests/unit/test_stage35_journey_smoke_helpers.py \
    backend/tests/integration/test_stage35_journey_smoke.py \
    -v
}

run_error() {
  "$PYTHON_BIN" -m pytest \
    backend/tests/integration/test_stage35_error_journey_smoke.py \
    -v
}

case "$TARGET" in
  all)
    run_main
    run_error
    ;;
  main)
    run_main
    ;;
  error)
    run_error
    ;;
  *)
    echo "Usage: scripts/journey_smoke.sh [all|main|error]" >&2
    exit 1
    ;;
esac
