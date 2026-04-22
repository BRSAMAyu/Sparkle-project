#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/backend/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

GUARDS=(
  "PersDyn|ID1|scripts/stage32/check_sqam_persdyn_id1.py"
  "PersDyn|ST1|scripts/stage32/check_sqam_persdyn_st1.py"
  "PersDyn|DP1|scripts/stage32/check_sqam_persdyn_dp1.py"
  "PersDyn|SM1|scripts/stage32/check_sqam_persdyn_sm1_mood.py"
  "JITAI|ID1|scripts/stage32/check_sqam_jitai_id1.py"
  "JITAI|DP1|scripts/stage32/check_sqam_jitai_dp1.py"
  "Predictive|ID1|scripts/stage32/check_sqam_predictive_id1.py"
  "Predictive|ST1|scripts/stage32/check_sqam_predictive_st1.py"
  "Predictive|DP1|scripts/stage32/check_sqam_predictive_dp1.py"
  "Predictive|SM1|scripts/stage32/check_sqam_predictive_sm1.py"
  "SRL|DP1|scripts/stage32/check_sqam_srl_dp1.py"
  "Idiographic|DP1|scripts/stage32/check_sqam_idiographic_dp1.py"
  "Idiographic|SM1|scripts/stage32/check_sqam_idiographic_sm1.py"
)

echo "Stage 32 SQAM suite"
printf '%-12s %-4s %s\n' "Component" "Dim" "Guard"
printf '%-12s %-4s %s\n' "---------" "---" "-----"

for entry in "${GUARDS[@]}"; do
  IFS='|' read -r component dim script_path <<< "${entry}"
  printf '%-12s %-4s %s\n' "${component}" "${dim}" "${script_path}"
  "${PYTHON_BIN}" "${REPO_ROOT}/${script_path}"
done

echo "Stage 32 SQAM suite passed (${#GUARDS[@]} guards)"
