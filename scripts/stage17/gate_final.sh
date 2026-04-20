#!/bin/bash
set -euo pipefail

cd backend
./.venv/bin/python -m pytest tests/aurora -q
./.venv/bin/python -m pytest \
  tests/unit/test_persistent_bayesian_learner_contract.py \
  tests/unit/test_multi_dimensional_learner_contract.py \
  tests/unit/test_distilled_strategy_store_contract.py \
  -q

./.venv/bin/python -m pytest \
  tests/unit/test_rule_z_guard.py \
  tests/unit/test_social_namespace_isolation.py \
  tests/services/test_memory_subject_type_extraction.py \
  tests/services/test_commitment_parser.py \
  tests/services/test_accountability_mvp_service.py \
  tests/unit/test_router_context_reader.py \
  tests/unit/test_social_kill_switch.py \
  -q

cd ../mobile
flutter test test/features/memory/ test/features/home/

cd ..
python3 - <<'PY'
from pathlib import Path

required = [
    "docs/product/SPARKLE_AURORA_STAGE17_ROUTER_AB_REPORT_2026-04-20.md",
    "docs/product/SPARKLE_AURORA_STAGE17_ACCT_HEALTH_AUDIT_2026-04-20.md",
    "docs/product/SPARKLE_AURORA_STAGE17_HANDOFF_2026-04-20.md",
]
missing = [path for path in required if not Path(path).exists()]
if missing:
    raise SystemExit(f"missing artifacts: {missing}")
PY

grep -rnE "subject_type|mentioned_entity_owner_user_id" backend/app mobile/lib > /tmp/grep_subject.log
grep -rn "RouterContextReader" backend/app > /tmp/grep_router.log

echo "[Gate S17-FINAL] ✅ ALL CHECKS PASSED"
