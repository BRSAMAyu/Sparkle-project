#!/usr/bin/env python3
from __future__ import annotations

import ast

from _sqam_guard_common import (
    contains_call,
    find_function,
    guard_fail,
    guard_pass,
    load_tree,
)

REQUIRED_KEYS = {
    "study_pace",
    "completion_rate",
    "engagement_level",
    "mood_valence",
    "plan_adherence",
}


def main() -> int:
    path, _, tree = load_tree("backend/app/services/persdyn_attractor_service.py")
    function_node = find_function(tree, "_build_observation_for_day")
    violations: list[str] = []
    if function_node is None:
        return guard_fail("SQAM PersDyn ID1", [f"missing function in {path}"])

    return_nodes = [
        node
        for node in ast.walk(function_node)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
    ]
    if not return_nodes:
        return guard_fail(
            "SQAM PersDyn ID1",
            [f"{path.name} missing dict return in _build_observation_for_day"],
        )

    seen_keys: set[str] = set()
    for return_node in return_nodes:
        for key_node, value_node in zip(
            return_node.value.keys, return_node.value.values, strict=False
        ):
            if not isinstance(key_node, ast.Constant) or not isinstance(
                key_node.value, str
            ):
                continue
            key = key_node.value
            seen_keys.add(key)
            if key in REQUIRED_KEYS and not contains_call(
                value_node, "_clamp_unit_interval"
            ):
                violations.append(
                    f"{path.name}:{getattr(value_node, 'lineno', '?')} {key} is not clamped to [0,1]"
                )

    missing_keys = sorted(REQUIRED_KEYS - seen_keys)
    if missing_keys:
        violations.append(f"{path.name} missing observation keys: {missing_keys}")

    if violations:
        return guard_fail("SQAM PersDyn ID1", violations)
    return guard_pass(
        "SQAM PersDyn ID1",
        "observation outputs remain unit-clamped for all 5 dimensions",
    )


if __name__ == "__main__":
    raise SystemExit(main())
