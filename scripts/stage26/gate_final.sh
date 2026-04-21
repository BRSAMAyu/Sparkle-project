#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

python3 scripts/stage26/check_rule_ak_algorithm_constraint.py
python3 scripts/stage26/check_scene_no_llm_import.py
python3 scripts/stage26/check_scene_idempotency.py
python3 scripts/stage26/check_scene_user_isolation.py

backend/.venv/bin/python -m pytest \
  backend/tests/unit/test_scene_model.py \
  backend/tests/unit/test_scene_cluster_incremental.py \
  backend/tests/unit/test_scene_cluster_algorithm_constraint.py \
  backend/tests/unit/test_scene_quality_score.py \
  backend/tests/unit/test_scene_title_rule_based.py \
  backend/tests/unit/test_aggregator_schema_v1_7.py \
  backend/tests/unit/test_scene_router_zero_hit.py \
  backend/tests/unit/test_scene_kill_switch.py \
  backend/tests/unit/test_scene_auto_downgrade.py \
  backend/tests/unit/test_rule_ak_algorithm_constraint.py \
  backend/tests/unit/test_scene_idempotency.py \
  backend/tests/unit/test_scene_user_isolation.py \
  -q

(
  cd mobile
  flutter test test/widget/scene_recent_summary_test.dart
)
