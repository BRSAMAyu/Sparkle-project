#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "backend" / "app"
TARGET_FILES = [
    APP_ROOT / "services" / "conflict_resolver_service.py",
    APP_ROOT / "services" / "memory_inferred_write_lane.py",
]


def main() -> int:
    violations: list[str] = []
    for path in TARGET_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "ResolutionDecision" not in text and "conflict_resolution" not in text:
            continue
        if "record_resolution" not in text and "create_conflict_resolution_record" not in text:
            violations.append(
                f"{path.relative_to(ROOT)}: conflict override logic detected without an explicit conflict audit write"
            )

    if violations:
        print("[Rule AE] FAIL")
        for item in violations:
            print(item)
        return 1

    print("[Rule AE] PASS - conflict override paths include audit hooks or are not yet present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
