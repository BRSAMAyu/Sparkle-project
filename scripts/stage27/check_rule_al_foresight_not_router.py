#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


FORBIDDEN_TOKENS = (
    "foresight_hint",
    "build_foresight_snapshot",
    "ForesightSnapshot",
    "attractors",
    "deviations",
)


def _router_targets(repo_root: Path) -> list[Path]:
    backend_root = repo_root / "backend" / "app"
    targets = [
        backend_root / "api" / "v1" / "router.py",
        backend_root / "agents" / "graph" / "nodes" / "router.py",
        backend_root / "orchestration" / "dual_core_router.py",
        backend_root / "orchestration" / "request_router.py",
        backend_root / "orchestration" / "routing_engine.py",
    ]
    targets.extend(sorted((backend_root / "routing").glob("*.py")))
    targets.extend(sorted((backend_root / "core").glob("*router*.py")))
    return [path for path in targets if path.exists()]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    violations: list[str] = []
    for path in _router_targets(repo_root):
        source = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            if token in source:
                violations.append(f"{path.relative_to(repo_root)} -> {token}")
    if violations:
        print("Rule AL violation: router code references foresight tokens:", file=sys.stderr)
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1
    print("Rule AL router isolation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
