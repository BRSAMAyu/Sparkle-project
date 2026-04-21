#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / "backend" / "app" / "scaffolding" / "scaffolding_fsm.py"
FORBIDDEN_TOKENS = (
    "srl_phase_tracker_service",
    "SRLPhaseTrackerService",
)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    violations = [token for token in FORBIDDEN_TOKENS if token in text]
    if violations:
        raise SystemExit(
            "FAIL scaffolding must not import tracker:\n"
            + "\n".join(f"{TARGET.relative_to(REPO_ROOT)}:{token}" for token in violations)
        )
    print("PASS scaffolding aggregator-only tracker isolation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
