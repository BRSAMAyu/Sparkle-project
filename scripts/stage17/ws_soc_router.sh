#!/bin/bash
set -euo pipefail

WS_NAME="WS-SOC-ROUTER-READ"
echo "[$WS_NAME] starting..."

cd backend
./.venv/bin/python -m pytest tests/unit/test_router_context_reader.py -q || {
  echo "$WS_NAME tests FAIL"
  exit 1
}

./.venv/bin/python ../scripts/stage17/router_ab_test.py || {
  echo "$WS_NAME ab FAIL"
  exit 1
}

cd ..
echo "[$WS_NAME] ready for atomic commits"
