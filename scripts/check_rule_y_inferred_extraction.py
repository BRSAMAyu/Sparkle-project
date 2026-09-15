#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

from ast_guard_utils import call_name, parse_module


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "backend/app/services/memory_inferred_write_lane.py"
APP_ROOT = REPO_ROOT / "backend/app"


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _validate_write_lane_guard(target: Path = TARGET) -> list[str]:
    tree = parse_module(target)
    write_candidate = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "write_candidate_to_l1"
        ),
        None,
    )
    if write_candidate is None:
        return ["RY001 missing write_candidate_to_l1"]

    has_validate = any(
        isinstance(node, ast.Call) and call_name(node) == "RuleYAdapter.validate"
        for node in ast.walk(write_candidate)
    )
    if not has_validate:
        return ["RY002 write_candidate_to_l1 must validate candidates through RuleYAdapter.validate"]
    return []


def _scan_direct_inferred_writes(app_root: Path = APP_ROOT, target: Path = TARGET) -> list[str]:
    violations: list[str] = []
    for path in sorted(app_root.rglob("*.py")):
        tree = parse_module(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if (call_name(node) or "").rsplit(".", 1)[-1] != "create_episodic_memory":
                continue
            source_lane_kw = next((kw for kw in node.keywords if kw.arg == "source_lane"), None)
            if source_lane_kw is None:
                continue
            source_text = ast.unparse(source_lane_kw.value)
            if "SOURCE_LANE" not in source_text and "inferred_extraction" not in source_text:
                continue
            if path != target:
                violations.append(
                    f"RY003 {_display_path(path)}:{getattr(node, 'lineno', '?')} "
                    "direct inferred_extraction writes must stay inside memory_inferred_write_lane.py"
                )
    return violations


def check_rule_y(target: Path = TARGET, app_root: Path = APP_ROOT) -> list[str]:
    violations = _validate_write_lane_guard(target)
    violations.extend(_scan_direct_inferred_writes(app_root, target))
    return violations


def main() -> int:
    violations = check_rule_y()
    if violations:
        print("[Rule Y] FAIL")
        for item in violations:
            print(item)
        return 1
    print("[Rule Y] PASS - inferred_extraction writes stay on the governed Rule Y path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
