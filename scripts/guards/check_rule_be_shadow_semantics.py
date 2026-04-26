#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    checks = {
        "backend/app/services/idiographic_association_service.py": (
            'if mode == "live":',
            "await self._upsert_daily_vectors",
            "await self.event_bus.publish",
        ),
        "backend/app/services/srl_phase_tracker_service.py": (
            'live_write = mode == "live" and tracker_mode == "live"',
            "persist_missing=live_write",
            'status="applied" if live_write else "shadow"',
        ),
        "backend/app/services/social_signal_bridge.py": (
            "AuroraStage33KillSwitchService",
            'if mode == "off":',
            'if mode != "live":',
        ),
        "backend/app/state_aggregator/service.py": (
            "AuroraStage18KillSwitchService",
            'if aggregator_mode == "off":',
            'if aggregator_mode == "shadow":',
        ),
    }
    failures: list[str] = []
    for path, needles in checks.items():
        text = _read(path)
        for needle in needles:
            if needle not in text:
                failures.append(f"{path}: missing {needle!r}")

    if failures:
        print("[Rule BE] FAIL - shadow semantics are not consistently guarded")
        for failure in failures:
            print(failure)
        return 1
    print("[Rule BE] PASS - shadow computes without live persistence/publish hooks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
