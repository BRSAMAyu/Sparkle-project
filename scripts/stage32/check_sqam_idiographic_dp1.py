#!/usr/bin/env python3
from __future__ import annotations

from _sqam_guard_common import (
    find_function,
    guard_fail,
    guard_pass,
    load_source,
    load_tree,
)


def main() -> int:
    service_path, service_source, _ = load_tree(
        "backend/app/services/idiographic_association_service.py"
    )
    schema_path, schema_source = load_source("backend/app/state_aggregator/schema.py")
    violations: list[str] = []
    if "DISCLAIMER_TEXT" not in service_source:
        violations.append(f"{service_path.name} missing disclaimer constant")
    if "disclaimer_text" not in schema_source:
        violations.append(f"{schema_path.name} missing disclaimer_text field")
    function_node = find_function(
        load_tree("backend/app/services/idiographic_association_service.py")[2],
        "recompute_all_users",
    )
    if function_node is None:
        violations.append(f"{service_path.name} missing recompute_all_users")
    elif "distinct()" not in "\n".join(
        service_source.splitlines()[function_node.lineno - 1 : function_node.end_lineno]
    ):
        violations.append(
            f"{service_path.name} recompute_all_users must remain user-scoped via distinct user_ids"
        )
    if violations:
        return guard_fail("SQAM Idiographic DP1", violations)
    return guard_pass(
        "SQAM Idiographic DP1",
        "idiographic summary keeps disclaimer and user-scoped recompute",
    )


if __name__ == "__main__":
    raise SystemExit(main())
