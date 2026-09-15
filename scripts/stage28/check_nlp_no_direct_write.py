#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / "backend" / "app" / "services" / "traits_nlp_observer_service.py"
FORBIDDEN = (".traits_prior =", "update_traits(", "traits_prior=")


def main() -> int:
    source = TARGET.read_text(encoding="utf-8")
    for token in FORBIDDEN:
        if token in source:
            raise AssertionError(f"NLP observer may directly write traits: {token}")
    print("NLP direct-write guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
