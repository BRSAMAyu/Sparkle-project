#!/bin/bash
set -euo pipefail

WS_NAME="WS-SOC-RULE-Z"
echo "[$WS_NAME] starting..."

cd backend
./.venv/bin/python -m pytest tests/unit/test_rule_z_guard.py -q || {
  echo "$WS_NAME tests FAIL"
  exit 1
}

cd ..
./backend/.venv/bin/python scripts/check_rule_k_write_paths.py || {
  echo "$WS_NAME guard FAIL"
  exit 1
}

cd backend
./.venv/bin/python -m pytest tests/aurora -q || {
  echo "$WS_NAME baseline regression FAIL"
  exit 1
}

cd ..
echo "[$WS_NAME] ready for atomic commits once implementation is green"
