#!/bin/bash
set -euo pipefail

STAGE="stage17"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="logs/${STAGE}_${TIMESTAMP}"
mkdir -p "$LOG_DIR"

echo "[Gate S17-0] running baseline replay..."
cd backend
./.venv/bin/python -m pytest \
  tests/aurora \
  tests/api/test_profile_transparency_api.py \
  tests/profile/eval/test_profile_eval_skeleton.py \
  tests/profile/test_intervention_verification_loop.py \
  tests/unit/test_situation_brief.py \
  tests/unit/test_phase2_intervention_pipeline.py \
  -q > "../$LOG_DIR/baseline.log" 2>&1 || { echo "baseline FAIL"; exit 1; }

./.venv/bin/python -m pytest \
  tests/unit/test_persistent_bayesian_learner_contract.py \
  tests/unit/test_multi_dimensional_learner_contract.py \
  tests/unit/test_distilled_strategy_store_contract.py \
  -q > "../$LOG_DIR/rule_v.log" 2>&1 || { echo "Rule V FAIL"; exit 1; }

cd ..
./backend/.venv/bin/python scripts/check_rule_k_write_paths.py \
  > "$LOG_DIR/rule_k.log" 2>&1 || { echo "Rule K FAIL"; exit 1; }

cd backend
./.venv/bin/python -m pytest \
  tests/unit/test_router_node_learning_integration.py \
  tests/unit/test_tool_preference_router.py \
  tests/unit/test_persistent_bayesian_sqam_scale.py \
  tests/unit/test_evidence_resolve.py \
  tests/services/test_within_category_preference_service.py \
  tests/unit/test_predictive_service_productization.py \
  tests/unit/test_memory_inferred_write_lane.py \
  -q > "../$LOG_DIR/carry_forward.log" 2>&1 || { echo "carry-forward FAIL"; exit 1; }

cd ..
echo "[Gate S17-0] ✅ passed"

bash scripts/stage17/ws_soc_rule_z.sh || { echo "WS-SOC-RULE-Z FAIL"; exit 2; }
bash scripts/stage17/ws_soc_namespace.sh || { echo "WS-SOC-NAMESPACE FAIL"; exit 2; }
bash scripts/stage17/ws_soc_extract.sh || { echo "WS-SOC-EXTRACT FAIL"; exit 3; }
bash scripts/stage17/ws_soc_commit.sh || { echo "WS-SOC-COMMIT FAIL"; exit 3; }
bash scripts/stage17/ws_acct_mvp.sh || { echo "WS-ACCT-MVP FAIL"; exit 4; }
bash scripts/stage17/ws_soc_router.sh || { echo "WS-SOC-ROUTER-READ FAIL"; exit 4; }
bash scripts/stage17/ws_soc_mobile.sh || { echo "WS-SOC-MOBILE FAIL"; exit 5; }
bash scripts/stage17/ws_soc_kill.sh || { echo "WS-SOC-KILL FAIL"; exit 5; }
bash scripts/stage17/gate_final.sh || { echo "Gate S17-FINAL FAIL"; exit 6; }

echo "[Stage 17] ✅ ALL WS PASSED"
