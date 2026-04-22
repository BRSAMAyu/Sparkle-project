#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = REPO_ROOT / "backend/app/services/idiographic_association_service.py"
PROMPTS_PATH = REPO_ROOT / "backend/app/orchestration/prompts.py"
SCHEMA_PATH = REPO_ROOT / "backend/app/state_aggregator/schema.py"
FORBIDDEN_IMPORT_TOKENS = {
    "CausalInference",
    "TreatmentEffect",
    "PropensityScore",
    "do_calculus",
}
BANNED_CAUSAL_PATTERNS = [
    r"因为",
    r"导致",
    r"所以",
    r"因此",
    r"使得",
    r"改善了",
    r"提高了",
    r"降低了",
    r"\bcauses?\b",
    r"\bbecause of\b",
    r"\bled to\b",
    r"\bresults? in\b",
]
REQUIRED_DISCLAIMER = "这只是你数据中的模式，不代表因果关系"


def _scan_forbidden_imports() -> list[str]:
    tree = ast.parse(SERVICE_PATH.read_text(encoding="utf-8"), filename=str(SERVICE_PATH))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = {alias.name.split(".")[-1] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            names = {alias.name for alias in node.names}
        else:
            continue
        bad = sorted(name for name in names if name in FORBIDDEN_IMPORT_TOKENS)
        if bad:
            violations.append(
                f"AP001 {SERVICE_PATH.relative_to(REPO_ROOT)}:{getattr(node, 'lineno', '?')} forbidden import(s): {bad}"
            )
    return violations


def _scan_causal_language() -> list[str]:
    violations: list[str] = []
    for path in (SERVICE_PATH, PROMPTS_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            value = node.value.strip()
            if not value:
                continue
            for pattern in BANNED_CAUSAL_PATTERNS:
                if re.search(pattern, value, flags=re.IGNORECASE):
                    violations.append(
                        f"AP002 {path.relative_to(REPO_ROOT)}:{getattr(node, 'lineno', '?')} banned causal language `{pattern}`"
                    )
                    break
    return violations


def _scan_disclaimer_contract() -> list[str]:
    tree = ast.parse(SCHEMA_PATH.read_text(encoding="utf-8"), filename=str(SCHEMA_PATH))
    fields: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "IdiographicSummaryValue":
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                fields.add(stmt.target.id)
    violations: list[str] = []
    if "disclaimer_text" not in fields:
        violations.append("AP003 schema.py IdiographicSummaryValue must include disclaimer_text")
    service_text = SERVICE_PATH.read_text(encoding="utf-8")
    if REQUIRED_DISCLAIMER not in service_text:
        violations.append("AP004 idiographic_association_service.py missing required disclaimer text")
    return violations


def main() -> int:
    violations = []
    violations.extend(_scan_forbidden_imports())
    violations.extend(_scan_causal_language())
    violations.extend(_scan_disclaimer_contract())
    if violations:
        print("[Rule AP] FAIL")
        for item in violations:
            print(item)
        return 1
    print("[Rule AP] PASS - idiographic association layer stays associative, templated, and disclaimed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
