#!/bin/bash
set -euo pipefail

echo "[WS-WM-CORE] running working memory core tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_working_memory_schema_contract.py \
  tests/unit/test_working_memory_service.py \
  -q
cd ..
python3 scripts/check_rule_ac_working_memory.py
echo "[WS-WM-CORE] ✅ done"
