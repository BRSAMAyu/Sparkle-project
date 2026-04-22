#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

from ast_guard_utils import call_name, literal_string, parse_module, walk_parents

REPO_ROOT = Path(__file__).resolve().parents[1]
AGGREGATOR_ROOT = REPO_ROOT / "backend/app/state_aggregator"
ROUTER_TARGETS = [
    REPO_ROOT / "backend/app/orchestration/routing_engine.py",
    *sorted((REPO_ROOT / "backend/app/routing").glob("*.py")),
]
ROUTER_WHITELIST = {
    "task_sufficiency_summary": {
        "stage": "Stage 20",
        "boundary": "Router may branch only for follow-up question selection.",
    },
    "context_sufficiency_summary": {
        "stage": "Stage 20",
        "boundary": "Prompt caveat only; never a router branch condition.",
    },
    "active_skills_summary": {
        "stage": "Stage 21",
        "boundary": "Skill selection input only; may not expand beyond skill routing.",
    },
}
ALL_AGGREGATOR_FIELDS = {
    "commitment_summary",
    "pending_policies",
    "recent_reflections",
    "recent_scenes",
    "foresight_hint",
    "recent_person_mentions",
    "engagement_state",
    "learning_state",
    "working_memory_snapshot",
    "task_sufficiency_summary",
    "context_sufficiency_summary",
    "active_skills_summary",
    "achievement_summary",
    "calendar_context",
    "traits_prior",
    "srl_phase",
    "metacognition_profile",
    "idiographic_summary",
    "emotion_hint",
}
SAFE_USER_STATE_FIELDS = {"user_id", "schema_version"}
WRITE_METHODS = {"save", "update", "insert", "delete", "add", "commit", "flush"}
SQL_WRITE_TOKENS = ("INSERT ", "UPDATE ", "DELETE ")


def scan_aggregator_read_only(
    paths: list[Path] | None = None, repo_root: Path = REPO_ROOT
) -> list[str]:
    violations: list[str] = []
    scan_paths = paths or sorted(AGGREGATOR_ROOT.rglob("*.py"))
    for path in scan_paths:
        tree = parse_module(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = call_name(node) or ""
                last = name.rsplit(".", 1)[-1]
                if last in WRITE_METHODS:
                    violations.append(
                        f"AB001 {path.relative_to(repo_root)}:{getattr(node, 'lineno', '?')} forbidden call `{name}`"
                    )
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        text = str(arg.value).upper()
                        if any(token in text for token in SQL_WRITE_TOKENS):
                            violations.append(
                                f"AB002 {path.relative_to(repo_root)}:{getattr(node, 'lineno', '?')} raw SQL write token"
                            )
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = str(node.value).upper()
                if any(token in text for token in SQL_WRITE_TOKENS):
                    violations.append(
                        f"AB003 {path.relative_to(repo_root)}:{getattr(node, 'lineno', '?')} inline SQL write token"
                    )
    return violations


def _field_name_from_read(node: ast.AST) -> str | None:
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "user_state"
    ):
        if node.attr == "get":
            return None
        if node.attr in SAFE_USER_STATE_FIELDS:
            return None
        return node.attr
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "user_state"
    ):
        return literal_string(node.slice)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "user_state"
        and node.func.attr == "get"
        and node.args
    ):
        return literal_string(node.args[0])
    return None


def _is_branch_condition(node: ast.AST) -> bool:
    for parent in walk_parents(node):
        if isinstance(parent, ast.If) and node in ast.walk(parent.test):
            return True
        if isinstance(parent, ast.While) and node in ast.walk(parent.test):
            return True
        if isinstance(parent, ast.Assert) and node in ast.walk(parent.test):
            return True
        if isinstance(parent, ast.comprehension) and node in ast.walk(parent):
            return True
    return False


def scan_router_reads(
    paths: list[Path] | None = None, repo_root: Path = REPO_ROOT
) -> list[str]:
    violations: list[str] = []
    scan_paths = paths or ROUTER_TARGETS
    for path in scan_paths:
        if not path.exists():
            continue
        tree = parse_module(path)
        for node in ast.walk(tree):
            field_name = _field_name_from_read(node)
            if field_name is None:
                continue
            if field_name not in ROUTER_WHITELIST:
                violations.append(
                    f"AB101 {path.relative_to(repo_root)}:{getattr(node, 'lineno', '?')} "
                    f"router read on non-whitelisted field `{field_name}`"
                )
                continue
            if field_name == "context_sufficiency_summary" and _is_branch_condition(
                node
            ):
                violations.append(
                    f"AB102 {path.relative_to(repo_root)}:{getattr(node, 'lineno', '?')} "
                    "context_sufficiency_summary may not be used in a branch condition"
                )
    return violations


def main() -> int:
    violations = scan_aggregator_read_only()
    violations.extend(scan_router_reads())
    if violations:
        print("[Rule AB] FAIL")
        for item in violations:
            print(item)
        return 1

    print(
        "[Rule AB] PASS - aggregator remains read-only and router reads stay within the whitelist"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
