#!/usr/bin/env python3
from __future__ import annotations

from _sqam_guard_common import guard_fail, guard_pass, load_source


def main() -> int:
    path, source = load_source("backend/app/services/predictive_service.py")
    if "min(confidence, 0.95)" not in source and "min(confidence,0.95)" not in source:
        return guard_fail(
            "SQAM Predictive ST1", [f"{path.name} missing 0.95 confidence ceiling"]
        )
    return guard_pass(
        "SQAM Predictive ST1", "predictive confidence remains capped at 0.95"
    )


if __name__ == "__main__":
    raise SystemExit(main())
