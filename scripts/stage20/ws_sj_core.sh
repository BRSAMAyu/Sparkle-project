#!/bin/bash
set -euo pipefail

echo "[WS-SJ-CORE] running sufficiency judge tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_sufficiency_judge_schema.py \
  tests/unit/test_sufficiency_judge_service.py \
  -q
cd ..
echo "[WS-SJ-CORE] ✅ done"
