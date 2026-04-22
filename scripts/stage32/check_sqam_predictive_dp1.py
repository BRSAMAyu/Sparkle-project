#!/usr/bin/env python3
from __future__ import annotations

from _sqam_guard_common import (
    find_function,
    guard_fail,
    guard_pass,
    load_tree,
)


def main() -> int:
    path, source, tree = load_tree("backend/app/services/predictive_service.py")
    function_node = find_function(tree, "_build_realtime_llm_messages")
    if function_node is None:
        return guard_fail(
            "SQAM Predictive DP1",
            [f"missing _build_realtime_llm_messages in {path.name}"],
        )
    function_source = source.splitlines()[
        function_node.lineno - 1 : function_node.end_lineno
    ]
    joined = "\n".join(function_source)
    if "_redact_pii(partial_text)" not in joined:
        return guard_fail(
            "SQAM Predictive DP1",
            [f"{path.name} realtime LLM payload must redact PII before export"],
        )
    return guard_pass("SQAM Predictive DP1", "realtime LLM payload redacts PII")


if __name__ == "__main__":
    raise SystemExit(main())
