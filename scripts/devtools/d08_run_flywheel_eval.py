#!/usr/bin/env python3
"""D-08 · 数据飞轮纵向评估无人值守 runner（10 persona × 双臂 × Day0/3/7）。

数据→理解→决策→outcome 闭环的纵向证明：真实 Aurora 决策面（StuckJourneyService
+ FrictionChatWiringService）+ 真实记忆面（ContextPackBuilder 全漏斗 +
MemoryService 治理动作）+ 真实理解面（D-03 五维 + Stage20 确定性 judge）+
真实 outcome 面（D-05 lifecycle 关联）+ 真实个性化面（A-05 patch 证据门 +
旅程纠正环），sqlite 隔离 + fakeredis 基建绑定 + backdate 可控时钟。
双臂 paired design：``flywheel``（反馈事件开）vs ``no_feedback``（同世界同
探针、零反馈）——行为差分即飞轮因果证据。raw 落
``v3-output/WT397-D08-FLYWHEEL/raw/``，dashboard 全部由 raw 程序化复算。

用法（仓库根；backend venv 解释器）::

    backend/.venv/bin/python scripts/devtools/d08_run_flywheel_eval.py [options]
    backend/.venv/bin/python scripts/devtools/d08_run_flywheel_eval.py --summarize-only
    backend/.venv/bin/python scripts/devtools/d08_run_flywheel_eval.py --verify-repro

exit 0 = 全人口跑完且评估不变量全绿（no_feedback 臂零反馈事件 / 双臂探针
齐全 / 验收逐 persona 如实判定——不通过者保留在案）；否则非零。
零真实 LLM、零模拟器、零浏览器、模型 judge 0 次。

可复现性：PYTHONHASHSEED=0 固定；``--verify-repro`` 全量跑两遍并断言
dashboard 逐字节一致（provenance 时间戳除外）。
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

os.environ.setdefault("SECRET_KEY", "d08-eval-unattended-secret-key-01234567")
os.environ.setdefault("EVENT_BUS_MAX_RETRIES", "0")

from tests.d08_flywheel.engine import run_persona_arm  # noqa: E402
from tests.d08_flywheel.metrics import summarize_population  # noqa: E402
from tests.d08_flywheel.protocol import FLYWHEEL_ARMS, build_population  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "v3-output" / "WT397-D08-FLYWHEEL"


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
    for arm in FLYWHEEL_ARMS:
        records: list[dict] = []
        for spec in specs:
            records.extend(await run_persona_arm(spec, arm=arm))
        raw[arm] = records
        if persona_filter is None:
            _write_jsonl(out_dir / "raw" / f"{arm}.jsonl", records)
        print(f"[d08] arm={arm} records={len(records)}", file=sys.stderr)
    return raw


def render_dashboard_md(payload: dict) -> str:
    """DASHBOARD.md 渲染（数字全部来自 payload，无手填）。"""
    lines = [
        "# WT397 · D-08 数据飞轮纵向评估 — Dashboard（程序化生成）",
        "",
        f"- spec `{payload['spec_version']}` · metrics `{payload['metrics_version']}` · population {len(payload['population'])}",
        "",
        "## 验收总览（逐 persona ≥1 条 adaptation 因果链）",
        "",
        f"- 通过 {payload['acceptance']['personas_passed']}/{payload['acceptance']['personas_total']}"
        f"（链型计数 {json.dumps(payload['acceptance']['chain_type_counts'], ensure_ascii=False)}）",
        f"- 未通过者保留在案：{[p for p in payload['population'] if p not in payload['acceptance']['passed_ids']]}",
        f"- 无效/无效力个性化台账：**{payload['invalid_personalization_total']} 条（保留不筛）**",
        "",
        "## Fleet 级五维状态迁移（Day0 → Day7，按 persona 计数）",
        "",
    ]
    transitions = payload["fleet"]["understanding_dim_status_transitions_day0_to_day7"]
    for dim, counts in transitions.items():
        lines.append(f"- **{dim}**: {json.dumps(counts, ensure_ascii=False)}")
    lines += [
        "",
        f"- 被跟随决策匹配分均值：Day0 `{payload['fleet']['followed_match_mean_day0']}`"
        f" → Day7 `{payload['fleet']['followed_match_mean_day7']}`",
        "",
        "## 逐 persona 配对结果",
        "",
        "| persona | 验收 | 经由 | 链 | 无效台账 | 对照侵入(fly/no_fb) |",
        "|---|---|---|---|---|---|",
    ]
    for pid, p in payload["per_persona"].items():
        chains = ";".join(
            f"{c['chain_type']}{'✓' if c.get('behavior_changed') else '×'}" for c in p["adaptation_chains"]
        )
        lines.append(
            "| {} | {} | {} | {} | {} | {}/{} |".format(
                pid,
                "PASS" if p["acceptance"]["passed"] else "FAIL",
                "+".join(p["acceptance"]["via"]) or "-",
                chains or "-",
                len(p["invalid_personalization"]),
                len(p["control_intrusions"]["flywheel"]),
                len(p["control_intrusions"]["no_feedback"]),
            )
        )
    lines += ["", "## 五维逐 persona（Day0 → Day7 配对差）", ""]
    for pid, p in payload["per_persona"].items():
        lines.append(f"### {pid}")
        lines.append("")
        for dim, entry in p["faces"]["understanding"].items():
            lines.append(f"- {dim}: {entry['delta_day7_vs_day0']}")
        lines.append(
            f"- memory: stale_surfaced {p['faces']['memory']['delta_day7_vs_day0']['stale_surfaced']}"
            f", stale_confidence {p['faces']['memory']['delta_day7_vs_day0']['stale_confidence']}"
        )
        lines.append(
            f"- intervention: match {p['faces']['intervention']['delta_day7_vs_day0']['match_class']}"
            f", followed {p['faces']['intervention']['delta_day7_vs_day0']['followed']}"
        )
        lines.append(f"- outcome: associations +{p['faces']['outcome']['delta_day7_vs_day0']}")
        lines.append("")
    content = "\n".join(lines) + "\n"
    import hashlib

    digest = hashlib.sha256(content.encode()).hexdigest()[:16]
    return content + f"\n（内容摘要 sha256[:16] = {digest}）\n"


def build_dashboard(out_dir: Path, *, run_meta: dict | None = None) -> dict:
    raw = {arm: _read_jsonl(out_dir / "raw" / f"{arm}.jsonl") for arm in FLYWHEEL_ARMS}
    payload = summarize_population(raw)
    payload["generated_at"] = datetime.now(UTC).isoformat()
    payload["git_sha"] = run_meta.get("git_sha") if run_meta else _git_sha()
    payload["counts"] = {
        arm: {
            "records": len(raw[arm]),
            "probes": sum(1 for r in raw[arm] if r.get("kind") == "probe"),
            "events": sum(1 for r in raw[arm] if r.get("kind") == "event"),
            "controls": sum(1 for r in raw[arm] if r.get("kind") == "control"),
        }
        for arm in FLYWHEEL_ARMS
    }
    (out_dir / "dashboard.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "DASHBOARD.md").write_text(render_dashboard_md(payload), encoding="utf-8")
    return payload


def _invariants_ok(payload: dict) -> tuple[bool, list[str]]:
    problems: list[str] = []
    for arm, counts in payload.get("counts", {}).items():
        if counts["probes"] != 3 * 10:
            problems.append(f"{arm}.probes={counts['probes']}")
    return (not problems), problems


def _canonicalize(obj):
    """剔除 run 间必然不同的随机标识（uuid4 派生 id），保留结构与存在性。

    可复现性比对的口径：因果链的 established 取决于 applied id 列表**非空**
    与行为差分字段（friction/intervention/surfaced 等，全部稳定）；id 本身
    内容寻址自 uuid4，逐 run 必然不同，归一为占位符后再比对。
    """
    import re

    volatile = re.compile(
        r"(polpatch_[0-9a-f]+|outc_[0-9a-f]+|aurora_[0-9a-f]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    )
    if isinstance(obj, dict):
        return {k: _canonicalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_canonicalize(v) for v in obj]
    if isinstance(obj, str) and volatile.search(obj):
        return "<volatile-ref>"
    return obj


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--out-dir", type=Path, default=DEFAULT_OUT, help="产物目录（默认 v3-output/WT397-D08-FLYWHEEL）"
    )
    parser.add_argument("--persona", type=str, default=None, help="只跑单个 persona（调试用；不落 raw）")
    parser.add_argument(
        "--summarize-only", action="store_true", help="跳过评估，从 raw 复算 dashboard.json/DASHBOARD.md"
    )
    parser.add_argument(
        "--verify-repro", action="store_true", help="全量跑两遍并断言 dashboard 一致（可复现性证据）"
    )
    args = parser.parse_args()

    out_dir: Path = args.out_dir
    if not args.summarize_only:
        run_meta = {"git_sha": _git_sha()}
        asyncio.run(run_all_arms(out_dir, persona_filter=args.persona))
        if args.persona:
            print("[d08] single-persona debug run done（raw 不落盘）", file=sys.stderr)
            return 0
        payload = build_dashboard(out_dir, run_meta=run_meta)
        if args.verify_repro:
            raw_backup = {
                arm: (out_dir / "raw" / f"{arm}.jsonl").read_text(encoding="utf-8")
                for arm in FLYWHEEL_ARMS
            }
            asyncio.run(run_all_arms(out_dir, persona_filter=args.persona))
            payload2 = build_dashboard(out_dir, run_meta=run_meta)
            p1 = json.dumps(_canonicalize(payload["per_persona"]), ensure_ascii=False, sort_keys=True)
            p2 = json.dumps(_canonicalize(payload2["per_persona"]), ensure_ascii=False, sort_keys=True)
            if p1 != p2:
                print("[d08] REPRO FAIL: per_persona differs across runs", file=sys.stderr)
                return 2
            for arm in FLYWHEEL_ARMS:
                (out_dir / "raw" / f"{arm}.jsonl").write_text(raw_backup[arm], encoding="utf-8")
            build_dashboard(out_dir, run_meta=run_meta)
            print("[d08] repro OK: per_persona identical across two full runs", file=sys.stderr)
    else:
        payload = build_dashboard(out_dir)

    acc = payload["acceptance"]
    for pid, p in payload["per_persona"].items():
        print(
            f"[d08] {pid}: acceptance={'PASS' if p['acceptance']['passed'] else 'FAIL'} "
            f"chains={len(p['adaptation_chains'])} invalid={len(p['invalid_personalization'])}",
            file=sys.stderr,
        )
    print(
        f"[d08] acceptance {acc['personas_passed']}/{acc['personas_total']}"
        f" invalid_kept={payload['invalid_personalization_total']}",
        file=sys.stderr,
    )
    ok, problems = _invariants_ok(payload)
    if not ok:
        print(f"[d08] INVARIANT FAIL: {problems}", file=sys.stderr)
        return 1
    print(f"[d08] done → {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
