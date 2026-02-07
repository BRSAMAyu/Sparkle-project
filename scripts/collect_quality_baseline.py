#!/usr/bin/env python3
"""Collect and optionally validate project quality baseline metrics."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path


METRICS = {
    "backend_datetime_utcnow": "rg -n \"datetime\\.utcnow\\(\" backend/app backend/tests | wc -l",
    "backend_pydantic_class_config": "rg -n \"class Config:\" backend/app backend/tests | wc -l",
    "backend_pydantic_json_encoders": "rg -n \"json_encoders\" backend/app backend/tests | wc -l",
    "backend_pydantic_min_items": "rg -n \"min_items=\" backend/app backend/tests | wc -l",
    "backend_asyncmock_unawaited_test_refs": "rg -n \"AsyncMock was never awaited\" backend/tests | wc -l",
}


COMMANDS = {
    "backend_pytest": "cd backend && pytest -q",
    "gateway_go_test": "cd backend/gateway && go test ./...",
    "flutter_tests": "cd mobile && flutter test -r compact",
    "compose_smoke": "make smoke",
}


def _run_int(command: str) -> int:
    proc = subprocess.run(command, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"metric command failed: {command}\n{proc.stderr.strip()}")
    return int(proc.stdout.strip())


def _run_check(command: str) -> dict:
    proc = subprocess.run(command, shell=True, capture_output=True, text=True)
    return {
        "command": command,
        "exit_code": proc.returncode,
        "stdout_tail": "\n".join(proc.stdout.strip().splitlines()[-20:]),
        "stderr_tail": "\n".join(proc.stderr.strip().splitlines()[-20:]),
        "ok": proc.returncode == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect Sparkle quality baseline")
    parser.add_argument("--output", default="quality/baseline_snapshot.json", help="Output JSON path")
    parser.add_argument(
        "--run-checks",
        action="store_true",
        help="Run expensive validation commands (pytest/go test/flutter test/smoke)",
    )
    args = parser.parse_args()

    snapshot = {
        "generated_at": datetime.now(UTC).isoformat(),
        "metrics": {},
        "checks": {},
    }

    for metric, cmd in METRICS.items():
        snapshot["metrics"][metric] = _run_int(cmd)

    if args.run_checks:
        for name, cmd in COMMANDS.items():
            snapshot["checks"][name] = _run_check(cmd)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Baseline written to {output}")
    print(json.dumps(snapshot["metrics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
