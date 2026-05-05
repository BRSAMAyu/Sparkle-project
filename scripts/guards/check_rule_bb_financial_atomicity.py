#!/usr/bin/env python3
"""Rule BB: Financial atomicity guard.

Verifies that photon deduction is atomic with balance guard:
1. _deduct_balance_atomically exists as a method in PhotonService
2. The method contains a WHERE balance >= amount guard
3. The method contains a RETURNING clause for verification
4. Achievement engine uses transaction-managed external grants

Layer 1: Quick string presence check (fast fail)
Layer 2: AST-level verification of method structure
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PHOTON_SERVICE = REPO_ROOT / "backend/app/services/photon_service.py"
DEFAULT_ACHIEVEMENT_ENGINE = REPO_ROOT / "backend/app/services/achievement_engine.py"


def _extract_method_source(source: str, class_name: str, method_name: str) -> str | None:
    """Extract the source lines of a specific method using AST."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method_name:
                    lines = source.splitlines()
                    start = item.body[0].lineno - 1
                    end = item.end_lineno or len(lines)
                    return "\n".join(lines[start:end])
    return None


def scan_rule_bb(
    *,
    photon_service: Path = DEFAULT_PHOTON_SERVICE,
    achievement_engine: Path = DEFAULT_ACHIEVEMENT_ENGINE,
) -> list[str]:
    violations: list[str] = []
    photon_source = photon_service.read_text(encoding="utf-8")
    achievement_source = achievement_engine.read_text(encoding="utf-8")

    # Layer 1: Quick string presence (fast fail for missing functions)
    photon_required = (
        "_deduct_balance_atomically",
        "update(User)",
    )
    for token in photon_required:
        if token not in photon_source:
            violations.append(f"BB001 missing token `{token}` in {photon_service}")

    achievement_required = (
        "_EXTERNAL_TRANSACTION_MANAGED_KEY",
        "begin_nested",
        "grant_photons",
    )
    for token in achievement_required:
        if token not in achievement_source:
            violations.append(f"BB002 missing token `{token}` in {achievement_engine}")

    # Early return if basic structure is missing
    if violations:
        return violations

    # Layer 2: AST-level verification of _deduct_balance_atomically
    method_body = _extract_method_source(photon_source, "PhotonService", "_deduct_balance_atomically")
    if method_body is None:
        # Try without class context — method may be standalone or on different class
        method_body = _extract_method_source(photon_source, None, "_deduct_balance_atomically")  # type: ignore[arg-type]

    if method_body is not None:
        # Verify the method body contains the critical SQL safety clauses
        critical_clauses = {
            "photon_balance >= amount": "balance guard (WHERE balance >= amount)",
            ".returning(": "RETURNING clause for verification",
        }
        for clause, description in critical_clauses.items():
            if clause not in method_body and clause.replace(" ", "") not in method_body.replace(" ", ""):
                violations.append(
                    f"BB003 _deduct_balance_atomically missing {description} (`{clause}`)"
                )
    else:
        # Fallback: verify via full-file string that critical clauses exist near the method
        violations.append(
            "BB003 could not locate _deduct_balance_atomically for AST verification"
        )

    return violations


def main() -> int:
    violations = scan_rule_bb()
    if violations:
        print("[Rule BB] FAIL")
        for violation in violations:
            print(violation)
        return 1
    print("[Rule BB] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
