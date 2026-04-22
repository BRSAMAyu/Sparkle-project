#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export SECRET_KEY="${SECRET_KEY:-stage34-drill-secret-0123456789abcd}"
export JWT_SECRET="${JWT_SECRET:-stage34-drill-jwt-0123456789abcde}"
cd "$ROOT_DIR/backend"
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/opt/python@3.11/bin/python3.11}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

echo "[stage34] off -> shadow"
"$PYTHON_BIN" - <<'PY'
import asyncio
from app.services.aurora_stage34_kill_switch_service import AuroraStage34KillSwitchService

async def main():
    service = AuroraStage34KillSwitchService()
    await service.set_mode("shadow")
    await service.set_feature_mode("error_bridge", "shadow")
    await service.set_feature_mode("capsule", "shadow")
    await service.set_feature_mode("journey_subscribers", "live")
    print(await service.summary())

asyncio.run(main())
PY

echo "[stage34] shadow -> live"
"$PYTHON_BIN" - <<'PY'
import asyncio
from app.services.aurora_stage34_kill_switch_service import AuroraStage34KillSwitchService

async def main():
    service = AuroraStage34KillSwitchService()
    await service.set_mode("live")
    await service.set_feature_mode("error_bridge", "live")
    await service.set_feature_mode("capsule", "live")
    await service.set_feature_mode("journey_subscribers", "live")
    print(await service.summary())

asyncio.run(main())
PY

echo "[stage34] live -> shadow"
"$PYTHON_BIN" - <<'PY'
import asyncio
from app.services.aurora_stage34_kill_switch_service import AuroraStage34KillSwitchService

async def main():
    service = AuroraStage34KillSwitchService()
    await service.set_mode("shadow")
    await service.set_feature_mode("error_bridge", "shadow")
    await service.set_feature_mode("capsule", "shadow")
    await service.set_feature_mode("journey_subscribers", "live")
    print(await service.summary())

asyncio.run(main())
PY

echo "[stage34] shadow -> off"
"$PYTHON_BIN" - <<'PY'
import asyncio
from app.services.aurora_stage34_kill_switch_service import AuroraStage34KillSwitchService

async def main():
    service = AuroraStage34KillSwitchService()
    await service.set_mode("off")
    print(await service.summary())

asyncio.run(main())
PY
