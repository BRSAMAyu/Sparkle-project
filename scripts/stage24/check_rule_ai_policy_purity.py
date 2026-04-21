#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    REPO_ROOT / "backend/app/services/policy_compiler_service.py",
    REPO_ROOT / "backend/app/services/policy_scheduler_service.py",
]
FORBIDDEN_IMPORTS = (
    "llm",
    "openai",
    "anthropic",
    "deepseek",
    "qwen",
    "glm",
)


def main() -> int:
    violations: list[str] = []
    for path in TARGETS:
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_IMPORTS:
            for line_no, line in enumerate(text.splitlines(), start=1):
                normalized = line.strip().lower()
                if not normalized.startswith(("import ", "from ")):
                    continue
                if token in normalized:
                    violations.append(f"{path}:{line_no}:{line.strip()}")
    if violations:
        print("Rule AI purity violated:")
        for violation in violations:
            print(violation)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
