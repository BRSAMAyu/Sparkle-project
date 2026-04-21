#!/bin/bash
set -euo pipefail

STAGE="stage22"
LOG_DIR="logs/${STAGE}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

python3 scripts/render_stage22_precheck.py > "$LOG_DIR/precheck.log" 2>&1
python3 scripts/check_prompt_render_coverage.py --write > "$LOG_DIR/prompt_coverage.log" 2>&1
python3 scripts/check_error_replan_trigger_purity.py > "$LOG_DIR/error_purity.log" 2>&1

test -f docs/product/SPARKLE_AURORA_STAGE22_DISPATCH_PLAN_2026-04-21.md
test -f docs/product/SPARKLE_AURORA_ROADMAP_v2_1_FAST_DEV_LOCK_2026-04-21.md
test -f docs/product/stage22_precheck.md
test -f docs/product/stage22_prompt_coverage_baseline.md

echo "[Gate S22-0] ✅ passed"

bash scripts/stage22/ws_br_prompt_verify.sh
bash scripts/stage22/ws_br_loop_closure.sh
bash scripts/stage22/ws_br_achievement_wire.sh
bash scripts/stage22/ws_br_calendar_wire.sh
bash scripts/stage22/ws_br_intervention_q.sh
bash scripts/stage22/ws_br_seed_verify.sh
bash scripts/stage22/gate_final.sh

echo "[Stage 22] ✅ ALL WS PASSED"
