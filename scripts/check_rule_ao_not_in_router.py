#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTER_TARGETS = [
    REPO_ROOT / "backend/app/orchestration/routing_engine.py",
    *sorted((REPO_ROOT / "backend/app/routing").glob("*.py")),
]
FORBIDDEN_TOKENS = {
    "metacognition_dashboard",
    "metacognition_process_scaffolding",
}


def _string_hits(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value.strip()
            if value in FORBIDDEN_TOKENS:
                hits.append(
                    f"{path.relative_to(REPO_ROOT)}:{getattr(node, 'lineno', '?')}:{value}"
                )
    return hits


def main() -> int:
    violations: list[str] = []
    for path in ROUTER_TARGETS:
        if not path.exists():
            continue
        violations.extend(f"AO101 {item}" for item in _string_hits(path))

    if violations:
        print("[Rule AO Router] FAIL")
        for item in violations:
            print(item)
        return 1

    print("[Rule AO Router] PASS - router only consumes the bounded Stage35 metacognition hint path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
