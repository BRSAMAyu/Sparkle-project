#!/usr/bin/env python3
from __future__ import annotations

import ast

from _sqam_guard_common import guard_fail, guard_pass, load_tree

TARGETS = [
    "backend/app/services/jitai_trigger_service.py",
    "backend/app/services/predictive_service.py",
    "backend/app/services/foresight_deviation_service.py",
]
OTHER_DIMS = {"study_pace", "completion_rate", "engagement_level", "plan_adherence"}


def _string_literals(node: ast.AST) -> set[str]:
    return {
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    }


def main() -> int:
    violations: list[str] = []
    for relative_path in TARGETS:
        path, _, tree = load_tree(relative_path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.IfExp, ast.Match)):
                condition_node = (
                    node.test if isinstance(node, (ast.If, ast.IfExp)) else node.subject
                )
                strings = _string_literals(condition_node)
                if "mood_valence" in strings and not (strings & OTHER_DIMS):
                    violations.append(
                        f"{path.name}:{getattr(node, 'lineno', '?')} branch references mood_valence without another PersDyn dimension"
                    )
    if violations:
        return guard_fail("SQAM PersDyn SM1", violations)
    return guard_pass(
        "SQAM PersDyn SM1",
        "no single-factor mood_valence branch detected in decision paths",
    )


if __name__ == "__main__":
    raise SystemExit(main())
