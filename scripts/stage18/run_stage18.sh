#!/bin/bash
set -euo pipefail

STAGE="stage18"
LOG_DIR="logs/${STAGE}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo "[Gate S18-0] running baseline replay..."
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
  -q > "../$LOG_DIR/carry_forward.log" 2>&1
cd ..

echo "[Gate S18-0] ✅ passed"

bash scripts/stage18/ws_sa_rule_ab.sh
bash scripts/stage18/ws_sa_core.sh
bash scripts/stage18/ws_sa_router_migrate.sh
bash scripts/stage18/ws_sa_push_policy.sh
bash scripts/stage18/ws_sa_push_channel.sh
bash scripts/stage18/ws_sa_mobile.sh
bash scripts/stage18/ws_sa_kill.sh
bash scripts/stage18/gate_final.sh

echo "[Stage 18] ✅ ALL WS PASSED"

