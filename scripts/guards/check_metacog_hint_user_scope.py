#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTING_ENGINE = REPO_ROOT / "backend/app/orchestration/routing_engine.py"


def _literal_tuple(node: ast.AST) -> tuple[str, ...] | None:
    if not isinstance(node, (ast.Tuple, ast.List)):
        return None
    values: list[str] = []
    for item in node.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            return None
        values.append(item.value)
    return tuple(values)


def scan_user_scope(path: Path = ROUTING_ENGINE) -> list[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    violations: list[str] = []

    target_fn: ast.AsyncFunctionDef | None = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "RoutingEngineMixin":
            for child in node.body:
                if isinstance(child, ast.AsyncFunctionDef) and child.name == "_build_metacognition_hint":
                    target_fn = child
                    break
    if target_fn is None:
        return [f"MS001 {path.relative_to(REPO_ROOT)} missing _build_metacognition_hint"]

    get_user_state_calls = [
        node
        for node in ast.walk(target_fn)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get_user_state"
    ]
    if not get_user_state_calls:
        return [f"MS002 {path.relative_to(REPO_ROOT)} missing scoped get_user_state call"]

    call = get_user_state_calls[0]
    first_arg = call.args[0] if call.args else None
    if not (
        isinstance(first_arg, ast.Call)
        and isinstance(first_arg.func, ast.Attribute)
        and isinstance(first_arg.func.value, ast.Name)
        and first_arg.func.value.id == "uuid"
        and first_arg.func.attr == "UUID"
        and first_arg.args
        and isinstance(first_arg.args[0], ast.Name)
        and first_arg.args[0].id == "user_id"
    ):
        violations.append(
            f"MS003 {path.relative_to(REPO_ROOT)} _build_metacognition_hint must scope reads with uuid.UUID(user_id)"
        )

    required_fields_kw = next((kw for kw in call.keywords if kw.arg == "required_fields"), None)
    if required_fields_kw is None or _literal_tuple(required_fields_kw.value) != ("metacognition_profile",):
        violations.append(
            f"MS004 {path.relative_to(REPO_ROOT)} _build_metacognition_hint must request only ('metacognition_profile',)"
        )

    return violations


def main() -> int:
    violations = scan_user_scope()
    if violations:
        print("[Metacog Hint Scope] FAIL")
        for violation in violations:
            print(violation)
        return 1
    print("[Metacog Hint Scope] PASS - metacognition hint remains user-scoped and profile-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
