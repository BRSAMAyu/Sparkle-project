#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PYTHON_BIN="$ROOT/backend/.venv/bin/python"

python3 scripts/stage24/check_rule_ai_policy_purity.py
"$PYTHON_BIN" scripts/stage24/check_policy_ir_schema.py
bash scripts/stage24/run_stage24.sh
