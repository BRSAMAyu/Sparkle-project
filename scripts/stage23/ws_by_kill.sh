#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."
cd backend
pytest tests/unit/test_bayesian_kill_switch.py tests/unit/test_bayesian_rollback_parity.py tests/unit/orchestrator/mixins/test_routing_engine_dual_core.py -q
