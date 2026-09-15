#!/usr/bin/env python3
"""GOV-013 guard: high-risk cross-user models must have minimization scopes."""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.data_minimization import TARGET_MODEL_ALIASES, TARGET_MODEL_SCOPES

REQUIRED_CANONICAL_SCOPES: set[str] = {
    "achievement",
    "causal_trace",
    "chronicle",
    "cohort_aggregate",
    "growth_chronicle",
    "intervention_episode",
    "knowledge_node",
    "policy_decision",
    "recall_opportunity",
    "relationship_model",
    "return_case_file",
    "skill_entry",
    "source_asset",
    "sprint_pack",
    "user_profile",
}

HIGH_RISK_MODEL_TERMS: set[str] = REQUIRED_CANONICAL_SCOPES | {
    "aurora_decision_telemetry",
    "counterfactual_report",
    "episodic_memory",
    "goal_world_graph",
    "growth_chronicle_snapshot",
    "intervention_audit_log",
    "intervention_outcome",
    "intervention_request",
    "knowledge_node_document",
    "learning_asset",
    "memory_goal",
    "memory_preference",
    "recommendation_cache",
    "safe_experiment_episode",
    "stored_file",
    "strategy_state",
    "user_achievement",
    "user_learning_profile",
    "user_node_status",
    "user_skill",
}

CROSS_USER_TOKENS: tuple[str, ...] = (
    "created_by",
    "first_unlocker_id",
    "owner_user_id",
    "subject_user_id",
    "user_id",
    "user_id_1",
    "user_id_2",
)


@dataclass(frozen=True)
class ModelCandidate:
    alias: str
    table_name: str
    class_name: str
    path: Path


def _snake_case(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _assigned_string(stmt: ast.stmt, target_name: str) -> str | None:
    if not isinstance(stmt, ast.Assign):
        return None
    if not any(
        isinstance(target, ast.Name) and target.id == target_name
        for target in stmt.targets
    ):
        return None
    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
        return stmt.value.value
    return None


def _class_source(source: str, node: ast.ClassDef) -> str:
    lines = source.splitlines()
    return "\n".join(lines[node.lineno - 1 : node.end_lineno or node.lineno])


def _is_high_risk_cross_user(alias: str, table_name: str, class_text: str) -> bool:
    haystack = f"{alias} {table_name} {class_text}".lower()
    has_risk_term = any(term in haystack for term in HIGH_RISK_MODEL_TERMS)
    has_cross_user_token = any(token in haystack for token in CROSS_USER_TOKENS)
    return has_risk_term and has_cross_user_token


def discover_high_risk_models(
    search_roots: tuple[Path, ...] | None = None,
) -> list[ModelCandidate]:
    roots = search_roots or (
        REPO_ROOT / "backend/app/models",
        REPO_ROOT / "backend/app/aurora/runtime_v1",
    )
    candidates: list[ModelCandidate] = []
    for root in roots:
        if root.is_file():
            paths = [root]
        else:
            paths = sorted(root.glob("*.py"))
        for path in paths:
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as exc:
                candidates.append(
                    ModelCandidate(
                        alias=f"SYNTAX_ERROR:{exc.lineno}",
                        table_name="",
                        class_name="",
                        path=path,
                    )
                )
                continue
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                table_name = next(
                    (
                        value
                        for stmt in node.body
                        if (value := _assigned_string(stmt, "__tablename__"))
                        is not None
                    ),
                    None,
                )
                if not table_name:
                    continue
                alias = _snake_case(node.name)
                if _is_high_risk_cross_user(
                    alias, table_name, _class_source(source, node)
                ):
                    candidates.append(
                        ModelCandidate(
                            alias=alias,
                            table_name=table_name,
                            class_name=node.name,
                            path=path,
                        )
                    )
    return candidates


def _canonical_scope_for(candidate: ModelCandidate) -> str | None:
    for key in (candidate.alias, candidate.table_name):
        if key in TARGET_MODEL_SCOPES:
            return key
        aliased = TARGET_MODEL_ALIASES.get(key)
        if aliased in TARGET_MODEL_SCOPES:
            return aliased
    return None


def scan_data_minimization_coverage(
    search_roots: tuple[Path, ...] | None = None,
) -> list[str]:
    failures: list[str] = []
    missing_required = sorted(REQUIRED_CANONICAL_SCOPES - set(TARGET_MODEL_SCOPES))
    for scope in missing_required:
        failures.append(f"DM001 missing required canonical scope: {scope}")

    for model in discover_high_risk_models(search_roots):
        if model.alias.startswith("SYNTAX_ERROR:"):
            failures.append(f"DM000 cannot parse {model.path}: {model.alias}")
            continue
        canonical = _canonical_scope_for(model)
        if canonical is None:
            failures.append(
                "DM002 high-risk cross-user model is not registered: "
                f"{model.class_name} alias={model.alias} table={model.table_name} path={model.path}"
            )
    return failures


def main() -> int:
    failures = scan_data_minimization_coverage()
    if failures:
        print("[GOV-DATA-MIN] FAIL - data minimization coverage gaps")
        for failure in failures:
            print(failure)
        return 1

    print(
        "[GOV-DATA-MIN] PASS - "
        f"{len(REQUIRED_CANONICAL_SCOPES)} canonical scopes and "
        f"{len(discover_high_risk_models())} high-risk model aliases covered"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
