#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "backend" / "app"
ALLOWED_CONTEXT_FILES = {
    APP_ROOT / "orchestration" / "prompts.py",
}
BRANCH_PATTERN = re.compile(r"\b(if|elif|while|case)\b.*\bcontext_sufficiency\b|\bcontext_sufficiency\b.*\b(if|elif|while)\b")


def main() -> int:
    violations: list[str] = []
    for path in APP_ROOT.rglob("*.py"):
        if "/gen/" in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8")
        if "context_sufficiency" not in text:
            continue
        if path in ALLOWED_CONTEXT_FILES:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if BRANCH_PATTERN.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{lineno}: context_sufficiency may not drive control flow")

    if violations:
        print("[Rule AD] FAIL")
        for item in violations:
            print(item)
        return 1

    print("[Rule AD] PASS - context_sufficiency is not used as a branch condition")
    return 0


if __name__ == "__main__":
    sys.exit(main())
