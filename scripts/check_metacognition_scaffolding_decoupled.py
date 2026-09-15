#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "backend/app/scaffolding/scaffolding_fsm.py"
FORBIDDEN_TOKENS = (
    "MetacognitionService",
    "metacognition_service",
)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    violations = [token for token in FORBIDDEN_TOKENS if token in text]
    if violations:
        print("[Stage 30 Decouple] FAIL")
        for token in violations:
            print(f"{TARGET.relative_to(REPO_ROOT)}:{token}")
        return 1

    print(
        "[Stage 30 Decouple] PASS - ScaffoldingFSM stays aggregator-only for metacognition"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
