#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTE_HISTORY = ROOT / "backend" / "app" / "services" / "route_history_service.py"
ROUTING_ENGINE = ROOT / "backend" / "app" / "orchestration" / "routing_engine.py"


def main() -> int:
    violations: list[str] = []

    if ROUTE_HISTORY.exists():
        text = ROUTE_HISTORY.read_text(encoding="utf-8")
        if "skills_injected" not in text:
            violations.append("route history service is missing skills_injected write support")
    else:
        violations.append("missing route_history_service.py")

    if ROUTING_ENGINE.exists():
        text = ROUTING_ENGINE.read_text(encoding="utf-8")
        if "skills_injected=" not in text:
            violations.append("routing engine must explicitly write skills_injected on every decision")
    else:
        violations.append("missing routing_engine.py")

    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        if "skill_usage_history" in rel or "skill_activation_log" in rel:
            violations.append(f"parallel skill activation history path forbidden: {rel}")

    if violations:
        print("[Route History Skill Field] FAIL")
        for item in violations:
            print(item)
        return 1

    print("[Route History Skill Field] PASS - skills_injected is written via routing_decision_log only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
