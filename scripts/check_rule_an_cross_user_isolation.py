#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    REPO_ROOT / "backend/app/services/idiographic_association_service.py",
    REPO_ROOT / "backend/app/services/route_history_service.py",
    REPO_ROOT / "backend/app/services/profile_context_service.py",
]
MODEL_NAMES = ("IdiographicAssociation", "IdiographicChangepoint", "DailyBehaviorVector")


def _scan_missing_user_scope(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    violations: list[str] = []
    for index, line in enumerate(lines):
        if not any(f"select({model})" in line for model in MODEL_NAMES):
            continue
        window = "\n".join(lines[index : index + 12])
        if "user_id ==" not in window and ".user_id ==" not in window:
            violations.append(
                f"AN201 {path.relative_to(REPO_ROOT)}:{index + 1} idiographic select missing explicit user_id predicate"
            )
    return violations


def _scan_cross_user_grouping(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    violations: list[str] = []
    for match in re.finditer(r"group_by\s*\(", text):
        window = text[max(0, match.start() - 120) : match.end() + 240]
        if "Idiographic" not in window and "idiographic_" not in window:
            continue
        if "user_id" not in window:
            line = text[: match.start()].count("\n") + 1
            violations.append(
                f"AN202 {path.relative_to(REPO_ROOT)}:{line} idiographic group_by missing user_id scope"
            )
    if re.search(r"select\s+\*\s+from\s+idiographic_associations?\b", text, flags=re.IGNORECASE):
        violations.append(
            f"AN203 {path.relative_to(REPO_ROOT)} raw idiographic SELECT * detected"
        )
    return violations


def main() -> int:
    violations: list[str] = []
    for path in TARGETS:
        if not path.exists():
            continue
        violations.extend(_scan_missing_user_scope(path))
        violations.extend(_scan_cross_user_grouping(path))
    if violations:
        print("[Rule AN Idiographic] FAIL")
        for item in violations:
            print(item)
        return 1
    print("[Rule AN Idiographic] PASS - idiographic access remains user-scoped and non-aggregated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
