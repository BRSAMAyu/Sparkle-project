#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export SECRET_KEY="${SECRET_KEY:-stage38-drill-secret-0123456789abcdef}"
export JWT_SECRET="${JWT_SECRET:-stage38-drill-jwt-0123456789abcdef0}"
cd "$ROOT_DIR/backend"
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/opt/python@3.11/bin/python3.11}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

echo "[stage38] shadow baseline"
AURORA_STAGE38_ERR_REPLAN_MODE=shadow AURORA_STAGE38_PUSH_SCHEDULER_MODE=shadow EVENT_BUS_DLQ_ENABLED=true \
"$PYTHON_BIN" - <<'PY'
import asyncio
from app.config import settings
from app.core.event_bus import EventBus
from app.services.aurora_stage38_kill_switch_service import AuroraStage38KillSwitchService

async def main():
    service = AuroraStage38KillSwitchService()
    print(await service.summary())
    print({"event_bus_dlq_enabled": EventBus().dlq_enabled, "settings_dlq": settings.EVENT_BUS_DLQ_ENABLED})

asyncio.run(main())
PY

echo "[stage38] shadow -> live"
AURORA_STAGE38_ERR_REPLAN_MODE=shadow AURORA_STAGE38_PUSH_SCHEDULER_MODE=shadow EVENT_BUS_DLQ_ENABLED=true \
"$PYTHON_BIN" - <<'PY'
import asyncio
from app.services.aurora_stage38_kill_switch_service import AuroraStage38KillSwitchService

async def main():
    service = AuroraStage38KillSwitchService()
    await service.set_feature_mode("err_replan", "live")
    await service.set_feature_mode("push_scheduler", "live")
    print(await service.summary())

asyncio.run(main())
PY

echo "[stage38] live -> shadow"
AURORA_STAGE38_ERR_REPLAN_MODE=live AURORA_STAGE38_PUSH_SCHEDULER_MODE=live EVENT_BUS_DLQ_ENABLED=true \
"$PYTHON_BIN" - <<'PY'
import asyncio
from app.services.aurora_stage38_kill_switch_service import AuroraStage38KillSwitchService

async def main():
    service = AuroraStage38KillSwitchService()
    await service.set_feature_mode("err_replan", "shadow")
    await service.set_feature_mode("push_scheduler", "shadow")
    print(await service.summary())

asyncio.run(main())
PY

echo "[stage38] shadow -> off + dlq false"
AURORA_STAGE38_ERR_REPLAN_MODE=shadow AURORA_STAGE38_PUSH_SCHEDULER_MODE=shadow EVENT_BUS_DLQ_ENABLED=false \
"$PYTHON_BIN" - <<'PY'
import asyncio
from app.config import settings
from app.core.event_bus import EventBus
from app.services.aurora_stage38_kill_switch_service import AuroraStage38KillSwitchService

async def main():
    service = AuroraStage38KillSwitchService()
    await service.set_feature_mode("err_replan", "off")
    await service.set_feature_mode("push_scheduler", "off")
    print(await service.summary())
    print({"event_bus_dlq_enabled": EventBus().dlq_enabled, "settings_dlq": settings.EVENT_BUS_DLQ_ENABLED})

asyncio.run(main())
PY
