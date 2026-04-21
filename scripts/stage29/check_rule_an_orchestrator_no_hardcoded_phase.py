#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION_ROOT = REPO_ROOT / "backend" / "app" / "orchestration"
FORBIDDEN_TOKENS = (
    "SRLPhase.FORETHOUGHT",
    "SRLPhase.PERFORMANCE",
    "SRLPhase.SELF_REFLECTION",
    "SRLPhase.UNKNOWN",
)


def main() -> int:
    violations: list[str] = []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            if token in text:
                violations.append(f"{path.relative_to(REPO_ROOT)}:{token}")

    if violations:
        raise SystemExit("FAIL Rule AN orchestrator hardcoded phase:\n" + "\n".join(violations))

    print("PASS Rule AN orchestrator no hardcoded phase")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
