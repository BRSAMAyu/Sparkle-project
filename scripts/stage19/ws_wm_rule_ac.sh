#!/bin/bash
set -euo pipefail

echo "[WS-WM-RULE-AC] validating Rule AC artifacts..."
test -f docs/product/SPARKLE_AURORA_STAGE19_DISPATCH_PLAN_2026-04-21.md
test -f docs/product/SPARKLE_AURORA_STAGE19_RULE_AC_DEFINITION_2026-04-21.md
python3 scripts/check_rule_ac_working_memory.py
echo "[WS-WM-RULE-AC] ✅ done"
