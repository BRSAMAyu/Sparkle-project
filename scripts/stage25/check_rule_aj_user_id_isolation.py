#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from ast_guard_utils import call_name, parse_module

TARGET = REPO_ROOT / "backend/app/services/route_history_service.py"
PUBLIC_READ_METHODS = {"read_recent_decisions", "read_decision_chain"}
USER_SCOPED_HELPERS = {"_load_decision_for_user", "_load_related_decisions"}


def _has_user_id_arg(function: ast.AsyncFunctionDef) -> bool:
    args = [arg.arg for arg in function.args.args]
    return "user_id" in args


def _calls_require_user_id(function: ast.AsyncFunctionDef) -> bool:
    return any(
        isinstance(node, ast.Call)
        and (call_name(node) or "").rsplit(".", 1)[-1] == "_require_user_id"
        for node in ast.walk(function)
    )


def _function_calls(function: ast.AsyncFunctionDef) -> set[str]:
    calls: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            name = call_name(node)
            if name:
                calls.add(name.rsplit(".", 1)[-1])
    return calls


def _has_user_filter(function: ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(function):
        if not isinstance(node, ast.Compare):
            continue
        left = ast.unparse(node.left)
        comparators = [ast.unparse(item) for item in node.comparators]
        if "RoutingDecisionLog.user_id" in left and any("user_id" in item for item in comparators):
            return True
    return False


def check_rule_aj(path: Path) -> list[str]:
    tree = parse_module(path)
    violations: list[str] = []

    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
    }

    for name in PUBLIC_READ_METHODS:
        function = functions.get(name)
        if function is None:
            violations.append(f"AJ001 missing public read method `{name}`")
            continue
        if not _has_user_id_arg(function):
            violations.append(f"AJ002 {name} must require user_id")
        if not _calls_require_user_id(function):
            violations.append(f"AJ003 {name} must normalize user_id through _require_user_id")
        calls = _function_calls(function)
        if name == "read_recent_decisions" and not _has_user_filter(function):
            violations.append("AJ004 read_recent_decisions query must filter RoutingDecisionLog.user_id")
        if name == "read_decision_chain" and not USER_SCOPED_HELPERS.issubset(calls):
            violations.append(
                "AJ005 read_decision_chain must rely on user-scoped helpers for direct and related decision reads"
            )

    for helper_name in USER_SCOPED_HELPERS:
        function = functions.get(helper_name)
        if function is None:
            violations.append(f"AJ006 missing user-scoped helper `{helper_name}`")
            continue
        if not _has_user_filter(function):
            violations.append(f"AJ007 {helper_name} must filter RoutingDecisionLog.user_id")

    return violations


def main() -> int:
    violations = check_rule_aj(TARGET)
    if violations:
        print("[Rule AJ] FAIL")
        for item in violations:
            print(item)
        return 1
    print("[Rule AJ] PASS - route history read APIs remain user-scoped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
