#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / "backend/app/services/route_history_service.py"

REQUIRED_SNIPPETS = (
    "def _require_user_id(",
    "RoutingDecisionLog.user_id == normalized_user_id",
    "RoutingDecisionLog.user_id == user_id",
    "raise ValueError(\"RouteHistoryService read APIs require a non-empty user_id\")",
)


def main() -> int:
    if not TARGET.exists():
        print("missing route_history_service.py")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    missing = [snippet for snippet in REQUIRED_SNIPPETS if snippet not in text]
    if missing:
        print("Rule AJ isolation drift detected:")
        for snippet in missing:
            print(f"- missing snippet: {snippet}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
