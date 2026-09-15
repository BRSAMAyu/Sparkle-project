from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.simulation_runner import run_benchmark_suite  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SparkleGoalBench simulation regression benchmarks.")
    parser.add_argument("--suite", default="full", help="Benchmark suite: full, ExamSprintBench, exam_sprint, etc.")
    parser.add_argument("--reports-dir", default=None, help="Directory for markdown benchmark reports.")
    parser.add_argument("--commit", default=None, help="Commit SHA to stamp into the report.")
    parser.add_argument("--skip-db", action="store_true", help="Run without writing simulation_runs.")
    parser.add_argument("--no-report", action="store_true", help="Run without writing docs/benchmarks markdown.")
    parser.add_argument("--fail-on-warning", action="store_true", help="Exit non-zero for warning gates as well.")
    return parser.parse_args()


async def _main() -> int:
    args = _parse_args()
    if args.skip_db:
        report = await run_benchmark_suite(
            args.suite,
            write_report=not args.no_report,
            reports_dir=args.reports_dir,
            commit=args.commit,
        )
    else:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            report = await run_benchmark_suite(
                args.suite,
                session=session,
                write_report=not args.no_report,
                reports_dir=args.reports_dir,
                commit=args.commit,
            )

    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if report.status == "blocked":
        return 1
    if args.fail_on_warning and report.status == "warning":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
