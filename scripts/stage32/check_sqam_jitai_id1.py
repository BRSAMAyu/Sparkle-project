#!/usr/bin/env python3
from __future__ import annotations

from _sqam_guard_common import find_function, guard_fail, guard_pass, load_tree


def main() -> int:
    path, source, tree = load_tree("backend/app/services/jitai_trigger_service.py")
    function_node = find_function(tree, "generate_hints")
    if function_node is None:
        return guard_fail("SQAM JITAI ID1", [f"missing generate_hints in {path.name}"])

    function_source = source[function_node.lineno - 1 :]
    violations: list[str] = []
    if "math.isfinite(z_score)" not in function_source:
        violations.append(f"{path.name} generate_hints missing finite z_score guard")
    if "math.isfinite(confidence)" not in function_source:
        violations.append(f"{path.name} generate_hints missing finite confidence guard")
    if "abs(z_score)" not in function_source:
        violations.append(
            f"{path.name} generate_hints no longer thresholds on normalized z_score"
        )

    if violations:
        return guard_fail("SQAM JITAI ID1", violations)
    return guard_pass(
        "SQAM JITAI ID1", "JITAI checks finite z_score and confidence before use"
    )


if __name__ == "__main__":
    raise SystemExit(main())
