#!/bin/bash
set -euo pipefail

echo "[WS-SA-RULE-AB] validating Rule AB artifacts..."
test -f docs/product/SPARKLE_AURORA_STAGE18_RULE_AB_DEFINITION_2026-04-20.md
python3 scripts/check_rule_ab_aggregator_integrity.py
echo "[WS-SA-RULE-AB] ✅ done"

