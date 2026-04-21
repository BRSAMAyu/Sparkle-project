#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."
cd backend
pytest tests/unit/test_routing_outcome_backfill.py tests/unit/test_route_history_service.py tests/unit/test_route_history_performance.py -q
