#!/usr/bin/env python3
from __future__ import annotations

from _sqam_guard_common import find_function, guard_fail, guard_pass, load_tree


def main() -> int:
    path, source, tree = load_tree("backend/app/services/persdyn_attractor_service.py")
    function_node = find_function(tree, "_ema")
    if function_node is None:
        return guard_fail("SQAM PersDyn ST1", [f"missing _ema in {path.name}"])
    if "math.isfinite" not in source[function_node.col_offset :]:
        return guard_fail(
            "SQAM PersDyn ST1",
            [f"{path.name} _ema must guard non-finite values with math.isfinite"],
        )
    return guard_pass("SQAM PersDyn ST1", "EMA contains finite-value guarding")


if __name__ == "__main__":
    raise SystemExit(main())
