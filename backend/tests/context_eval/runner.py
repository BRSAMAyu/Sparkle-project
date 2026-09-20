"""C-08 · ablation 评测 CLI（确定性、可重复、真实 LLM 0 次）。

用法（backend/ 下）::

    SECRET_KEY=test python3 -m tests.context_eval.runner                        # stdout 机读 JSON
    SECRET_KEY=test python3 -m tests.context_eval.runner --out /tmp/abl.json
    SECRET_KEY=test python3 -m tests.context_eval.runner --export-scenarios /tmp/scenarios.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, UTC
from pathlib import Path

from .context_eval_schema import ARMS, MIN_SCENARIOS, check_coverage, validate_scenario
from .grading import aggregate, grade
from .mock_model import CITE_THRESHOLD, MAX_SEEN_ITEMS, TOKEN_BUDGET, assemble, mock_answer
from .scenarios import build_scenarios

RESULTS_VERSION = "c08-ablation.v1"


def _git_sha() -> str:
    override = os.environ.get("C08_GIT_SHA")
    if override:
        return override
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def run_ablation() -> dict:
    """跑满四臂 × 全场景；返回机读结果（metadata-only，无材料正文）。"""
    scenarios = build_scenarios()
    errors = [error for scenario in scenarios for error in validate_scenario(scenario)]
    errors.extend(check_coverage(scenarios))
    if errors:
        raise ValueError("scenario validation failed: " + "; ".join(errors))
    if len(scenarios) < MIN_SCENARIOS:
        raise ValueError(f"scenario count {len(scenarios)} < {MIN_SCENARIOS}")

    rows = []
    for scenario in scenarios:
        for arm in ARMS:
            assembled = assemble(scenario, arm)
            answer, cited_refs, used_memory_refs = mock_answer(scenario, assembled)
            result = grade(scenario, arm, assembled, answer, cited_refs, used_memory_refs)
            rows.append(result)

    return {
        "version": RESULTS_VERSION,
        "meta": {
            "git_sha": _git_sha(),
            "generated_at": datetime.now(UTC).isoformat(),
            "arms": list(ARMS),
            "scenario_count": len(scenarios),
            "real_llm_calls": 0,
            "mock": {
                # C-08 N1：meta 从 mock_model 常量取值（此前 max_seen_items 硬编码 5，
                # 实为 MAX_SEEN_ITEMS = 4，导出的 ablation_results.json 自述失真）。
                "cite_threshold": CITE_THRESHOLD,
                "max_seen_items": MAX_SEEN_ITEMS,
                "token_budget": TOKEN_BUDGET,
                "latency_model": "40 + 0.12*tokens + 15*surfaces (proxy, not wall-clock)",
            },
            "utility_judge": "C-04 deterministic citation outcome + constructed gold labels",
        },
        "summary": aggregate(rows),
        "scenarios": [row.to_payload() for row in rows],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="C-08 context decision utility ablation")
    parser.add_argument("--out", type=Path, default=None, help="write JSON here (default stdout)")
    parser.add_argument(
        "--export-scenarios", type=Path, default=None, help="dump frozen scenario set as JSON"
    )
    args = parser.parse_args(argv)

    if args.export_scenarios:
        payload = [scenario.to_payload() for scenario in build_scenarios()]
        args.export_scenarios.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"exported {len(payload)} scenarios -> {args.export_scenarios}", file=sys.stderr)

    results = run_ablation()
    text = json.dumps(results, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote ablation results -> {args.out}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
