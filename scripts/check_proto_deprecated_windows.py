#!/usr/bin/env python3
"""Enforce deprecated proto fields to carry an explicit removal milestone."""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROTO_DIR = ROOT / "proto"
REMOVE_AFTER_RE = re.compile(r"remove_after:\s*M\d+", re.IGNORECASE)


def check_file(path: pathlib.Path) -> list[str]:
    errors: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()

    for idx, line in enumerate(lines, start=1):
        if "deprecated = true" not in line:
            continue

        # Look up nearby comments for removal milestone metadata.
        window = lines[max(0, idx - 4): idx]
        has_milestone = any(REMOVE_AFTER_RE.search(item) for item in window)
        if not has_milestone:
            errors.append(
                f"{path.relative_to(ROOT)}:{idx} deprecated field missing 'remove_after: Mx' comment"
            )

    return errors


def main() -> int:
    proto_files = sorted(PROTO_DIR.glob("*.proto"))
    all_errors: list[str] = []

    for path in proto_files:
        all_errors.extend(check_file(path))

    if all_errors:
        print("Proto deprecation policy violations detected:")
        for err in all_errors:
            print(f"- {err}")
        return 1

    print("Proto deprecation policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
