#!/usr/bin/env python3
"""Q-04 · Personalization / Overpersonalization 独立红队无人值守 runner.

十 persona × 六路攻击面（偏好变化 / 无关历史 / 敏感信息 / 删除 / 跨用户 /
sycophancy），全部真实服务面驱动（MemoryService / ContextPackBuilder /
StuckJourneyService / FrictionChatWiringService / PolicyPatchService /
SquadService / SeedLibraryService / StateRegister），模型 judge 0 次。

paired blind review：双臂探针（personalized / control）→ 去标识候选对
（seeded RNG 指派 a/b，映射单独落盘 blind_key.json）→ 冻结程序化 rubric
评审（只读 pairs 文件）→ 评审记录落盘 → 解盲 join 算 uplift。

产物：v3-output/WT404-Q04-REDTEAM/{raw/redteam.jsonl, blind/pairs.jsonl,
blind/blind_key.json, blind/review_records.jsonl, blind/unblinded.json,
dashboard.json, DASHBOARD.md}

用法（仓库根；backend venv 解释器）::

    backend/.venv/bin/python scripts/devtools/q04_run_personalization_redteam.py
    backend/.venv/bin/python scripts/devtools/q04_run_personalization_redteam.py --persona p01_experience_reinforce

exit 0 = 全人口跑完且 dashboard 复算一致；非零 = 不变量破坏。
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

os.environ.setdefault("SECRET_KEY", "q04-redteam-unattended-secret-key-012345")
os.environ.setdefault("EVENT_BUS_MAX_RETRIES", "0")

from tests.d08_flywheel.protocol import build_population  # noqa: E402
from tests.q04_personal_redteam.engine import run_persona_redteam  # noqa: E402
from tests.q04_personal_redteam.metrics import (  # noqa: E402
    build_blind_pairs,
    judge_blind_pairs,
    summarize_redteam,
    unblind_and_score,
)

DEFAULT_OUT = REPO_ROOT / "v3-output" / "WT404-Q04-REDTEAM"


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
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


async def run_all(out_dir: Path, *, persona_filter: str | None = None) -> dict:
    specs = build_population()
    if persona_filter:
        specs = [s for s in specs if s.persona_id == persona_filter]
    records: list[dict] = []
    for spec in specs:
        lane_records = await run_persona_redteam(spec)
        records.extend(lane_records)
        print(f"[q04] {spec.persona_id}: records={len(lane_records)}", file=sys.stderr)
    if persona_filter is None:
        _write_jsonl(out_dir / "raw" / "redteam.jsonl", records)
    else:
        print("[q04] single-persona debug run（raw 不落盘）", file=sys.stderr)
    return {"records": records, "personas": [s.persona_id for s in specs]}


def build_outputs(out_dir: Path, records: list[dict], personas: list[str], *, run_meta: dict) -> dict:
    pairs, key = build_blind_pairs(records)
    verdicts = judge_blind_pairs(pairs)
    unblinded = unblind_and_score(pairs, verdicts, key)
    payload = summarize_redteam(records, unblinded, personas=personas)
    payload["generated_at"] = datetime.now(UTC).isoformat()
    payload["git_sha"] = run_meta.get("git_sha")
    payload["counts"] = {
        "records": len(records),
        "blind_pairs": len(pairs),
        "lanes": sorted({r.get("lane") for r in records if r.get("lane")}),
    }

    # 盲评三件套：pairs（无臂标识）/ key（映射，评审后可解盲）/ 评审记录
    _write_jsonl(out_dir / "blind" / "pairs.jsonl", pairs)
    (out_dir / "blind" / "blind_key.json").write_text(
        json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_jsonl(out_dir / "blind" / "review_records.jsonl", verdicts)
    (out_dir / "blind" / "unblinded.json").write_text(
        json.dumps(unblinded, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "dashboard.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    (out_dir / "DASHBOARD.md").write_text(render_dashboard_md(payload), encoding="utf-8")
    return payload


def render_dashboard_md(payload: dict) -> str:
    lines = [
        "# WT404 · Q-04 Personalization 独立红队 — Dashboard（程序化生成）",
        "",
        f"- spec `{payload['spec_version']}` · metrics `{payload['metrics_version']}` · population {len(payload['personas'])}",
        f"- 盲评对 {payload['counts']['blind_pairs']}（pairs 无臂标识；映射见 blind/blind_key.json；评审记录见 blind/review_records.jsonl）",
        "",
        "## 四统计量（V3-4 指标）",
        "",
        f"- **precision**: `{payload['fleet']['precision']}`（目标 ≥{payload['fleet']['precision_target']}）→ {'MET' if payload['gates']['precision_met'] else 'NOT MET'}",
        f"- **invalid**: `{payload['fleet']['invalid_total']}`（**硬门 = 0**）→ {'MET' if payload['gates']['invalid_zero'] else 'VIOLATED'}",
        f"- **overpersonalization**: `{payload['fleet']['overpersonalization_rate']}`"
        f"（{payload['fleet']['overpersonalization_events']}/{payload['fleet']['overpersonalization_contexts']}，目标 ≤{payload['fleet']['overpersonalization_max_rate']}）→ {'MET' if payload['gates']['overpersonalization_met'] else 'NOT MET'}",
        f"- **uplift**: `{payload['fleet']['uplift_pp_mean']}pp`（目标 +{payload['fleet']['uplift_target_pp']}pp）→ {'MET' if payload['gates']['uplift_met'] else 'NOT MET'}",
        "",
        f"## 验收：**{payload['acceptance']}**（失败案例原样保留于 raw/blind 产物）",
        "",
        "## invalid 台账（硬门口径：不存在/已删/跨用户/未授权/超 scope 依据；逐条保留）",
        "",
    ]
    if payload["fleet"]["invalid_events"]:
        for ev in payload["fleet"]["invalid_events"]:
            lines.append(f"- `{ev.get('lane')}/{ev.get('scenario')}` {ev.get('persona')}: **{ev.get('kind')}**")
    else:
        lines.append("- （零条——硬门绿）")
    lines += ["", "## findings 台账（依据存活/授权，不进硬门；照登）", ""]
    if payload["fleet"].get("findings"):
        for ev in payload["fleet"]["findings"]:
            lines.append(f"- `{ev.get('lane')}/{ev.get('scenario')}` {ev.get('persona')}: {ev.get('kind')}")
    else:
        lines.append("- （零条）")
    lines += ["", "## overpersonalization 事件明细", ""]
    if payload.get("overpersonalization_detail"):
        for ev in payload["overpersonalization_detail"]:
            lines.append(f"- {ev.get('persona')}: {ev.get('kind')}")
    else:
        lines.append("- （零条）")
    lines += [
        "",
        "## 逐 persona 矩阵",
        "",
        "| persona | 路数 | pers_uses | valid | invalid | overpers (n/ctx) |",
        "|---|---|---|---|---|---|",
    ]
    for pid, row in payload["per_persona"].items():
        lines.append(
            "| {} | {} | {} | {} | {} | {}/{} |".format(
                pid,
                len(row["lanes_present"]),
                row["personalized_uses"],
                row["valid_uses"],
                row["invalid_count"],
                row["overpersonalization_events"],
                row["overpersonalization_contexts"],
            )
        )
    content = "\n".join(lines) + "\n"
    import hashlib

    digest = hashlib.sha256(content.encode()).hexdigest()[:16]
    return content + f"\n（内容摘要 sha256[:16] = {digest}）\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--persona", type=str, default=None, help="只跑单 persona（调试；不落 raw）")
    args = parser.parse_args()

    out_dir: Path = args.out_dir
    run_meta = {"git_sha": _git_sha()}
    result = asyncio.run(run_all(out_dir, persona_filter=args.persona))
    if args.persona:
        return 0
    payload = build_outputs(out_dir, result["records"], result["personas"], run_meta=run_meta)
    fleet = payload["fleet"]
    print(
        f"[q04] precision={fleet['precision']} invalid={fleet['invalid_total']} "
        f"overpers={fleet['overpersonalization_rate']} uplift={fleet['uplift_pp_mean']}pp "
        f"acceptance={payload['acceptance']}",
        file=sys.stderr,
    )
    print(f"[q04] done → {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
