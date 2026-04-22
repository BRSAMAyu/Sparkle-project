#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export SECRET_KEY="${SECRET_KEY:-stage39-drill-secret-0123456789abcd}"
export JWT_SECRET="${JWT_SECRET:-stage39-drill-jwt-0123456789abcde}"
cd "$ROOT_DIR/backend"
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/opt/python@3.11/bin/python3.11}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

echo "[stage39] off -> shadow"
"$PYTHON_BIN" - <<'PY'
import asyncio
from app.services.aurora_stage39_kill_switch_service import AuroraStage39KillSwitchService

async def main():
    service = AuroraStage39KillSwitchService()
    await service.set_mode("shadow")
    await service.set_feature_mode("scaffolding_prompt", "live")
    await service.set_feature_mode("cogload_route", "shadow")
    await service.set_feature_mode("galaxy_inject", "shadow")
    print(await service.summary())

asyncio.run(main())
PY

echo "[stage39] shadow -> live"
"$PYTHON_BIN" - <<'PY'
import asyncio
from app.services.aurora_stage39_kill_switch_service import AuroraStage39KillSwitchService

async def main():
    service = AuroraStage39KillSwitchService()
    await service.set_mode("live")
    await service.set_feature_mode("scaffolding_prompt", "live")
    await service.set_feature_mode("cogload_route", "live")
    await service.set_feature_mode("galaxy_inject", "live")
    print(await service.summary())

asyncio.run(main())
PY

echo "[stage39] live -> shadow"
"$PYTHON_BIN" - <<'PY'
import asyncio
from app.services.aurora_stage39_kill_switch_service import AuroraStage39KillSwitchService

async def main():
    service = AuroraStage39KillSwitchService()
    await service.set_mode("shadow")
    await service.set_feature_mode("scaffolding_prompt", "live")
    await service.set_feature_mode("cogload_route", "shadow")
    await service.set_feature_mode("galaxy_inject", "shadow")
    print(await service.summary())

asyncio.run(main())
PY

echo "[stage39] shadow -> off"
"$PYTHON_BIN" - <<'PY'
import asyncio
from app.services.aurora_stage39_kill_switch_service import AuroraStage39KillSwitchService

async def main():
    service = AuroraStage39KillSwitchService()
    await service.set_mode("off")
    print(await service.summary())

asyncio.run(main())
PY
