#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/backend/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage28/check_rule_am_confidence_cap.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage28/check_trait_not_router.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage28/check_nlp_no_direct_write.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage28/check_trait_user_isolation.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage28/check_nlp_bias_calibration.py"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/stage28/check_traits_no_diagnostic_labels.py"

cd "${ROOT_DIR}/backend"
if [[ -x ".venv/bin/pytest" ]]; then
  .venv/bin/pytest tests/unit/test_big_five_model.py tests/unit/test_trait_dynamic_conflict_resolution.py tests/unit/test_traits_nlp_observer.py tests/unit/test_coldstart_service.py tests/unit/test_aggregator_schema_v1_9.py tests/unit/test_traits_router_zero_hit.py tests/unit/test_traits_kill_switch.py tests/unit/test_traits_auto_downgrade.py tests/unit/test_trait_user_isolation.py tests/unit/test_confidence_cap_enforcement.py
fi
