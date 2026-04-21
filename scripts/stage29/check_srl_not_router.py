#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend" / "app"
TOKENS = ("srl_phase", "SRLPhase", "srl.phase.transition", "SRLPhaseTrackerService")


def main() -> int:
    targets = list((BACKEND_ROOT / "routing").glob("*.py"))
    targets.extend((BACKEND_ROOT / "core").glob("*router*.py"))
    targets.append(BACKEND_ROOT / "orchestration" / "routing_engine.py")
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for token in TOKENS:
            if token in text:
                raise AssertionError(f"Router unexpectedly references {token}: {path}")
    print("PASS SRL router zero-hit check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
