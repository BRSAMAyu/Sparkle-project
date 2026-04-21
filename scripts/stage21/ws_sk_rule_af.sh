#!/bin/bash
set -euo pipefail

echo "[WS-SK-RULE-AF] validating Rule AF artifacts..."
test -f docs/product/SPARKLE_AURORA_STAGE21_DISPATCH_PLAN_2026-04-21.md
test -f docs/product/SPARKLE_AURORA_STAGE21_RULE_AF_DEFINITION_2026-04-21.md
test -f backend/app/services/skill_extract_prompt.v1.md
test -f backend/app/services/skill_pii_detector_prompt.v1.md
test -f backend/app/services/skill_injection_detector_prompt.v1.md
test -f backend/app/services/skill_extract_trigger_keywords.v1.json
python3 scripts/check_rule_af_skill_share_isolation.py
python3 scripts/check_rule_af_skill_pii_pipeline.py
python3 scripts/check_skill_extract_trigger_purity.py
printf '[%s] WS-SK-RULE-AF accepted | commits: %s | tests: guards pass\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$(git rev-parse --short HEAD)" >> docs/product/stage21_progress.md
echo "[WS-SK-RULE-AF] ✅ done"
