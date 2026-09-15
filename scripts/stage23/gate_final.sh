#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

PYTHONPATH=backend python3 scripts/stage23/check_rule_ah_dimension_registry.py
PYTHONPATH=backend python3 scripts/stage23/check_bayesian_no_llm_import.py
PYTHONPATH=backend python3 scripts/stage23/check_data_density.py

cd backend
pytest \
  tests/unit/test_source_state_encoder.py \
  tests/unit/test_source_state_backfill.py \
  tests/unit/test_routing_outcome_backfill.py \
  tests/unit/test_persistent_bayesian_learner_multidim.py \
  tests/unit/test_bayesian_router_integration.py \
  tests/unit/test_bayesian_kill_switch.py \
  tests/unit/test_bayesian_rollback_parity.py \
  tests/unit/test_rule_ah_dimension_registry.py \
  tests/unit/test_route_history_service.py \
  tests/unit/test_route_history_performance.py \
  tests/unit/test_persistent_bayesian_learner_contract.py \
  tests/unit/orchestrator/mixins/test_routing_engine_dual_core.py \
  tests/test_context_manager.py \
  tests/unit/test_prompt_signal_closure.py \
  tests/unit/test_state_aggregator_service.py \
  -q
