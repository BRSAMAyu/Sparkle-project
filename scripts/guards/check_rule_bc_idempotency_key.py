#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGETS = {
    REPO_ROOT / "backend/app/api/v1/shop.py": ("purchase_item",),
    REPO_ROOT / "backend/app/api/v1/photons.py": ("transfer_photons", "adjust_photons"),
    REPO_ROOT / "backend/app/api/v1/achievements.py": (
        "create_contract",
        "cancel_contract",
        "process_achievement_event",
    ),
}


def scan_rule_bc(
    targets: dict[Path, tuple[str, ...]] = TARGETS,
) -> list[str]:
    violations: list[str] = []
    for path, function_names in targets.items():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        functions = {
            node.name: ast.get_source_segment(source, node) or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef)
        }
        for function_name in function_names:
            function_source = functions.get(function_name, "")
            if not function_source:
                violations.append(f"BC001 missing handler `{function_name}` in {path}")
                continue
            if "Idempotency-Key" not in function_source:
                violations.append(
                    f"BC002 handler `{function_name}` does not parse Idempotency-Key in {path}"
                )
    return violations


def main() -> int:
    violations = scan_rule_bc()
    if violations:
        print("[Rule BC] FAIL")
        for violation in violations:
            print(violation)
        return 1
    print("[Rule BC] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
