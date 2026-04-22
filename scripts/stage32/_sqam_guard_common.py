from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_path(relative_path: str) -> Path:
    return REPO_ROOT / relative_path


def load_source(relative_path: str) -> tuple[Path, str]:
    path = repo_path(relative_path)
    return path, path.read_text(encoding="utf-8")


def load_tree(relative_path: str) -> tuple[Path, str, ast.AST]:
    path, source = load_source(relative_path)
    return path, source, ast.parse(source, filename=str(path))


def find_function(
    tree: ast.AST, name: str
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return node
    return None


def contains_call(node: ast.AST, func_name: str) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name) and func.id == func_name:
            return True
        if isinstance(func, ast.Attribute) and func.attr == func_name:
            return True
    return False


def find_publish_payload(function_node: ast.AST) -> ast.Dict | None:
    for child in ast.walk(function_node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if not isinstance(func, ast.Attribute) or func.attr != "publish":
            continue
        if len(child.args) < 2 or not isinstance(child.args[1], ast.Dict):
            continue
        return child.args[1]
    return None


def dict_string_keys(node: ast.Dict) -> set[str]:
    keys: set[str] = set()
    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.add(key.value)
    return keys


def guard_fail(label: str, violations: list[str]) -> int:
    print(f"[{label}] FAIL")
    for item in violations:
        print(item)
    return 1


def guard_pass(label: str, message: str) -> int:
    print(f"[{label}] PASS - {message}")
    return 0
