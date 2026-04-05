#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.human_eval_review_service import HumanEvalReviewService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review a Sparkle human-eval run and emit ops-loop outputs.")
    parser.add_argument("input", help="Path to the human-eval JSON payload.")
    parser.add_argument("--summary-out", help="Optional path to write the summary markdown.")
    parser.add_argument("--ops-out", help="Optional path to write the ops-loop markdown.")
    parser.add_argument("--json-out", help="Optional path to write the normalized ops-loop JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    service = HumanEvalReviewService()
    summary = service.summarize_review_run(payload)
    ops = service.build_operations_report(payload)
    summary_md = service.render_markdown_summary(summary)
    ops_md = service.render_operations_markdown(ops)

    if args.summary_out:
        Path(args.summary_out).write_text(summary_md, encoding="utf-8")
    if args.ops_out:
        Path(args.ops_out).write_text(ops_md, encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(ops, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(summary_md.rstrip())
    print()
    print(ops_md.rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
