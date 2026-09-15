#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from ast_guard_utils import parse_module

TARGET = REPO_ROOT / "backend/app/core/user_insight_state.py"
SCAN_ROOTS = [REPO_ROOT / "backend/app", REPO_ROOT / "backend/tests"]
COMMENT_ALLOWLIST = "rule-am-dynamic-ok"


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _validator_caps_confidence(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "_validate_confidence":
            continue
        decorators = [ast.unparse(decorator) for decorator in node.decorator_list]
        if not any("field_validator(" in decorator and "confidence" in decorator for decorator in decorators):
            continue
        source = ast.unparse(node)
        return "0.3" in source and "numeric > 0.3" in source
    return False


def _safe_assignment_expr(function: ast.AST, name: str) -> str | None:
    for node in ast.walk(function):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.unparse(node.value)
    return None


def _expr_is_safe(expr: ast.AST, function: ast.AST, line_text: str) -> bool:
    if COMMENT_ALLOWLIST in line_text:
        return True
    if isinstance(expr, ast.Constant) and isinstance(expr.value, (int, float)):
        return float(expr.value) <= 0.3
    if isinstance(expr, ast.Name):
        assigned = _safe_assignment_expr(function, expr.id)
        if assigned is None:
            return COMMENT_ALLOWLIST in line_text
        return any(token in assigned for token in ("0.3", "0.2", "0.1", "0.05", "_clamp(", "min("))
    source = ast.unparse(expr)
    return any(token in source for token in ("0.3", "0.2", "0.1", "0.05", "_clamp(", "min("))


def check_rule_am() -> list[str]:
    target_tree = parse_module(TARGET)
    violations: list[str] = []
    if not _validator_caps_confidence(target_tree):
        violations.append("AM001 BigFiveDimension._validate_confidence must enforce the 0.3 cap")

    for root in SCAN_ROOTS:
        for path in sorted(root.rglob("*.py")):
            tree = parse_module(path)
            lines = path.read_text(encoding="utf-8").splitlines()
            for function in [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]:
                for node in ast.walk(function):
                    if not isinstance(node, ast.Call):
                        continue
                    if ast.unparse(node.func) != "BigFiveDimension":
                        continue
                    confidence_kw = next((kw for kw in node.keywords if kw.arg == "confidence"), None)
                    if confidence_kw is None:
                        continue
                    line_text = lines[getattr(node, "lineno", 1) - 1]
                    if not _expr_is_safe(confidence_kw.value, function, line_text):
                        violations.append(
                            f"AM002 {_display_path(path)}:{getattr(node, 'lineno', '?')} "
                            "BigFiveDimension confidence argument is not statically capped at <= 0.3"
                        )
    return violations


def main() -> int:
    violations = check_rule_am()
    if violations:
        print("[Rule AM] FAIL")
        for item in violations:
            print(item)
        return 1
    print("[Rule AM] PASS - BigFive confidence remains capped at 0.3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
