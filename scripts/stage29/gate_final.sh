#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/backend/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage29/check_rule_an_orchestrator_isolation.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage29/check_rule_an_orchestrator_no_hardcoded_phase.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage29/check_scaffolding_aggregator_only.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage29/check_srl_not_router.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage29/check_srl_user_isolation.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage29/check_srl_no_llm_import.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage29/check_rule_al_sdt_language.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/check_rule_ab_aggregator_integrity.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/check_rule_ac_working_memory.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/check_rule_ad_sufficiency_split.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/check_rule_ae_conflict_audit.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage23/check_rule_ah_dimension_registry.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage24/check_rule_ai_policy_purity.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage25/check_rule_aj_user_id_isolation.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage26/check_rule_ak_algorithm_constraint.py"

cd "${ROOT_DIR}/backend"
if [[ -x ".venv/bin/pytest" ]]; then
  .venv/bin/pytest \
    tests/unit/test_srl_phase_model.py \
    tests/unit/test_srl_transition_matrix.py \
    tests/unit/test_srl_coldstart_from_traits.py \
    tests/unit/test_srl_phase_tracker.py \
    tests/unit/test_tracker_concurrent_user_isolation.py \
    tests/unit/test_srl_event_publish.py \
    tests/unit/test_srl_event_consume.py \
    tests/unit/test_event_bus_lag_monitor.py \
    tests/unit/test_no_direct_tracker_import_from_orchestrator.py \
    tests/unit/test_scaffolding_srl_extend.py \
    tests/unit/test_scaffolding_no_direct_tracker_import.py \
    tests/unit/test_aggregator_schema_v1_10.py \
    tests/unit/test_srl_router_zero_hit.py \
    tests/unit/test_srl_kill_switch.py \
    tests/unit/test_srl_auto_downgrade.py \
    tests/unit/test_rule_an_full_scan.py \
    tests/unit/test_srl_user_isolation.py
fi
