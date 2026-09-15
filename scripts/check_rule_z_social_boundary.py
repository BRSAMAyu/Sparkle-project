#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from check_rule_k_write_paths import iter_rule_z_paths, scan_rule_z_paths


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    targets = iter_rule_z_paths(REPO_ROOT)
    violations = scan_rule_z_paths(targets, REPO_ROOT)
    if violations:
        print("[Rule Z] FAIL")
        for violation in violations:
            print(
                f"[{violation.rule_id}] {violation.path}:{violation.line_no} "
                f"{violation.message} :: {violation.snippet}"
            )
        return 1
    print(f"[Rule Z] PASS - {len(targets)} files scanned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
