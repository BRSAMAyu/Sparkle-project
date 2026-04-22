#!/usr/bin/env python3
from __future__ import annotations

from _sqam_guard_common import find_function, guard_fail, guard_pass, load_tree


def main() -> int:
    path, source, tree = load_tree("backend/app/services/predictive_service.py")
    function_node = find_function(tree, "build_foresight_snapshot")
    if function_node is None:
        return guard_fail(
            "SQAM Predictive SM1", [f"missing build_foresight_snapshot in {path.name}"]
        )
    function_source = "\n".join(
        source.splitlines()[function_node.lineno - 1 : function_node.end_lineno]
    )
    violations: list[str] = []
    if "dropout_risk_level" not in function_source:
        violations.append(
            f"{path.name} JITAI path does not consume predictive risk_level"
        )
    if "jitai_deviations" not in function_source:
        violations.append(f"{path.name} missing guarded JITAI deviation handoff")
    if violations:
        return guard_fail("SQAM Predictive SM1", violations)
    return guard_pass(
        "SQAM Predictive SM1", "predictive risk_level now constrains JITAI handoff"
    )


if __name__ == "__main__":
    raise SystemExit(main())
