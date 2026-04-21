#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."
cd backend
pytest tests/unit/test_source_state_encoder.py tests/unit/test_source_state_backfill.py tests/unit/test_rule_ah_dimension_registry.py -q
