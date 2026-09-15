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


def main() -> int:
    path, _, tree = load_tree("backend/app/services/jitai_trigger_service.py")
    function_node = find_function(tree, "_mark_triggered")
    if function_node is None:
        return guard_fail("SQAM JITAI DP1", [f"missing _mark_triggered in {path.name}"])
    payload = find_publish_payload(function_node)
    if payload is None:
        return guard_fail("SQAM JITAI DP1", [f"{path.name} missing publish payload"])
    payload_keys = dict_string_keys(payload)
    violations: list[str] = []
    if "user_id" in payload_keys:
        violations.append(
            f"{path.name} publish payload still exposes plaintext user_id"
        )
    if "user_id_hash" not in payload_keys:
        violations.append(f"{path.name} publish payload must include user_id_hash")
    if violations:
        return guard_fail("SQAM JITAI DP1", violations)
    return guard_pass(
        "SQAM JITAI DP1", "JITAI event payload hashes external user identity"
    )


if __name__ == "__main__":
    raise SystemExit(main())
