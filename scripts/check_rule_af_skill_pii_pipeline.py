#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_FILES = [
    ROOT / "backend" / "app" / "services" / "skill_share_service.py",
    ROOT / "backend" / "app" / "services" / "skill_share" / "service.py",
]
REQUIRED_TOKENS = (
    "scan_for_pii",
    "detect_injection",
    "enqueue_for_moderation",
)


def main() -> int:
    existing = [path for path in TARGET_FILES if path.exists()]
    if not existing:
        print("[Rule AF Pipeline] FAIL - skill sharing service missing")
        return 1

    violations: list[str] = []
    for path in existing:
        text = path.read_text(encoding="utf-8")
        missing = [token for token in REQUIRED_TOKENS if token not in text]
        if missing:
            violations.append(f"{path.relative_to(ROOT)} missing pipeline steps: {', '.join(missing)}")

    if violations:
        print("[Rule AF Pipeline] FAIL")
        for item in violations:
            print(item)
        return 1

    print("[Rule AF Pipeline] PASS - sharing publish path includes PII, injection, moderation steps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
