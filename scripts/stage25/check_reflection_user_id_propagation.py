#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    REPO_ROOT / "backend/app/agents/graph/nodes/review_nodes.py",
    REPO_ROOT / "backend/app/agents/reflection_agent.py",
]


class ReflectionCallVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violations: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"reflect", "reflect_and_fix"}:
            keyword_names = {kw.arg for kw in node.keywords if kw.arg is not None}
            if "user_id" not in keyword_names:
                self.violations.append(f"line {node.lineno}: missing user_id on {func.attr}()")
        self.generic_visit(node)


def main() -> int:
    violations: list[str] = []
    for path in TARGETS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = ReflectionCallVisitor()
        visitor.visit(tree)
        violations.extend(f"{path}:{item}" for item in visitor.violations)
    if violations:
        print("Reflection user_id propagation drift detected:")
        for violation in violations:
            print(violation)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
