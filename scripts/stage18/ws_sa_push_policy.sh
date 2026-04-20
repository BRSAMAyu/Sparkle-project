#!/bin/bash
set -euo pipefail

echo "[WS-SA-PUSH-POLICY] validating frozen templates..."
test -f backend/app/services/push_message_templates.v1.json
python3 - <<'PY'
import json
from pathlib import Path

path = Path("backend/app/services/push_message_templates.v1.json")
payload = json.loads(path.read_text(encoding="utf-8"))
assert len(payload) <= 8
assert all("id" in item and "policy_id" in item and "body" in item for item in payload)
PY
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_push_policy_compiler.py \
  tests/unit/test_state_driven_push_service.py \
  -q
cd ..
echo "[WS-SA-PUSH-POLICY] ✅ done"
