#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "backend/app/services/error_replan_bridge.py"
FORBIDDEN = (
    re.compile(r"\bopenai\b", re.IGNORECASE),
    re.compile(r"\banthropic\b", re.IGNORECASE),
    re.compile(r"\bllm\b", re.IGNORECASE),
)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    for pattern in FORBIDDEN:
        match = pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            print(f"FAIL forbidden token {pattern.pattern} at line {line}")
            return 1
    trigger_match = re.search(r"TRIGGERING_ERROR_TYPES\s*=\s*\{([^}]+)\}", text, re.S)
    if not trigger_match:
        print("FAIL missing TRIGGERING_ERROR_TYPES")
        return 1
    raw = trigger_match.group(1)
    count = len([item for item in raw.split(",") if item.strip()])
    if count < 6:
        print(f"FAIL trigger types too small: {count}")
        return 1
    print(f"PASS trigger_types={count} file=backend/app/services/error_replan_bridge.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
