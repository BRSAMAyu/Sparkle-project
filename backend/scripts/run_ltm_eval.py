#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from uuid import UUID

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.services.memory_eval_service import MemoryEvalService


def _print_table(cases: list[dict]) -> None:
    header = "case_id | score | pref | goal | episodic | over | evidence | stale | status"
    print(header)
    print("-" * len(header))
    for item in cases:
        metrics = item["metrics"]
        print(
            f"{item['case_id']} | "
            f"{metrics['score']:.2f} | "
            f"{metrics['pref_hit_rate']:.2f} | "
            f"{metrics['goal_hit_rate']:.2f} | "
            f"{metrics['episodic_hit_rate']:.2f} | "
            f"{metrics['over_inclusion_rate']:.2f} | "
            f"{metrics['evidence_quality']:.2f} | "
            f"{metrics['staleness_rate']:.2f} | "
            f"{item['status']}"
        )


async def run_eval(args: argparse.Namespace) -> int:
    dataset_path = args.dataset or settings.LTM_EVAL_DATASET_PATH
    user_id = UUID(args.user_id) if args.user_id else None
    async with AsyncSessionLocal() as db:
        service = MemoryEvalService(db)
        summary = await service.run_dataset(
            dataset_path,
            intent=args.intent,
            user_id=user_id,
            threshold=settings.LTM_EVAL_FAIL_THRESHOLD,
        )

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, default=str))
    else:
        print(f"LTM eval status: {summary['status']} avg_score={summary['avg_score']:.2f} threshold={summary['threshold']}")
        _print_table(summary["cases"])

    return 0 if summary["avg_score"] >= summary["threshold"] else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LTM evaluation dataset.")
    parser.add_argument("--dataset", help="Path to JSONL dataset")
    parser.add_argument("--intent", help="Filter by intent")
    parser.add_argument("--user-id", dest="user_id", help="Filter by user id")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    exit_code = asyncio.run(run_eval(args))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
