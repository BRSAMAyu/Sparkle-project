#!/bin/bash
set -euo pipefail

STAGE="stage20"
LOG_DIR="logs/${STAGE}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo "[Gate S20-0] running baseline replay..."
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
  tests/unit/test_rule_z_guard.py \
  tests/unit/test_social_namespace_isolation.py \
  tests/unit/test_user_state_schema_contract.py \
  tests/unit/test_state_aggregator_service.py \
  tests/unit/test_aggregator_backed_social_context_provider.py \
  tests/unit/test_llm_extractor_service.py \
  tests/unit/test_working_memory_aggregator_integration.py \
  tests/unit/test_working_memory_consolidation.py \
  tests/unit/test_memory_inferred_write_lane.py \
  -q > "../$LOG_DIR/carry_forward.log" 2>&1
cd ..

test -f docs/product/SPARKLE_AURORA_STAGE19_HANDOFF_2026-04-21.md
test -f docs/product/SPARKLE_AURORA_STAGE19_LLM_EXTRACT_DRY_RUN_2026-04-21.md

echo "[Gate S20-0] ✅ passed"

bash scripts/stage20/ws_scq_rules.sh
bash scripts/stage20/ws_sj_core.sh
bash scripts/stage20/ws_cr_core.sh
bash scripts/stage20/ws_scq_aggregator_integrate.sh
bash scripts/stage20/ws_sj_router_consume.sh
bash scripts/stage20/ws_rh_core.sh
bash scripts/stage20/ws_scq_mobile_decl.sh
bash scripts/stage20/gate_final.sh

echo "[Stage 20] ✅ ALL WS PASSED"
