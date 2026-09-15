#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TRACKER = REPO_ROOT / "backend" / "app" / "services" / "srl_phase_tracker_service.py"
REQUIRED_SNIPPETS = (
    'raise ValueError("user_id is required")',
    "SRLPhaseStateRecord.user_id == user_id",
    "UserPreferencesCenter.user_id == user_id",
)


def main() -> int:
    text = TRACKER.read_text(encoding="utf-8")
    missing = [snippet for snippet in REQUIRED_SNIPPETS if snippet not in text]
    if missing:
        raise SystemExit(
            "FAIL SRL user isolation guard:\n"
            + "\n".join(f"missing:{snippet}" for snippet in missing)
        )
    print("PASS SRL user isolation guard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
