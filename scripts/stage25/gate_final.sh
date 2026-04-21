#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PYTHON_BIN="$ROOT/backend/.venv/bin/python"

python3 scripts/stage25/check_rule_aj_user_id_isolation.py
"$PYTHON_BIN" scripts/stage25/check_reflection_trigger_registry.py
python3 scripts/stage25/check_reflection_user_id_propagation.py
bash scripts/stage25/run_stage25.sh
