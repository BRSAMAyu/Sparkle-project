#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "backend" / "app"
SHARE_ROOT = APP_ROOT / "services" / "skill_share"
STORE_ROOT = APP_ROOT / "services" / "skill_store"
AUTHOR_REFERENCE_PATTERN = re.compile(r"\bauthor_user_id\b")


def main() -> int:
    violations: list[str] = []

    if SHARE_ROOT.exists():
        for path in SHARE_ROOT.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "skill_store" in text:
                violations.append(
                    f"{path.relative_to(ROOT)}: Rule AF forbids skill_share importing skill_store internals"
                )

    for path in APP_ROOT.rglob("*.py"):
        if "/gen/" in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8")
        if "forked_from_share_id" not in text:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if AUTHOR_REFERENCE_PATTERN.search(line):
                violations.append(
                    f"{path.relative_to(ROOT)}:{lineno}: adopted Skill path must not preserve author_user_id"
                )

    if violations:
        print("[Rule AF Isolation] FAIL")
        for item in violations:
            print(item)
        return 1

    share_state = "present" if SHARE_ROOT.exists() else "not-yet-landed"
    store_state = "present" if STORE_ROOT.exists() else "not-yet-landed"
    print(
        f"[Rule AF Isolation] PASS - share={share_state}, store={store_state}, "
        "no forbidden author_user_id retention detected"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
