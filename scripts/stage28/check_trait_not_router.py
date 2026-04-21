#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend" / "app"
TOKENS = ("traits_prior", "BigFiveTraits", "TraitPrior")


def main() -> int:
    targets = list((BACKEND_ROOT / "routing").glob("*.py"))
    targets.extend((BACKEND_ROOT / "core").glob("*router*.py"))
    targets.append(BACKEND_ROOT / "orchestration" / "routing_engine.py")
    for path in targets:
        source = path.read_text(encoding="utf-8")
        for token in TOKENS:
            if token in source:
                raise AssertionError(f"Router unexpectedly references {token}: {path}")
    print("Trait router zero-hit check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
