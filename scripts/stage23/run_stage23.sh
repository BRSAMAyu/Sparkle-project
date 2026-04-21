#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

bash scripts/stage23/ws_by_source_state_design.sh
bash scripts/stage23/ws_by_source_state_impl.sh
bash scripts/stage23/ws_by_data_bootstrap.sh
bash scripts/stage23/ws_by_outcome.sh
bash scripts/stage23/ws_by_wire.sh
bash scripts/stage23/ws_by_kill.sh
bash scripts/stage23/gate_final.sh
PYTHONPATH=backend python3 scripts/stage23/render_stage23_handoff.py

echo "Stage 23 PASS"
