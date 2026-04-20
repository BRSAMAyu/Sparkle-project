#!/bin/bash
set -euo pipefail

echo "[WS-SA-PUSH-CHANNEL] running delivery tests..."
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_push_delivery_service.py \
  -q
cd ..
echo "[WS-SA-PUSH-CHANNEL] ✅ done"
