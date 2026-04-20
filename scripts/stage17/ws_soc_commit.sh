#!/bin/bash
set -euo pipefail

WS_NAME="WS-SOC-COMMIT"
echo "[$WS_NAME] starting..."

cd backend
./.venv/bin/python -m pytest tests/services/test_commitment_parser.py -q || {
  echo "$WS_NAME tests FAIL"
  exit 1
}

cd ..
echo "[$WS_NAME] ready for atomic commits"
