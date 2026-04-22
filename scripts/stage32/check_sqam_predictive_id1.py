#!/usr/bin/env python3
from __future__ import annotations

from _sqam_guard_common import find_function, guard_fail, guard_pass, load_tree


def main() -> int:
    path, source, tree = load_tree("backend/app/services/predictive_service.py")
    function_node = find_function(tree, "get_prediction_analytics")
    if function_node is None:
        return guard_fail(
            "SQAM Predictive ID1", [f"missing get_prediction_analytics in {path.name}"]
        )
    function_source = source[function_node.lineno - 1 :]
    if '"ctr"' not in function_source and '"ctr_percent"' not in function_source:
        return guard_fail(
            "SQAM Predictive ID1",
            [f"{path.name} get_prediction_analytics must expose ctr/ctr_percent"],
        )
    return guard_pass("SQAM Predictive ID1", "prediction analytics exposes CTR fields")


if __name__ == "__main__":
    raise SystemExit(main())
