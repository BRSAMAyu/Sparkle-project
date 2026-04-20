#!/bin/bash
set -euo pipefail

echo "[WS-WM-LLM-EXTRACT] running llm extractor tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_llm_extractor_service.py \
  -q
cd ..
test -f backend/app/services/llm_extractor_prompt.v1.md
test -f docs/product/SPARKLE_AURORA_STAGE19_LLM_EXTRACT_DRY_RUN_2026-04-21.md
echo "[WS-WM-LLM-EXTRACT] ✅ done"
