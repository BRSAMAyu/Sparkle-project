#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = REPO_ROOT / "docs" / "aurora" / "stage40_sgw_dogfood_report.md"
STATUS_PATTERN = re.compile(r"PHASE_I_EXIT_READY:\s*(YES|NO|CONDITIONAL)", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Stage40 SGW readiness report status.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = args.report
    if not report_path.exists():
        print(f"[Rule BD] FAIL - report missing: {report_path}")
        return 1

    text = report_path.read_text(encoding="utf-8")
    match = STATUS_PATTERN.search(text)
    if match is None:
        print("[Rule BD] FAIL - PHASE_I_EXIT_READY field missing")
        return 1

    status = match.group(1).upper()
    if status == "NO":
        print("[Rule BD] FAIL - PHASE_I_EXIT_READY: NO")
        return 1

    required_markers = ["Phase A", "Phase B", "Phase C", "/tmp/stage40_off.db", "/tmp/stage40_shadow.db", "/tmp/stage40_rl.db"]
    missing = [marker for marker in required_markers if marker not in text]
    if missing:
        print("[Rule BD] FAIL - report missing required markers")
        for item in missing:
            print(item)
        return 1

    print(f"[Rule BD] PASS - PHASE_I_EXIT_READY: {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
