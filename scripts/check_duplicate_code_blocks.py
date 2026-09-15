#!/usr/bin/env python3
"""
Duplicate Code Block Detector for CI.

Scans Python files for consecutive duplicate code blocks (>=8 lines)
that indicate copy-paste bugs. Used as a CI quality gate.

Usage:
    python scripts/check_duplicate_code_blocks.py <file> [--threshold N]

Exit 0 = pass, non-zero = fail.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

DEFAULT_THRESHOLD = 8
DEFAULT_MAX_DUPLICATES = 0


def check_file(filepath: str | Path, threshold: int = DEFAULT_THRESHOLD) -> list[dict]:
    """Check a single file for duplicate code blocks.

    Returns a list of duplicate findings with block content and line positions.
    """
    filepath = Path(filepath)
    source = filepath.read_text(encoding="utf-8")
    lines = source.split("\n")

    # Normalize: strip whitespace, skip empty and comment lines
    normalized: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            normalized.append((i + 1, stripped))  # 1-based line numbers

    # Build sliding window of blocks
    if len(normalized) < threshold:
        return []

    blocks: dict[str, list[int]] = {}
    for idx in range(len(normalized) - threshold + 1):
        block_lines = [normalized[idx + j][1] for j in range(threshold)]
        block = "\n".join(block_lines)
        start_line = normalized[idx][0]
        if block not in blocks:
            blocks[block] = []
        blocks[block].append(start_line)

    # Find duplicates, filtering error-handling boilerplate
    findings = []
    boilerplate_markers = ["logger.warning(", "exc_info=True)", "except Exception:"]
    for block, positions in blocks.items():
        if len(positions) < 2:
            continue
        bp_count = sum(1 for m in boilerplate_markers if m in block)
        if bp_count >= 3:
            continue
        findings.append({
            "block_preview": block[:200],
            "line_positions": positions,
            "count": len(positions),
        })

    return findings


def check_class_duplicates(filepath: str | Path) -> list[dict]:
    """Check for duplicate class definitions in a file."""
    filepath = Path(filepath)
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)

    class_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_names.append(node.name)

    seen: dict[str, int] = {}
    for name in class_names:
        seen[name] = seen.get(name, 0) + 1

    findings = []
    for name, count in seen.items():
        if count > 1:
            findings.append({"class_name": name, "count": count})

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect duplicate code blocks")
    parser.add_argument("files", nargs="+", help="Files to check")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                        help=f"Minimum lines for a duplicate block (default: {DEFAULT_THRESHOLD})")
    args = parser.parse_args()

    all_findings = []
    for filepath in args.files:
        # Check duplicate code blocks
        dupes = check_file(filepath, args.threshold)
        for d in dupes:
            all_findings.append(f"DUPLICATE BLOCK ({d['count']}x) in {filepath}: lines {d['line_positions']}")

        # Check duplicate class names
        class_dupes = check_class_duplicates(filepath)
        for cd in class_dupes:
            all_findings.append(f"DUPLICATE CLASS '{cd['class_name']}' ({cd['count']}x) in {filepath}")

    if all_findings:
        print(f"Found {len(all_findings)} duplicate(s):")
        for f in all_findings:
            print(f"  - {f}")
        return 1

    print(f"No duplicates found (threshold={args.threshold} lines).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
