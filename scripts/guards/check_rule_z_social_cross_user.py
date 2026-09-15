#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / "backend/app/services/social_signal_bridge.py"
REQUIRED_TOKENS = (
    "async def _fetch_for_user(self, user_id: UUID)",
    "fetch_social_snapshot(user_id)",
    "get_preferences(user_id)",
)
FORBIDDEN_TOKENS = (
    "metacognition",
    "traits_prior",
    "trait_observation_state",
    "other_user_id",
)


def scan_social_cross_user(target: Path = TARGET) -> list[str]:
    text = target.read_text(encoding="utf-8")
    violations: list[str] = []
    for token in REQUIRED_TOKENS:
        if token not in text:
            violations.append(f"ZS001 missing required token `{token}` in {target}")
    for token in FORBIDDEN_TOKENS:
        if token in text:
            violations.append(f"ZS002 forbidden token `{token}` present in {target}")
    return violations


def main() -> int:
    violations = scan_social_cross_user()
    if violations:
        print("[Rule Z social] FAIL")
        for violation in violations:
            print(violation)
        return 1
    print("[Rule Z social] PASS - social bridge remains user-scoped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
