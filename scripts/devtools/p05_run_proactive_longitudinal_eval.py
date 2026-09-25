#!/usr/bin/env python3
"""P-05 · Proactive Longitudinal Evaluation 无人值守 runner（主动组 vs 基线组）.

多天 persona 时间线：stalled / deadline / completion 三谱 × seeded 决策模型，
真实 comeback 任务（生成/抑制/投递）+ 真实 Action/Feedback/Permission 服务驱动；
主动组（主动面开）与基线组（同时间线关掉主动面）对照。raw 落
``v3-output/WT384-P05-EVAL/raw/``，summary 全部由 raw 程序化复算。

用法（worktree 根；backend/.venv 解释器）::

    backend/.venv/bin/python scripts/devtools/p05_run_proactive_longitudinal_eval.py [options]
    backend/.venv/bin/python scripts/devtools/p05_run_proactive_longitudinal_eval.py --summarize-only

exit 0 = 两组跑完且正确性不变量全零（mute 后复发/授权撤销后 auto/阈值内投放）；
否则非零。零真实 LLM、零模拟器、零浏览器。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import os  # noqa: E402

os.environ.setdefault("SECRET_KEY", "p05-eval-unattended")
os.environ.setdefault("EVENT_BUS_MAX_RETRIES", "0")

from tests.proactive_longitudinal.engine import run_population  # noqa: E402
from tests.proactive_longitudinal.metrics import (
    compare_groups,
    render_markdown,
    summarize_group,
)  # noqa: E402
from tests.proactive_longitudinal.persona import build_population  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "v3-output" / "WT384-P05-EVAL"

#: 正确性不变量（评估红条件；负担反例不在此列——反例保留并回流 dynamic issue）
_INVARIANTS = (
    ("post_mute_deliveries", "mute 后跨天复发投放"),
    ("sub_threshold_deliveries", "沉默 <3 天即投放（eligibility 违例）"),
    ("post_auto_revoke_auto_steps", "revoke 后 auto 直通（P-04 时序违例）"),
    ("next_day_redeliveries_after_accept", "accept 次日复发投放"),
)


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def summarize_from_raw(out_dir: Path, *, meta: dict) -> dict:
    """summary 全部由 raw 文件程序化复算（--summarize-only 同路径）。"""
    records: dict[str, list[dict]] = {}
    for group in ("proactive", "baseline"):
        raw_path = out_dir / "raw" / f"{group}_group.jsonl"
        records[group] = _read_jsonl(raw_path)
    days = int(meta["days"])
    summary = {
        "meta": meta,
        "proactive": summarize_group(
            records["proactive"], group="proactive", days=days
        ),
        "baseline": summarize_group(records["baseline"], group="baseline", days=days),
    }
    summary["compare"] = compare_groups(summary["proactive"], summary["baseline"])
    violations = {
        name: summary["proactive"]["burden"]["correctness"][key]
        for key, name in _INVARIANTS
    }
    summary["invariant_violations"] = violations
    summary["acceptance_invariants_pass"] = all(v == 0 for v in violations.values())
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260925,
        help="persona 总体与决策模型 seed（同 seed 同时间线）",
    )
    parser.add_argument(
        "--per-arc", type=int, default=8, help="每事件谱 persona 数（默认 8 → 每组 24）"
    )
    parser.add_argument(
        "--days", type=int, default=14, help="模拟时间线天数（默认 14）"
    )
    parser.add_argument(
        "--groups",
        choices=("both", "proactive", "baseline"),
        default="both",
        help="跑哪些组（默认 both）",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT,
        help="产物目录（默认 v3-output/WT384-P05-EVAL）",
    )
    parser.add_argument(
        "--summarize-only",
        action="store_true",
        help="跳过运行，直接从已有 raw/ 复算 summary 与报告",
    )
    args = parser.parse_args()

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    groups: tuple[str, ...] = (
        ("proactive", "baseline") if args.groups == "both" else (args.groups,)
    )

    if not args.summarize_only:
        specs = build_population(seed=args.seed, per_arc=args.per_arc, days=args.days)
        timeline = {
            "seed": args.seed,
            "per_arc": args.per_arc,
            "days": args.days,
            # dataclass → JSON（frozenset 需展开）
            "personas": [
                {
                    **{
                        k: v
                        for k, v in spec.__dict__.items()
                        if k != "intrinsic_restart_days"
                    },
                    "intrinsic_restart_days": sorted(spec.intrinsic_restart_days),
                }
                for spec in specs
            ],
        }
        (out_dir / "raw").mkdir(parents=True, exist_ok=True)
        (out_dir / "raw" / "events_timeline.json").write_text(
            json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        raw_groups = asyncio.run(run_population(specs, groups=groups, days=args.days))
        for group, rows in raw_groups.items():
            _write_jsonl(out_dir / "raw" / f"{group}_group.jsonl", rows)

    meta = {
        "git_sha": _git_sha(),
        "ran_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "seed": args.seed,
        "per_arc": args.per_arc,
        "days": args.days,
        "groups": list(groups),
        "raw_dir": str(out_dir / "raw"),
    }
    summary = summarize_from_raw(out_dir, meta=meta)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "EVAL_RESULTS.md").write_text(
        render_markdown(summary, meta=meta), encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "groups": list(groups),
                "proactive_restart_rate": summary["proactive"]["recovery"][
                    "restart_rate"
                ],
                "baseline_restart_rate": summary["baseline"]["recovery"][
                    "restart_rate"
                ],
                "proactive_suggestions": summary["proactive"]["burden"][
                    "suggestions_issued"
                ],
                "invariant_violations": summary["invariant_violations"],
                "summary": str(out_dir / "summary.json"),
                "report": str(out_dir / "EVAL_RESULTS.md"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if summary["acceptance_invariants_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
