#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


BANNED_PATTERNS = {
    "kmeans": "Rule AK forbids K-means or fixed-K clustering.",
    "KMeans": "Rule AK forbids K-means or fixed-K clustering.",
    "MiniBatchKMeans": "Rule AK forbids K-means or fixed-K clustering.",
    "n_clusters": "Rule AK forbids algorithms that require specifying cluster count.",
    "specify_k": "Rule AK forbids fixed-K algorithm configuration.",
}


def scan_for_rule_ak_violations(source: str) -> list[str]:
    violations: list[str] = []
    for pattern, message in BANNED_PATTERNS.items():
        if pattern in source:
            violations.append(f"{pattern}: {message}")
    return violations


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "backend" / "app" / "services" / "scene_consolidation_service.py"
    source = target.read_text(encoding="utf-8")
    violations = scan_for_rule_ak_violations(source)
    if violations:
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    print("Rule AK algorithm constraint check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
