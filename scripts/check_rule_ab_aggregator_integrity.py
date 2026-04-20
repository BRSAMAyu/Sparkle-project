#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AGGREGATOR_ROOT = REPO_ROOT / "backend/app/state_aggregator"
FORBIDDEN_PATTERNS = {
    "AB001": re.compile(r"\.save\s*\("),
    "AB002": re.compile(r"\.update\s*\("),
    "AB003": re.compile(r"\bINSERT\b"),
    "AB004": re.compile(r"\bUPDATE\b"),
}


def main() -> int:
    violations: list[str] = []
    for path in sorted(AGGREGATOR_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for code, pattern in FORBIDDEN_PATTERNS.items():
            for match in pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                violations.append(f"{code} {path.relative_to(REPO_ROOT)}:{line_no}")

    if violations:
        print("[Rule AB] violations found:")
        for item in violations:
            print(item)
        return 1

    print(f"[Rule AB] PASS - {AGGREGATOR_ROOT.relative_to(REPO_ROOT)} is read-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
