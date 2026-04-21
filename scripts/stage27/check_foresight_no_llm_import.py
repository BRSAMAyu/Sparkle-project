#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


FORBIDDEN_TOKENS = (
    "openai",
    "anthropic",
    "llm_router",
    "get_llm_service",
    "chat_completion",
    "responses.create",
)

TARGETS = (
    "backend/app/services/persdyn_attractor_service.py",
    "backend/app/services/foresight_deviation_service.py",
    "backend/app/services/jitai_trigger_service.py",
    "backend/app/services/aurora_stage27_foresight_kill_switch_service.py",
    "backend/app/models/aurora_stage27.py",
    "backend/app/schemas/foresight.py",
)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    violations: list[str] = []
    for relative_path in TARGETS:
        path = repo_root / relative_path
        source = path.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_TOKENS:
            if token in source:
                violations.append(f"{relative_path} -> {token}")
    if violations:
        print("Foresight no-LLM import check failed:", file=sys.stderr)
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1
    print("Foresight no-LLM import check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
