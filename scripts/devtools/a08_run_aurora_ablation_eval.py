#!/usr/bin/env python3
"""A-08 · Aurora 纵向/消融评估无人值守 runner（四臂对照）。

10 persona × multi-session 时间线，四臂（full / no_memory / no_experience /
fixed_policy）同时间线单因子消融；真实 Aurora 决策服务面（StuckJourneyService
+ FrictionChatWiringService + D-05 lifecycle + A-05 patch 回路）驱动，sqlite
隔离 + fakeredis 基建绑定 + 可控时钟 backdate。raw 落
``v3-output/WT393-A08-ABLATION/raw/``，summary 全部由 raw 程序化复算。

用法（仓库根；backend venv 解释器）::

    backend/.venv/bin/python scripts/devtools/a08_run_aurora_ablation_eval.py [options]
    backend/.venv/bin/python scripts/devtools/a08_run_aurora_ablation_eval.py --summarize-only
    backend/.venv/bin/python scripts/devtools/a08_run_aurora_ablation_eval.py --verify-repro

exit 0 = 四臂跑完且评估不变量全绿（fixed 零引擎调用 / 消融臂能力面确实缺席 /
预算与解决判据自洽）；否则非零。零真实 LLM、零模拟器、零浏览器、模型 judge 0 次。

可复现性：PYTHONHASHSEED=0 固定（A-03 B1 tie 的 argmax 次序依赖字符串哈希的
frozenset 迭代序——这本身是已登记的引擎问题）；``--verify-repro`` 全量跑两遍
并断言 summary 逐字节一致。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("SECRET_KEY", "a08-eval-unattended-secret-key-0123456789")
os.environ.setdefault("EVENT_BUS_MAX_RETRIES", "0")

from tests.aurora_ablation.engine import run_persona_arm  # noqa: E402
from tests.aurora_ablation.metrics import (  # noqa: E402
    compare_arms,
    extract_counterexamples,
    render_markdown,
    summarize_arm,
)
from tests.aurora_ablation.persona import ARMS, build_population  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "v3-output" / "WT393-A08-ABLATION"


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


async def run_all_arms(out_dir: Path, *, persona_filter: str | None = None) -> dict[str, list[dict]]:
    specs = build_population()
    if persona_filter:
        specs = [s for s in specs if s.persona_id == persona_filter]
    raw: dict[str, list[dict]] = {}
    for arm in ARMS:
        records: list[dict] = []
        for spec in specs:
            records.extend(await run_persona_arm(spec, arm=arm))
        raw[arm] = records
        _write_jsonl(out_dir / "raw" / f"{arm}.jsonl", records)
        print(f"[a08] arm={arm} records={len(records)}", file=sys.stderr)
    return raw


def build_summary(out_dir: Path, *, run_meta: dict | None = None) -> dict:
    raw = {arm: _read_jsonl(out_dir / "raw" / f"{arm}.jsonl") for arm in ARMS}
    summaries = {arm: summarize_arm(raw[arm], arm=arm) for arm in ARMS}
    comparisons = compare_arms(summaries)
    counterexamples = {
        arm: extract_counterexamples(raw[arm])
        for arm in ARMS
        if arm in ("full", "no_memory", "no_experience")
    }
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "git_sha": run_meta.get("git_sha") if run_meta else _git_sha(),
        "spec": "A-08 aurora longitudinal/ablation (wt393)",
        "arms": ARMS,
        "population": [s.persona_id for s in build_population()],
        "summaries": summaries,
        "comparison": comparisons,
        "counterexamples": counterexamples,
        "notes": {
            "determinism": "summary 全部由 raw 程序化复算；模型 judge 0 次",
            "repro": "PYTHONHASHSEED=0 固定；--verify-repro 断言两遍 summary 一致",
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "EVAL_RESULTS.md").write_text(
        render_markdown(summaries, comparisons), encoding="utf-8"
    )
    return payload


def _invariants_ok(payload: dict) -> tuple[bool, list[str]]:
    problems: list[str] = []
    for arm in ARMS:
        inv = payload["summaries"][arm]["invariants"]
        for name, ok in inv.items():
            if ok is False:
                problems.append(f"{arm}.{name}")
    return (not problems), problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help="产物目录（默认 v3-output/WT393-A08-ABLATION）")
    parser.add_argument("--persona", type=str, default=None, help="只跑单个 persona（调试用；summary 仍可复算）")
    parser.add_argument("--summarize-only", action="store_true", help="跳过评估，从 raw 复算 summary/EVAL_RESULTS")
    parser.add_argument("--verify-repro", action="store_true", help="全量跑两遍并断言 summary 一致（可复现性证据）")
    args = parser.parse_args()

    out_dir: Path = args.out_dir
    if not args.summarize_only:
        run_meta = {"git_sha": _git_sha()}
        asyncio.run(run_all_arms(out_dir, persona_filter=args.persona))
        payload = build_summary(out_dir, run_meta=run_meta)
        if args.verify_repro:
            raw_backup = {
                arm: (out_dir / "raw" / f"{arm}.jsonl").read_text(encoding="utf-8")
                for arm in ARMS
            }
            asyncio.run(run_all_arms(out_dir, persona_filter=args.persona))
            payload2 = build_summary(out_dir, run_meta=run_meta)
            p1 = json.dumps(payload["summaries"], ensure_ascii=False, sort_keys=True)
            p2 = json.dumps(payload2["summaries"], ensure_ascii=False, sort_keys=True)
            if p1 != p2:
                print("[a08] REPRO FAIL: summaries differ across runs", file=sys.stderr)
                return 2
            # 恢复第一遍 raw（同内容；语义等价）
            for arm in ARMS:
                (out_dir / "raw" / f"{arm}.jsonl").write_text(raw_backup[arm], encoding="utf-8")
            build_summary(out_dir, run_meta=run_meta)
            print("[a08] repro OK: summaries identical across two full runs", file=sys.stderr)
    else:
        payload = build_summary(out_dir)

    ok, problems = _invariants_ok(payload)
    for arm in ARMS:
        s = payload["summaries"][arm]
        print(
            f"[a08] {arm:>14}: accuracy={s['stuck_accuracy']} "
            f"sessions/ep={s['sessions_to_resolution_mean']} utility={s['utility']} "
            f"intrusions={s['control_intrusions']} questions={s['questions_total']}",
            file=sys.stderr,
        )
    if not ok:
        print(f"[a08] INVARIANT FAIL: {problems}", file=sys.stderr)
        return 1
    print(f"[a08] done → {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
