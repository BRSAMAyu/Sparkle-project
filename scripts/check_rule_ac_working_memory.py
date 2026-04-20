#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKING_MEMORY_ROOT = REPO_ROOT / "backend/app/working_memory"
FORBIDDEN_PATTERNS = {
    "AC001": re.compile(r"\bSQLAlchemy\b"),
    "AC002": re.compile(r"\bMapped\b|\bmapped_column\b"),
    "AC003": re.compile(r"\bAlembic\b|\balembic\b"),
    "AC004": re.compile(r"\.save\s*\("),
    "AC005": re.compile(r"\.update\s*\("),
    "AC006": re.compile(r"\bINSERT\b"),
    "AC007": re.compile(r"\bUPDATE\b"),
}


def main() -> int:
    if not WORKING_MEMORY_ROOT.exists():
        print(f"[Rule AC] PASS - {WORKING_MEMORY_ROOT.relative_to(REPO_ROOT)} not present yet")
        return 0

    violations: list[str] = []
    for path in sorted(WORKING_MEMORY_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for code, pattern in FORBIDDEN_PATTERNS.items():
            for match in pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                violations.append(f"{code} {path.relative_to(REPO_ROOT)}:{line_no}")

    if violations:
        print("[Rule AC] violations found:")
        for item in violations:
            print(item)
        return 1

    print(f"[Rule AC] PASS - {WORKING_MEMORY_ROOT.relative_to(REPO_ROOT)} is transient-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
