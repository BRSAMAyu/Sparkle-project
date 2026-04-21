#!/bin/bash
set -euo pipefail

STAGE="stage21"
LOG_DIR="logs/${STAGE}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo "[Gate S21-0] running baseline replay..."
cd backend && ./.venv/bin/python -m pytest \
  tests/aurora \
  tests/api/test_profile_transparency_api.py \
  tests/profile/eval/test_profile_eval_skeleton.py \
  tests/profile/test_intervention_verification_loop.py \
  tests/unit/test_situation_brief.py \
  tests/unit/test_phase2_intervention_pipeline.py \
  -q > "../$LOG_DIR/baseline.log" 2>&1

./.venv/bin/python -m pytest \
  tests/unit/test_persistent_bayesian_learner_contract.py \
  tests/unit/test_multi_dimensional_learner_contract.py \
  tests/unit/test_distilled_strategy_store_contract.py \
  -q > "../$LOG_DIR/rule_v.log" 2>&1
cd ..

./backend/.venv/bin/python scripts/check_rule_k_write_paths.py > "$LOG_DIR/rule_k.log" 2>&1
python3 scripts/check_rule_ab_aggregator_integrity.py > "$LOG_DIR/rule_ab.log" 2>&1
python3 scripts/check_rule_ac_working_memory.py > "$LOG_DIR/rule_ac.log" 2>&1
python3 scripts/check_rule_af_skill_share_isolation.py > "$LOG_DIR/rule_af_isolation.log" 2>&1
python3 scripts/check_rule_af_skill_pii_pipeline.py > "$LOG_DIR/rule_af_pipeline.log" 2>&1

cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_rule_z_guard.py \
  tests/unit/test_social_namespace_isolation.py \
  tests/unit/test_user_state_schema_contract.py \
  tests/unit/test_working_memory_aggregator_integration.py \
  tests/unit/test_route_history_service.py \
  tests/unit/test_route_history_performance.py \
  tests/unit/test_skill_schema_contract.py \
  tests/unit/test_skill_store_service.py \
  tests/unit/test_skill_extract_service.py \
  tests/unit/test_skill_selection_service.py \
  tests/unit/test_skill_selection_aggregator_integration.py \
  tests/unit/test_skill_share_service.py \
  tests/unit/test_stage21_kill_switch.py \
  tests/unit/test_skills_api.py \
  tests/unit/test_memory_admin_api.py \
  -q > "../$LOG_DIR/carry_forward.log" 2>&1
cd ..

test -f docs/product/SPARKLE_AURORA_STAGE20_HANDOFF_2026-04-21.md
test -f docs/product/SPARKLE_AURORA_STAGE21_DISPATCH_PLAN_2026-04-21.md
test -f docs/product/SPARKLE_AURORA_STAGE21_RULE_AF_DEFINITION_2026-04-21.md
test -f backend/app/services/skill_extract_prompt.v1.md
test -f backend/app/services/skill_pii_detector_prompt.v1.md
test -f backend/app/services/skill_injection_detector_prompt.v1.md
test -f backend/app/services/skill_extract_trigger_keywords.v1.json

echo "[Gate S21-0] ✅ passed"

bash scripts/stage21/ws_sk_rule_af.sh
bash scripts/stage21/ws_sk_schema.sh
bash scripts/stage21/ws_sk_extract.sh
bash scripts/stage21/ws_sk_selection.sh
bash scripts/stage21/ws_sk_share.sh
bash scripts/stage21/ws_sk_mobile.sh
bash scripts/stage21/ws_sk_kill.sh
bash scripts/stage21/gate_final.sh

echo "[Stage 21] ✅ ALL WS PASSED"
