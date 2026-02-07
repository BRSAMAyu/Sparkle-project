#!/usr/bin/env python3
"""Check technical-debt metrics against immutable budget thresholds."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


class BudgetError(RuntimeError):
    """Raised when budget file is malformed."""


def _run_metric(command: str) -> int:
    proc = subprocess.run(command, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {command}\n{proc.stderr.strip()}")
    output = proc.stdout.strip()
    try:
        return int(output)
    except ValueError as exc:
        raise RuntimeError(f"Metric command did not return integer: {command}\nstdout={output!r}") from exc


def _load_budget(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BudgetError(f"Budget file not found: {path}") from exc

    budgets = data.get("budgets")
    if not isinstance(budgets, list) or not budgets:
        raise BudgetError("Budget file must contain non-empty 'budgets' list")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Check technical debt budget")
    parser.add_argument(
        "--budget-file",
        default="quality/tech_debt_budget.json",
        help="Path to budget json file",
    )
    args = parser.parse_args()

    budget_file = Path(args.budget_file)
    payload = _load_budget(budget_file)

    print(f"Using budget file: {budget_file}")
    print("=" * 96)
    print(f"{'Metric':40} {'Current':>10} {'Budget':>10} {'Delta':>10} {'Severity':>10}")
    print("-" * 96)

    failed = False
    for entry in payload["budgets"]:
        metric_id = entry.get("id")
        command = entry.get("command")
        max_allowed = entry.get("max")
        severity = entry.get("severity", "P2")

        if not metric_id or not command or not isinstance(max_allowed, int):
            raise BudgetError(f"Invalid budget entry: {entry}")

        current = _run_metric(command)
        delta = current - max_allowed

        print(f"{metric_id:40} {current:10d} {max_allowed:10d} {delta:10d} {severity:>10}")

        if current > max_allowed:
            failed = True

    print("=" * 96)
    if failed:
        print("\n❌ Technical debt budget check failed: one or more metrics exceeded budget.")
        return 1

    print("\n✅ Technical debt budget check passed: no metric increased above budget.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BudgetError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        raise SystemExit(2)
