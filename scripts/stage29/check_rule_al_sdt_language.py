#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_PHRASES = ("你必须", "你应该", "你一定要", "你不可以不")
TARGETS = (
    REPO_ROOT / "backend" / "app" / "orchestration" / "prompts.py",
    REPO_ROOT / "backend" / "app" / "orchestration" / "multi_agent_adapter.py",
)


def main() -> int:
    violations: list[str] = []
    for path in TARGETS:
        text = path.read_text(encoding="utf-8")
        for phrase in FORBIDDEN_PHRASES:
            if phrase in text:
                violations.append(f"{path.relative_to(REPO_ROOT)}:{phrase}")

    if violations:
        raise SystemExit("FAIL Rule AL SDT language:\n" + "\n".join(violations))

    print("PASS Rule AL SDT language")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
