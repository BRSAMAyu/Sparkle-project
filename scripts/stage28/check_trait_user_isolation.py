#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / "backend" / "app" / "services" / "traits_nlp_observer_service.py"
REQUIRED = (
    "ChatMessage.user_id == user_id",
    "ChatMessage.role == MessageRole.USER",
)


def main() -> int:
    source = TARGET.read_text(encoding="utf-8")
    for token in REQUIRED:
        if token not in source:
            raise AssertionError(f"user isolation token missing: {token}")
    print("Trait user isolation check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
