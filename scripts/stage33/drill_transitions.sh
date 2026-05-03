#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEFAULT_PYTHON_BIN="${REPO_ROOT}/backend/.venv/bin/python"
if [[ -x "${DEFAULT_PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-${DEFAULT_PYTHON_BIN}}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi
AUDIT_DIR="${REPO_ROOT}/artifacts/stage33"
AUDIT_FILE="${AUDIT_DIR}/drill_audit.jsonl"

mkdir -p "${AUDIT_DIR}"
: > "${AUDIT_FILE}"

export REPO_ROOT
export AUDIT_FILE

TRANSITIONS=(off shadow live shadow off)
PREV="bootstrap"

for MODE in "${TRANSITIONS[@]}"; do
  export MODE PREV
  PYTHONPATH="${REPO_ROOT}/backend" "${PYTHON_BIN}" - <<'PY'
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.services.aurora_stage33_kill_switch_service import AuroraStage33KillSwitchService


async def main() -> None:
    mode = os.environ["MODE"]
    prev = os.environ["PREV"]
    audit_file = Path(os.environ["AUDIT_FILE"])
    service = AuroraStage33KillSwitchService()
    await service.set_mode(mode)
    for feature in ("social", "srl", "wm_prompt", "events"):
        await service.set_feature_mode(feature, mode if mode != "off" else "off")
    summary = await service.summary()
    with audit_file.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "from": prev,
                    "to": mode,
                    "summary": summary,
                    "audited_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
            )
            + "\n"
        )


asyncio.run(main())
PY

  if ! tail -n 1 "${AUDIT_FILE}" | grep -q "\"to\": \"${MODE}\""; then
    echo "[Stage33 Drill] FAIL missing audit line for transition ${PREV}->${MODE}" >&2
    exit 1
  fi
  PREV="${MODE}"
done

echo "[Stage33 Drill] PASS audit_file=${AUDIT_FILE}"
