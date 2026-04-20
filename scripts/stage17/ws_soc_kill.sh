#!/bin/bash
set -euo pipefail

WS_NAME="WS-SOC-KILL"
echo "[$WS_NAME] starting..."

cd backend
./.venv/bin/python -m pytest tests/unit/test_social_kill_switch.py -q || {
  echo "$WS_NAME tests FAIL"
  exit 1
}

cd ..
echo "[$WS_NAME] ready for atomic commit"
