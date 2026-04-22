#!/usr/bin/env python3
from __future__ import annotations

from _sqam_guard_common import find_function, guard_fail, guard_pass, load_tree


def main() -> int:
    path, source, tree = load_tree(
        "backend/app/services/idiographic_association_service.py"
    )
    function_node = find_function(tree, "_select_top_associations")
    if function_node is None:
        return guard_fail(
            "SQAM Idiographic SM1", [f"missing _select_top_associations in {path.name}"]
        )
    function_source = "\n".join(
        source.splitlines()[function_node.lineno - 1 : function_node.end_lineno]
    )
    violations: list[str] = []
    if "non_mood" not in function_source or "mood" not in function_source:
        violations.append(
            f"{path.name} must continue deprioritizing mood_valence-only associations"
        )
    if "CONFIDENCE_CAP = 0.80" not in source and "CONFIDENCE_CAP = 0.8" not in source:
        violations.append(f"{path.name} idiographic confidence cap must stay at 0.80")
    if violations:
        return guard_fail("SQAM Idiographic SM1", violations)
    return guard_pass(
        "SQAM Idiographic SM1",
        "idiographic selection keeps mood de-prioritization and 0.80 cap",
    )


if __name__ == "__main__":
    raise SystemExit(main())
