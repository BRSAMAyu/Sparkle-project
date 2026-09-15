#!/usr/bin/env python3
from __future__ import annotations

from _sqam_guard_common import find_function, guard_fail, guard_pass, load_tree


def main() -> int:
    path, source, tree = load_tree("backend/app/services/srl_phase_tracker_service.py")
    function_node = find_function(tree, "handle_transition_event")
    if function_node is None:
        return guard_fail(
            "SQAM SRL DP1", [f"missing handle_transition_event in {path.name}"]
        )
    function_source = "\n".join(
        source.splitlines()[function_node.lineno - 1 : function_node.end_lineno]
    )
    if "_is_valid_evidence_id(evidence_id)" not in function_source:
        return guard_fail(
            "SQAM SRL DP1", [f"{path.name} missing evidence_id format validation"]
        )
    return guard_pass(
        "SQAM SRL DP1", "SRL transition events validate evidence_id format"
    )


if __name__ == "__main__":
    raise SystemExit(main())
