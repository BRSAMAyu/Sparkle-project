#!/bin/bash
set -euo pipefail

echo "[WS-WM-CONSOLIDATE] running consolidation tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_working_memory_consolidation.py \
  -q
cd ..
echo "[WS-WM-CONSOLIDATE] ✅ done"
