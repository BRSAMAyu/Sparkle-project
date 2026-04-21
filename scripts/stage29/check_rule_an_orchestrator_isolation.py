#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION_ROOT = REPO_ROOT / "backend" / "app" / "orchestration"
TRACKER_FILE = REPO_ROOT / "backend" / "app" / "services" / "srl_phase_tracker_service.py"
FORBIDDEN_TOKENS = (
    "srl_phase_tracker_service",
    "SRLPhaseTrackerService",
)


def main() -> int:
    violations: list[str] = []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            if token in text:
                violations.append(f"{path.relative_to(REPO_ROOT)}:{token}")

    tracker_text = TRACKER_FILE.read_text(encoding="utf-8")
    guard_token = 'event_type.startswith("srl.") and event_type != "srl.phase.transition"'
    if guard_token not in tracker_text:
        violations.append("backend/app/services/srl_phase_tracker_service.py:missing_self_consume_guard")

    if violations:
        raise SystemExit("FAIL Rule AN orchestrator isolation:\n" + "\n".join(violations))

    print("PASS Rule AN orchestrator isolation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
