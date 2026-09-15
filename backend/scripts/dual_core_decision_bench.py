#!/usr/bin/env python3
"""Run the offline DualCore decision bench.

Examples:
    cd backend
    python scripts/dual_core_decision_bench.py --days 30 --limit 1000 --format markdown
    python scripts/dual_core_decision_bench.py --user-id <uuid> --format both --output /tmp/dual_core_bench
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import UUID

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal, engine
from app.services.analytics.dual_core_decision_bench import (
    BenchConfig,
    DualCoreDecisionBench,
    render_markdown_report,
)


def _json_default(value):
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit DualCore routing decisions and outcome evidence.",
    )
    parser.add_argument("--limit", type=int, default=1000, help="Maximum recent decisions to inspect.")
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days. Use 0 for no time filter.")
    parser.add_argument("--user-id", type=UUID, default=None, help="Optional user UUID filter.")
    parser.add_argument(
        "--min-group-size",
        type=int,
        default=5,
        help="Minimum labeled samples in a pseudo-causal context group.",
    )
    parser.add_argument("--examples", type=int, default=12, help="Maximum divergence examples to include.")
    parser.add_argument(
        "--format",
        choices=("json", "markdown", "both"),
        default="markdown",
        help="Output format.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Optional output path. For --format both, pass a directory or extensionless prefix; "
            ".json and .md files will be written."
        ),
    )
    return parser.parse_args()


def _write_output(report: dict, rendered_markdown: str, args: argparse.Namespace) -> None:
    if args.output is None:
        if args.format == "json":
            print(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default))
        elif args.format == "markdown":
            print(rendered_markdown)
        else:
            print(rendered_markdown)
            print("\n<!-- JSON -->")
            print(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default))
        return

    output = args.output
    if args.format == "json":
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
        print(f"Wrote JSON report to {output}")
        return

    if args.format == "markdown":
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered_markdown, encoding="utf-8")
        print(f"Wrote Markdown report to {output}")
        return

    if output.suffix:
        prefix = output.with_suffix("")
        prefix.parent.mkdir(parents=True, exist_ok=True)
    else:
        prefix = output
        if output.exists() and output.is_dir():
            prefix = output / "dual_core_decision_bench"
        prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = prefix.with_suffix(".json")
    md_path = prefix.with_suffix(".md")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    md_path.write_text(rendered_markdown, encoding="utf-8")
    print(f"Wrote JSON report to {json_path}")
    print(f"Wrote Markdown report to {md_path}")


async def _run() -> None:
    args = _parse_args()
    config = BenchConfig(
        limit=max(1, args.limit),
        days=None if args.days == 0 else max(1, args.days),
        user_id=args.user_id,
        min_group_size=max(1, args.min_group_size),
        examples=max(0, args.examples),
    )
    try:
        async with AsyncSessionLocal() as session:
            report = await DualCoreDecisionBench(session).run(config)
        rendered_markdown = render_markdown_report(report)
        _write_output(report, rendered_markdown, args)
    except Exception as exc:
        print(f"DualCore decision bench failed: {exc}", file=sys.stderr)
        print(
            "Hint: verify the database is reachable and has spare connections; "
            "try a smaller --limit or run after freeing local backend workers.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_run())
