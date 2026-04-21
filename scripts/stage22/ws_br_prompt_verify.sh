#!/bin/bash
set -euo pipefail

python3 scripts/check_prompt_render_coverage.py --write
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_prompt_signal_closure.py \
  tests/test_context_manager.py \
  -q
cd ..
printf '[%s] WS-BR-PROMPT-VERIFY accepted | head=%s | audit=prompt coverage baseline refreshed\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$(git rev-parse --short HEAD)" >> docs/product/stage22_progress.md
echo "[WS-BR-PROMPT-VERIFY] ✅ done"
