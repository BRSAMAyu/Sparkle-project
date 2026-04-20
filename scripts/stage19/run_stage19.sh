#!/bin/bash
set -euo pipefail

STAGE="stage19"
LOG_DIR="logs/${STAGE}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo "[Gate S19-0] running baseline replay..."
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

cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_router_node_learning_integration.py \
  tests/unit/test_tool_preference_router.py \
  tests/unit/test_persistent_bayesian_sqam_scale.py \
  tests/unit/test_evidence_resolve.py \
  tests/services/test_within_category_preference_service.py \
  tests/unit/test_predictive_service_productization.py \
  tests/unit/test_memory_inferred_write_lane.py \
  tests/unit/test_rule_z_guard.py \
  tests/unit/test_social_namespace_isolation.py \
  tests/services/test_memory_subject_type_extraction.py \
  tests/services/test_commitment_parser.py \
  tests/services/test_accountability_mvp_service.py \
  tests/unit/test_router_context_reader.py \
  tests/unit/test_social_kill_switch.py \
  tests/unit/test_user_state_schema_contract.py \
  tests/unit/test_state_aggregator_service.py \
  tests/unit/test_aggregator_backed_social_context_provider.py \
  tests/unit/test_push_policy_compiler.py \
  tests/unit/test_push_delivery_service.py \
  tests/unit/test_stage18_kill_switch.py \
  tests/unit/test_state_driven_push_service.py \
  tests/unit/test_memory_settings_api.py \
  tests/unit/test_memory_admin_api.py \
  -q > "../$LOG_DIR/carry_forward.log" 2>&1
cd ..

test -f docs/product/SPARKLE_AURORA_STAGE18_HANDOFF_2026-04-20.md
test -f docs/product/SPARKLE_AURORA_STAGE18_ROUTER_MIGRATE_EQUIVALENCE_2026-04-20.md

echo "[Gate S19-0] ✅ passed"

bash scripts/stage19/ws_wm_rule_ac.sh
bash scripts/stage19/ws_wm_core.sh
bash scripts/stage19/ws_wm_llm_extract.sh
bash scripts/stage19/ws_wm_consolidate.sh
bash scripts/stage19/ws_wm_aggregator_integrate.sh
bash scripts/stage19/ws_wm_mobile.sh
bash scripts/stage19/ws_wm_kill.sh
bash scripts/stage19/gate_final.sh

echo "[Stage 19] ✅ ALL WS PASSED"
