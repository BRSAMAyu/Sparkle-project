#!/bin/bash
set -euo pipefail

WS_NAME="WS-SOC-NAMESPACE"
echo "[$WS_NAME] starting..."

cd backend
./.venv/bin/python -m pytest tests/unit/test_social_namespace_isolation.py -q || {
  echo "$WS_NAME tests FAIL"
  exit 1
}

cd ..
./backend/.venv/bin/python scripts/check_rule_k_write_paths.py || {
  echo "$WS_NAME guard FAIL"
  exit 1
}

cd backend
./.venv/bin/python -m pytest tests/unit/test_context_manager_community_context.py -q || {
  echo "$WS_NAME regression FAIL"
  exit 1
}

cd ..
echo "[$WS_NAME] ready for atomic commit"
