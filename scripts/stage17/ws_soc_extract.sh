#!/bin/bash
set -euo pipefail

WS_NAME="WS-SOC-EXTRACT"
echo "[$WS_NAME] starting..."

cd backend
./.venv/bin/python -m pytest tests/services/test_memory_subject_type_extraction.py -q || {
  echo "$WS_NAME tests FAIL"
  exit 1
}

./.venv/bin/python -m pytest tests/unit/test_memory_inferred_write_lane.py -q || {
  echo "$WS_NAME regression FAIL"
  exit 1
}

cd ..
echo "[$WS_NAME] ready for atomic commits"
