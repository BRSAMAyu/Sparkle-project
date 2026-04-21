#!/bin/bash
set -euo pipefail

echo "[WS-SK-SCHEMA] running schema and store tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_skill_schema_contract.py \
  tests/unit/test_skill_store_service.py \
  tests/unit/test_skills_api.py \
  -q
cd ..
printf '[%s] WS-SK-SCHEMA accepted | commits: %s | tests: 3 files green\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" \
  "$(git rev-parse --short HEAD)" >> docs/product/stage21_progress.md
echo "[WS-SK-SCHEMA] ✅ done"
