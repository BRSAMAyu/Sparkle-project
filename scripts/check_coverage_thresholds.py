#!/usr/bin/env python3
"""Validate coverage reports against global and path-scoped thresholds."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CoverageScope:
    path: str
    threshold: float


def _normalize_path(value: str) -> str:
    normalized = str(value).replace("\\", "/").strip().lstrip("./")
    if normalized.startswith("/"):
        normalized = normalized[1:]
    return normalized


def parse_go_cover(path: Path) -> float:
    text = path.read_text(encoding="utf-8")
    if text.startswith("mode:"):
        counters = parse_go_coverprofile_scopes(path)
        covered = sum(item[0] for item in counters.values())
        total = sum(item[1] for item in counters.values())
        if total == 0:
            raise ValueError(f"Could not parse Go coverage from {path}")
        return (covered / total) * 100.0
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


def parse_go_coverprofile_scopes(path: Path) -> dict[str, tuple[int, int]]:
    counters: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("mode:"):
            continue
        parts = line.split()
        if len(parts) != 3:
            continue
        file_part, statement_count, hit_count = parts
        file_path = _normalize_path(file_part.split(":", 1)[0])
        statements = int(statement_count)
        covered = statements if int(hit_count) > 0 else 0
        counters[file_path][0] += covered
        counters[file_path][1] += statements
    return {path_key: (counts[0], counts[1]) for path_key, counts in counters.items()}


def parse_python_xml_scopes(path: Path) -> dict[str, tuple[int, int]]:
    tree = ET.parse(path)
    root = tree.getroot()
    counters: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for class_node in root.findall(".//class"):
        filename = _normalize_path(class_node.attrib.get("filename", ""))
        if not filename:
            continue
        covered = 0
        total = 0
        for line_node in class_node.findall("./lines/line"):
            total += 1
            hits = int(line_node.attrib.get("hits", "0"))
            if hits > 0:
                covered += 1
        counters[filename][0] += covered
        counters[filename][1] += total
    return {path_key: (counts[0], counts[1]) for path_key, counts in counters.items()}


def parse_lcov_scopes(path: Path) -> dict[str, tuple[int, int]]:
    counters: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    current_path: str | None = None
    current_found = 0
    current_hit = 0

    def flush() -> None:
        nonlocal current_path, current_found, current_hit
        if current_path:
            counters[current_path][0] += current_hit
            counters[current_path][1] += current_found
        current_path = None
        current_found = 0
        current_hit = 0

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("SF:"):
            flush()
            current_path = _normalize_path(line[3:])
        elif line.startswith("LF:"):
            current_found = int(line[3:])
        elif line.startswith("LH:"):
            current_hit = int(line[3:])
        elif line == "end_of_record":
            flush()
    flush()
    return {path_key: (counts[0], counts[1]) for path_key, counts in counters.items()}


def compute_scope_coverage(file_counters: dict[str, tuple[int, int]], scope_path: str) -> float:
    prefix = _normalize_path(scope_path)
    covered = 0
    total = 0
    for file_path, (file_covered, file_total) in file_counters.items():
        normalized_file = _normalize_path(file_path)
        if (
            normalized_file == prefix
            or normalized_file.startswith(f"{prefix}/")
            or normalized_file.endswith(prefix)
            or normalized_file.endswith(f"/{prefix}")
            or f"/{prefix}/" in normalized_file
        ):
            covered += file_covered
            total += file_total
    if total == 0:
        raise ValueError(f"No coverage records matched scope '{scope_path}'")
    return (covered / total) * 100.0


def load_rules(path: Path, kind: str) -> tuple[float | None, list[CoverageScope]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    config = payload.get(kind, {})
    global_threshold = config.get("global")
    scopes = [
        CoverageScope(path=str(entry["path"]), threshold=float(entry["threshold"]))
        for entry in config.get("paths", [])
    ]
    return (float(global_threshold) if global_threshold is not None else None, scopes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check coverage threshold")
    parser.add_argument("--kind", choices=["go", "python", "flutter"], required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--threshold", type=float, help="Global threshold")
    parser.add_argument("--rules-file", help="JSON rules file with global and path thresholds")
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        raise FileNotFoundError(f"Coverage report not found: {report_path}")

    global_threshold = args.threshold
    scopes: list[CoverageScope] = []
    if args.rules_file:
        rules_path = Path(args.rules_file)
        if not rules_path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
        rules_global, rules_scopes = load_rules(rules_path, args.kind)
        if rules_global is not None:
            global_threshold = rules_global
        scopes = rules_scopes

    if global_threshold is None and not scopes:
        raise ValueError("No threshold configured. Pass --threshold or --rules-file.")

    if args.kind == "go":
        global_value = parse_go_cover(report_path)
        scope_counters = parse_go_coverprofile_scopes(report_path) if scopes else {}
    elif args.kind == "python":
        global_value = parse_python_coverage_xml(report_path)
        scope_counters = parse_python_xml_scopes(report_path) if scopes else {}
    else:
        global_value = parse_lcov(report_path)
        scope_counters = parse_lcov_scopes(report_path) if scopes else {}

    failures: list[str] = []
    if global_threshold is not None:
        print(f"{args.kind} coverage={global_value:.2f}% (threshold={global_threshold:.2f}%)")
        if global_value < global_threshold:
            failures.append(
                f"{args.kind} global coverage {global_value:.2f}% is below threshold {global_threshold:.2f}%"
            )

    for scope in scopes:
        scope_value = compute_scope_coverage(scope_counters, scope.path)
        print(
            f"{args.kind} coverage[{scope.path}]={scope_value:.2f}% "
            f"(threshold={scope.threshold:.2f}%)"
        )
        if scope_value < scope.threshold:
            failures.append(
                f"{args.kind} coverage for {scope.path} "
                f"{scope_value:.2f}% is below threshold {scope.threshold:.2f}%"
            )

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
