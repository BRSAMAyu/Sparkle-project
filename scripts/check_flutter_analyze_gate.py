#!/usr/bin/env python3
"""Run Dart analyze in machine mode and enforce severity/code budgets."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path


def _run_analyze(project_dir: Path) -> list[str]:
    proc = subprocess.run(
        ["dart", "analyze", "--format", "machine"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    # analyzer returns non-zero when issues found; we parse ourselves.
    output = proc.stdout.strip().splitlines() if proc.stdout.strip() else []
    return output


def _parse(lines: list[str]) -> tuple[Counter, Counter]:
    severities: Counter[str] = Counter()
    codes: Counter[str] = Counter()
    for line in lines:
        parts = line.split("|")
        if len(parts) < 8:
            continue
        severity = parts[0].strip().upper()
        code = parts[2].strip().upper()
        severities[severity] += 1
        codes[code] += 1
    return severities, codes


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Flutter analyze budget")
    parser.add_argument("--project-dir", default="mobile")
    parser.add_argument("--budget-file", default="quality/flutter_analyze_allowlist.json")
    parser.add_argument("--write-report", default="quality/flutter_analyze_report.json")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    project_dir = repo_root / args.project_dir
    budget_file = repo_root / args.budget_file

    budget = json.loads(budget_file.read_text(encoding="utf-8"))
    lines = _run_analyze(project_dir)
    severity_counts, code_counts = _parse(lines)

    report = {
        "severity_counts": dict(severity_counts),
        "top_codes": dict(code_counts.most_common(50)),
        "total_issues": sum(severity_counts.values()),
    }
    report_path = repo_root / args.write_report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    failed = False
    max_error = int(budget.get("max_error", 0))
    max_warning = int(budget.get("max_warning", 0))
    max_info = int(budget.get("max_info", 0))

    err = severity_counts.get("ERROR", 0)
    warn = severity_counts.get("WARNING", 0)
    info = severity_counts.get("INFO", 0)

    print(f"Analyze counts => ERROR={err}, WARNING={warn}, INFO={info}")

    if err > max_error:
        print(f"❌ ERROR budget exceeded: {err} > {max_error}")
        failed = True
    if warn > max_warning:
        print(f"❌ WARNING budget exceeded: {warn} > {max_warning}")
        failed = True
    if info > max_info:
        print(f"❌ INFO budget exceeded: {info} > {max_info}")
        failed = True

    code_budget = budget.get("info_code_budgets", {})
    for code, allowed in code_budget.items():
        current = code_counts.get(code.upper(), 0)
        if current > int(allowed):
            print(f"❌ INFO code budget exceeded for {code}: {current} > {allowed}")
            failed = True

    if failed:
        print("\nRun this to refresh budget intentionally:")
        print("  dart analyze --format machine > /tmp/mobile_analyze_machine.txt")
        return 1

    print("✅ Flutter analyze gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
