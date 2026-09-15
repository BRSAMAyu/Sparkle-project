#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."
PYTHONPATH=backend python3 scripts/stage23/check_bayesian_no_llm_import.py
cd backend
pytest tests/unit/test_persistent_bayesian_learner_multidim.py tests/unit/test_bayesian_router_integration.py tests/unit/test_persistent_bayesian_learner_contract.py -q
