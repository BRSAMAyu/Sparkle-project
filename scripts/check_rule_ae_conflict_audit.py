#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

from ast_guard_utils import call_name, parse_module


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "backend/app/services/conflict_resolver_service.py"
BRANCH_GUARDED_FUNCTIONS = {
    "apply_live_decision": {"record_resolution"},
    "record_shadow_comparison": {"record_resolution"},
    "arbitrate_unresolved_conflict": {"record_resolution"},
}


def _branch_contains_required_call(branch: list[ast.stmt], required: set[str]) -> bool:
    return any(
        isinstance(node, ast.Call) and (call_name(node) or "").rsplit(".", 1)[-1] in required
        for stmt in branch
        for node in ast.walk(stmt)
    )


def check_rule_ae(path: Path) -> list[str]:
    tree = parse_module(path)
    violations: list[str] = []
    for function_name, required_calls in BRANCH_GUARDED_FUNCTIONS.items():
        function = next(
            (
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name
            ),
            None,
        )
        if function is None:
            violations.append(f"AE001 missing async function `{function_name}`")
            continue

        if function_name == "apply_live_decision":
            first_if = next((stmt for stmt in function.body if isinstance(stmt, ast.If)), None)
            if first_if is None:
                violations.append("AE002 apply_live_decision lost its decision-action branching")
                continue
            branches = [first_if.body]
            if first_if.orelse:
                if len(first_if.orelse) == 1 and isinstance(first_if.orelse[0], ast.If):
                    branches.append(first_if.orelse[0].body)
                    branches.append(first_if.orelse[0].orelse)
                else:
                    branches.append(first_if.orelse)
            for index, branch in enumerate(branches, start=1):
                if not _branch_contains_required_call(branch, required_calls):
                    violations.append(f"AE003 apply_live_decision branch {index} missing record_resolution")
        else:
            if not _branch_contains_required_call(function.body, required_calls):
                violations.append(f"AE004 {function_name} missing record_resolution")
    return violations


def main() -> int:
    violations = check_rule_ae(TARGET)
    if violations:
        print("[Rule AE] FAIL")
        for item in violations:
            print(item)
        return 1
    print("[Rule AE] PASS - conflict override branches retain explicit audit writes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
