#!/bin/bash
set -euo pipefail

echo "[WS-SJ-ROUTER-CONSUME] running router sufficiency tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_router_sufficiency_branch.py \
  tests/unit/test_follow_up_question_templates.py \
  -q
cd ..
python3 scripts/check_rule_ad_sufficiency_split.py
echo "[WS-SJ-ROUTER-CONSUME] ✅ done"
