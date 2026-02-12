#!/usr/bin/env python3
"""Validate coverage reports against configurable thresholds."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_go_cover(path: Path) -> float:
    text = path.read_text(encoding="utf-8")
    matches = re.findall(r"^total:\s+\(statements\)\s+([0-9]+(?:\.[0-9]+)?)%$", text, re.MULTILINE)
    if not matches:
        raise ValueError(f"Could not parse Go coverage from {path}")
    return float(matches[-1])


def parse_python_coverage_xml(path: Path) -> float:
    tree = ET.parse(path)
    root = tree.getroot()
    line_rate = root.attrib.get("line-rate")
    if line_rate is None:
        raise ValueError(f"Missing line-rate in {path}")
    return float(line_rate) * 100.0


def parse_lcov(path: Path) -> float:
    total_found = 0
    total_hit = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("LF:"):
            total_found += int(line[3:])
        elif line.startswith("LH:"):
            total_hit += int(line[3:])
    if total_found == 0:
        raise ValueError(f"No line coverage records in {path}")
    return (total_hit / total_found) * 100.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check coverage threshold")
    parser.add_argument("--kind", choices=["go", "python", "flutter"], required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--threshold", type=float, required=True)
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        raise FileNotFoundError(f"Coverage report not found: {report_path}")

    if args.kind == "go":
        value = parse_go_cover(report_path)
    elif args.kind == "python":
        value = parse_python_coverage_xml(report_path)
    else:
        value = parse_lcov(report_path)

    print(f"{args.kind} coverage={value:.2f}% (threshold={args.threshold:.2f}%)")
    if value < args.threshold:
        print(
            f"ERROR: {args.kind} coverage {value:.2f}% is below threshold {args.threshold:.2f}%",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
