#!/bin/bash
set -euo pipefail

echo "[WS-SCQ-RULES] validating Rule AD/AE artifacts..."
test -f docs/product/SPARKLE_AURORA_STAGE20_DISPATCH_PLAN_2026-04-21.md
test -f docs/product/SPARKLE_AURORA_STAGE20_RULE_AD_AE_DEFINITION_2026-04-21.md
test -f backend/app/services/follow_up_question_templates.v1.json
python3 scripts/check_rule_ad_sufficiency_split.py
python3 scripts/check_rule_ae_conflict_audit.py
echo "[WS-SCQ-RULES] ✅ done"
