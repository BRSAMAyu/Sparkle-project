#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


FORBIDDEN_TOKENS = (
    "openai",
    "anthropic",
    "llm_router",
    "llm_service",
    "from app.core.llm",
    "from app.services.llm",
)
TARGETS = (
    Path("backend/app/services/srl_phase_tracker_service.py"),
    Path("backend/app/services/srl_phase_types.py"),
    Path("backend/app/services/srl_phase_traits.py"),
    Path("backend/app/event_publishers/srl_events.py"),
    Path("backend/app/services/aurora_stage29_srl_kill_switch_service.py"),
)


def main() -> int:
    violations: list[str] = []
    for path in TARGETS:
        text = path.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_TOKENS:
            if token in text:
                violations.append(f"{path}:{token}")

    if violations:
        raise SystemExit("FAIL SRL no-llm import:\n" + "\n".join(violations))

    print(f"PASS SRL no-llm import: scanned={len(TARGETS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
