#!/usr/bin/env python3
from __future__ import annotations

from _sqam_guard_common import (
    dict_string_keys,
    find_function,
    find_publish_payload,
    guard_fail,
    guard_pass,
    load_tree,
)

FORBIDDEN_KEYS = {"baseline", "variability", "recovery_rate", "confidence"}


def main() -> int:
    path, _, tree = load_tree("backend/app/services/persdyn_attractor_service.py")
    function_node = find_function(tree, "_upsert_rows")
    if function_node is None:
        return guard_fail("SQAM PersDyn DP1", [f"missing _upsert_rows in {path.name}"])
    payload = find_publish_payload(function_node)
    if payload is None:
        return guard_fail(
            "SQAM PersDyn DP1", [f"{path.name} missing event_bus.publish payload"]
        )
    payload_keys = dict_string_keys(payload)
    leaked = sorted(payload_keys & FORBIDDEN_KEYS)
    if leaked:
        return guard_fail(
            "SQAM PersDyn DP1",
            [f"{path.name} event payload leaks attractor internals: {leaked}"],
        )
    return guard_pass("SQAM PersDyn DP1", "event payload excludes baseline internals")


if __name__ == "__main__":
    raise SystemExit(main())
