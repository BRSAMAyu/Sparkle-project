#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.user_insight_state import BigFiveDimension  # noqa: E402


def main() -> int:
    BigFiveDimension(value=0.0, confidence=0.3, evidence_count=0, source="coldstart")
    try:
        BigFiveDimension(value=0.0, confidence=0.31, evidence_count=0, source="coldstart")
    except ValueError:
        pass
    else:
        raise AssertionError("confidence 0.31 should be rejected")
    print("Rule AM confidence cap check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
