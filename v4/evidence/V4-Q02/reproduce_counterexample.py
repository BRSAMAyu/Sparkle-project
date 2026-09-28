#!/usr/bin/env python3
"""V4-Q02 · 冻结原反例复现（确定性；零模型调用）。

原反例 = B03 冻结行 ``V3-NEG-A08-POSTFIX-NOMEMORY-BEATS-FULL``
（v4/evidence/V4-B03/negative_results.jsonl）：A-08 修后 no_memory
（11/20=0.55）反超 full（9/20=0.45）——记忆/个性化面净贡献未证明为正。
复现判据（冻结行 falsifiable_criterion）：复算 raw jsonl 的
episode_end/episode_fail 计数与 summary.json / EVAL_RESULTS.md 逐数一致；
no_memory 反超方向成立。

本脚本四步（全部零模型、纯本地）：

  1. VERIFY   六个冻结源工件 sha256 对表冻结行 source_sha256（防漂移）。
  2. RECOMPUTE 冻结 raw 复算：双路径（harness 权威 ``summarize_arm`` +
     独立最小重算）episode 计数与冻结 utility（full=-9.2 / no_memory=0.0），
     反超方向复核（full < no_memory）。
  3. RERUN    当前 SHA 复跑 A-08 harness（full / no_memory 两臂、dev 人口、
     PYTHONHASHSEED=0、V4 旗标全部部署默认），raw 落
     ``runs/repro/raw/``（gitignore 生成物，不碰冻结 v3-output）。
  4. COMPARE  新 raw 对表冻结 raw：逐记录深度比对（首个分歧点定位）+ 新
     summary 复算——V3 基线在 V4 合并后是否逐字节未被扰动，反超方向是否
     仍在当前代码上成立。

exit 0 = 反例在当前 SHA 上复现（方向成立且与冻结 raw 逐记录一致或分歧已
定位）；exit 1 = 复现失败（方向翻转或 sha/计数对表失败）。复现失败不是
评测 FAIL 的反面——它是必须登记的新事实，不静默。

用法（仓库根；backend venv 解释器）::

    SECRET_KEY=... backend/.venv/bin/python \
        v4/evidence/V4-Q02/reproduce_counterexample.py [--skip-rerun] [--write]

边界：L1_CONTROLLABLE_SERVICE_SIMULATION（sqlite 隔离 + fakeredis + 可控时
钟）；零真实 LLM、零模拟器、零浏览器。复现的是既有反例，不是新效果主张。
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

Q02_DIR = Path(__file__).resolve().parent
REPO = Q02_DIR.parents[2]
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "app" / "gen"))

os.environ.setdefault("SECRET_KEY", "q02-repro-local-secret-key-0123456789ab")
os.environ.setdefault("EVENT_BUS_MAX_RETRIES", "0")
os.environ["PYTHONHASHSEED"] = "0"  # A-08 可复现性契约（A-03 B1 tie 的 argmax 次序）

FROZEN_NEG = Q02_DIR.parent / "V4-B03" / "negative_results.jsonl"
FROZEN_ROW_ID = "V3-NEG-A08-POSTFIX-NOMEMORY-BEATS-FULL"
RUNS_DIR = Q02_DIR / "runs" / "repro"

#: 冻结行 falsifiable_criterion 的期望计数。
EXPECTED = {"full": (9, 11), "no_memory": (11, 9)}
#: 冻结 summary 中的 utility（frozen_numbers.full_utility / no_memory_utility）。
EXPECTED_UTILITY = {"full": -9.2, "no_memory": 0.0}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# ---------------------------------------------------------------------------
# 1. VERIFY：sha256 对表
# ---------------------------------------------------------------------------


def verify_sha256(frozen_row: dict) -> dict:
    checks = []
    for rel, expected in sorted(frozen_row["source_sha256"].items()):
        path = REPO / rel
        actual = sha256(path) if path.exists() else None
        checks.append(
            {"artifact": rel, "match": actual == expected, "actual_sha256": actual}
        )
    return {
        "step": "verify_sha256",
        "ok": all(c["match"] for c in checks),
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# 2. RECOMPUTE：冻结 raw 双路径复算
# ---------------------------------------------------------------------------


def independent_recount(records: list[dict]) -> dict:
    """独立最小重算（不复用 harness metrics——第二路径交叉验证）。"""
    resolved = sum(
        1 for r in records if r.get("kind") == "episode_end" and r.get("resolved")
    )
    failed = sum(1 for r in records if r.get("kind") == "episode_fail")
    wrong = sum(
        1
        for r in records
        if r.get("kind") == "stuck"
        and r.get("match_class") == "wrong"
        and r.get("decision_used")
    )
    questions = sum(
        int(r.get("questions_this_session") or 0)
        for r in records
        if r.get("kind") == "stuck"
    )
    intrusions = sum(
        1 for r in records if r.get("kind") == "control" and r.get("control_intrusion")
    )
    utility = resolved - failed - 0.4 * wrong - 0.15 * questions - 0.6 * intrusions
    return {
        "resolved": resolved,
        "failed": failed,
        "followed_wrong": wrong,
        "questions": questions,
        "control_intrusions": intrusions,
        "utility": round(utility, 4),
    }


def recompute_frozen(frozen_row: dict) -> dict:
    from tests.aurora_ablation.metrics import summarize_arm

    raw_dir = REPO / "v3-output/WT412-FRICTION-FIXES/a08-post-fix/raw"
    summary = json.loads(
        (REPO / "v3-output/WT412-FRICTION-FIXES/a08-post-fix/summary.json").read_text()
    )
    frozen_nums = frozen_row["frozen_numbers"]
    arms = {}
    ok = True
    for arm in ("full", "no_memory"):
        records = read_jsonl(raw_dir / f"{arm}.jsonl")
        authority = summarize_arm(records, arm=arm)  # 路径 A：harness 权威复算
        independent = independent_recount(records)  # 路径 B：独立最小重算
        exp_res, exp_fail = EXPECTED[arm]
        arm_ok = (
            (authority["episodes_resolved"], authority["episodes_failed"])
            == (exp_res, exp_fail)
            and (independent["resolved"], independent["failed"]) == (exp_res, exp_fail)
            and authority["episodes_resolved"]
            == summary["summaries"][arm]["episodes_resolved"]
            and abs(authority["utility"] - EXPECTED_UTILITY[arm]) < 1e-6
            and abs(independent["utility"] - EXPECTED_UTILITY[arm]) < 1e-6
            and abs(float(frozen_nums[f"{arm}_utility"]) - EXPECTED_UTILITY[arm]) < 1e-6
        )
        ok = ok and arm_ok
        arms[arm] = {
            "expected_resolved_failed": [exp_res, exp_fail],
            "authority_recomputed": {
                "resolved": authority["episodes_resolved"],
                "failed": authority["episodes_failed"],
                "stuck_accuracy": authority["stuck_accuracy"],
                "utility": authority["utility"],
                "followed_wrong_decisions": authority["followed_wrong_decisions"],
                "questions_total": authority["questions_total"],
                "control_intrusions": authority["control_intrusions"],
            },
            "independent_recount": independent,
            "matches_frozen_row_and_summary": arm_ok,
        }
    direction_holds = (
        arms["full"]["authority_recomputed"]["resolved"]
        < arms["no_memory"]["authority_recomputed"]["resolved"]
    )
    uplift_pp = round(
        100.0
        * (
            arms["no_memory"]["authority_recomputed"]["resolved"] / 20
            - arms["full"]["authority_recomputed"]["resolved"] / 20
        ),
        2,
    )
    return {
        "step": "recompute_frozen_raw",
        "ok": ok and direction_holds,
        "arms": arms,
        "negative_direction": {
            "full_resolved": arms["full"]["authority_recomputed"]["resolved"],
            "no_memory_resolved": arms["no_memory"]["authority_recomputed"]["resolved"],
            "no_memory_beats_full": direction_holds,
            "uplift_no_memory_minus_full_pp": uplift_pp,
            "frozen_uplift_full_minus_no_memory_pp": frozen_nums[
                "uplift_full_minus_no_memory_pp"
            ],
        },
    }


# ---------------------------------------------------------------------------
# 3+4. RERUN + COMPARE：当前 SHA 复跑
# ---------------------------------------------------------------------------


def _deep_diff(frozen: dict, fresh: dict, path: str = "") -> list[str]:
    """逐记录深度比对，返回分歧点（最多 8 条防刷屏）。"""
    diffs: list[str] = []
    if isinstance(frozen, dict) and isinstance(fresh, dict):
        for key in sorted(set(frozen) | set(fresh)):
            if key not in frozen:
                diffs.append(
                    f"{path}.{key}: FRESH_ONLY={json.dumps(fresh[key], ensure_ascii=False)[:120]}"
                )
            elif key not in fresh:
                diffs.append(
                    f"{path}.{key}: FROZEN_ONLY={json.dumps(frozen[key], ensure_ascii=False)[:120]}"
                )
            else:
                diffs.extend(_deep_diff(frozen[key], fresh[key], f"{path}.{key}"))
    elif frozen != fresh:
        diffs.append(
            f"{path}: frozen={json.dumps(frozen, ensure_ascii=False)[:120]} fresh={json.dumps(fresh, ensure_ascii=False)[:120]}"
        )
    return diffs[:8]


_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_HASHID_RE = re.compile(r"^(polpatch|aurora|outc|expshadow|evalver)_[0-9a-f]{32}$")

#: 已声明的记录级分歧类别（复现判据：归一化后逐字节一致）：
#: a) friction_diagnosis_version 注记——冻结 SHA 后诊断引擎版本推进（v1_2→v1_3）；
#: b) 随机 UUID 盐派生身份面（decision_id/patch_id/goal/task id 等）——逐 run 必然不同；
#: c) applied_patch_ids 归因收窄——I05（4cac07ec）把归因面对齐 FIX-67 scope 谓词
#:    （b5e8dedd 上 applied=未过滤全量 effective 集，属已修正的归因/可观测缺陷，
#:    决策行为面不变；本复跑实证聚合全同、仅归因清单收窄）。


def normalize_record(obj: Any, key: str = "") -> Any:
    """归一化 a+b+c 类分歧（id 形值 + 诊断版本注记 + applied 归因键）。

    c 类（applied_patch_ids）整体剔除出对表，另行做**方向检查**：fresh 的
    applied 回合集必须 ⊆ frozen 的 applied 回合集（归因收窄只减不增——出现
    fresh-only 回合 = 未声明的行为分歧，复现判红）。
    """
    if isinstance(obj, dict):
        return {
            k: normalize_record(v, k)
            for k, v in obj.items()
            if k not in ("friction_diagnosis_version", "applied_patch_ids")
        }
    if isinstance(obj, list):
        return [normalize_record(v, key) for v in obj]
    if isinstance(obj, str) and (_UUID_RE.match(obj) or _HASHID_RE.match(obj)):
        return "<id>"
    return obj


def applied_attribution_narrowing_only(
    frozen_records: list[dict], fresh_records: list[dict]
) -> dict:
    """c 类方向检查：applied 归因回合 fresh ⊆ frozen（只收窄不扩张）。"""
    frozen_turns = {
        i
        for i, r in enumerate(frozen_records)
        if (r.get("chat") or {}).get("applied_patch_ids")
    }
    fresh_turns = {
        i
        for i, r in enumerate(fresh_records)
        if (r.get("chat") or {}).get("applied_patch_ids")
    }
    return {
        "narrowing_only": fresh_turns <= frozen_turns,
        "frozen_only_turns": sorted(frozen_turns - fresh_turns),
        "fresh_only_turns": sorted(fresh_turns - frozen_turns),
        "frozen_turns": len(frozen_turns),
        "fresh_turns": len(fresh_turns),
    }


async def rerun_current_sha() -> dict:
    from tests.aurora_ablation.engine import run_persona_arm
    from tests.aurora_ablation.metrics import summarize_arm
    from tests.aurora_ablation.persona import build_population

    raw_dir = RUNS_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    specs = build_population()
    per_arm: dict[str, dict] = {}
    for arm in ("full", "no_memory"):
        records: list[dict] = []
        for spec in specs:
            records.extend(await run_persona_arm(spec, arm=arm))
        out = raw_dir / f"{arm}.jsonl"
        with out.open("w", encoding="utf-8") as fh:
            for row in records:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        summary = summarize_arm(records, arm=arm)
        per_arm[arm] = {
            "records": len(records),
            "resolved": summary["episodes_resolved"],
            "failed": summary["episodes_failed"],
            "stuck_accuracy": summary["stuck_accuracy"],
            "utility": summary["utility"],
        }
        print(
            f"[q02-repro] arm={arm} records={len(records)} resolved={summary['episodes_resolved']} utility={summary['utility']}",
            file=sys.stderr,
        )
    return per_arm


def compare_with_frozen(fresh: dict[str, dict]) -> dict:
    frozen_raw_dir = REPO / "v3-output/WT412-FRICTION-FIXES/a08-post-fix/raw"
    fresh_raw_dir = RUNS_DIR / "raw"
    arms = {}
    for arm in ("full", "no_memory"):
        frozen_records = read_jsonl(frozen_raw_dir / f"{arm}.jsonl")
        fresh_records = read_jsonl(fresh_raw_dir / f"{arm}.jsonl")
        identical = frozen_records == fresh_records
        first_divergence: list[str] = []
        if not identical:
            for i, (fr, frsh) in enumerate(
                zip(frozen_records, fresh_records, strict=False)
            ):
                if fr != frsh:
                    first_divergence = [f"record[{i}]"] + _deep_diff(fr, frsh)
                    break
            if not first_divergence:
                first_divergence = [
                    f"record_count frozen={len(frozen_records)} fresh={len(fresh_records)}"
                ]
        # 归一化对表（声明分歧类别 a+b+c 归一后应逐字节一致）；c 类另做方向
        # 检查（applied 归因只收窄不扩张）。
        normalized_identical = [normalize_record(r) for r in frozen_records] == [
            normalize_record(r) for r in fresh_records
        ]
        narrowing = applied_attribution_narrowing_only(frozen_records, fresh_records)
        applied_frozen = narrowing["frozen_turns"]
        applied_fresh = narrowing["fresh_turns"]
        arms[arm] = {
            "frozen_records": len(frozen_records),
            "fresh_records": len(fresh_records),
            "byte_identical_records": identical,
            "normalized_identical": normalized_identical,
            "applied_attribution_narrowing": narrowing,
            "applied_attribution_turns_frozen": applied_frozen,
            "applied_attribution_turns_fresh": applied_fresh,
            "first_divergence": first_divergence,
            "fresh_summary": fresh[arm],
        }
    fresh_direction = fresh["full"]["resolved"] < fresh["no_memory"]["resolved"]
    uplift_pp = round(
        100.0 * (fresh["no_memory"]["resolved"] / 20 - fresh["full"]["resolved"] / 20),
        2,
    )
    aggregates_identical = all(
        arms[arm]["fresh_summary"]["resolved"] == EXPECTED[arm][0]
        and arms[arm]["fresh_summary"]["utility"] == EXPECTED_UTILITY[arm]
        for arm in ("full", "no_memory")
    )
    return {
        "step": "rerun_current_sha_compare",
        "arms": arms,
        "aggregates_match_frozen": aggregates_identical,
        "fresh_negative_direction": {
            "full_resolved": fresh["full"]["resolved"],
            "no_memory_resolved": fresh["no_memory"]["resolved"],
            "no_memory_beats_full": fresh_direction,
            "uplift_no_memory_minus_full_pp": uplift_pp,
        },
        "fresh_utility": {arm: fresh[arm]["utility"] for arm in fresh},
        "declared_divergence_classes": [
            "a) friction_diagnosis_version 注记推进（v1_2→v1_3，冻结 SHA 后版本 bump）",
            "b) 随机 UUID 盐派生身份面（decision_id/patch_id/goal/task id，逐 run 必然不同）",
            "c) applied_patch_ids 归因收窄（I05 4cac07ec 对齐 FIX-67 scope 谓词；"
            "b5e8dedd 上 applied=未过滤全量 effective 集——已修正的归因缺陷；聚合行为面实证全同）",
        ],
        "normalized_comparison_note": "a+b 归一化后逐字节一致=行为面未被扰动；c 类只影响归因清单不影响决策与结局",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--skip-rerun", action="store_true", help="只做 sha+重算两步（不重跑 harness）"
    )
    ap.add_argument(
        "--write", action="store_true", help="结果写 runs/repro_result.json"
    )
    args = ap.parse_args()

    rows = [json.loads(l) for l in FROZEN_NEG.open(encoding="utf-8") if l.strip()]
    frozen_row = next(r for r in rows if r["id"] == FROZEN_ROW_ID)

    git_sha = (
        os.popen("git rev-parse HEAD").read().strip()
        if (REPO / ".git").exists()
        else "unknown"
    )
    result: dict = {
        "task": "V4-Q02",
        "kind": "FROZEN_COUNTEREXAMPLE_REPRODUCE_ZERO_MODEL_CALLS",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "repo_head": git_sha,
        "frozen_row_id": FROZEN_ROW_ID,
        "evidence_layer": "L1_CONTROLLABLE_SERVICE_SIMULATION (VERIFY+RECOMPUTE+RERUN; 零真实 LLM)",
        "flags_at_run": {
            "ENABLE_MEMORY_UTILITY_GATE": "部署默认 False",
            "EXPERIENCE_STRATEGY_MODE": "部署默认 shadow（零行为）",
            "NO_ACTION_CORRECTION_MODE": "部署默认 off",
        },
    }

    step1 = verify_sha256(frozen_row)
    step2 = recompute_frozen(frozen_row)
    result["steps"] = [step1, step2]
    ok = step1["ok"] and step2["ok"]

    if not args.skip_rerun:
        fresh = asyncio.run(rerun_current_sha())
        step3 = compare_with_frozen(fresh)
        result["steps"].append(step3)
        ok = (
            ok
            and step3["fresh_negative_direction"]["no_memory_beats_full"]
            and step3["aggregates_match_frozen"]
            and all(step3["arms"][arm]["normalized_identical"] for arm in step3["arms"])
            and all(
                step3["arms"][arm]["applied_attribution_narrowing"]["narrowing_only"]
                for arm in step3["arms"]
            )
        )
        result["reproduced_on_current_sha"] = step3["fresh_negative_direction"][
            "no_memory_beats_full"
        ]
        result["aggregates_match_frozen"] = step3["aggregates_match_frozen"]
        result["records_normalized_identical_to_frozen"] = {
            arm: step3["arms"][arm]["normalized_identical"] for arm in step3["arms"]
        }
        result["declared_divergence_classes"] = step3["declared_divergence_classes"]
    else:
        result["reproduced_on_current_sha"] = None

    result["counterexample_reproduced"] = ok
    result["verdict"] = (
        "REPRODUCED"
        if ok
        else "NOT_REPRODUCED divergence documented (new fact, not silenced)"
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.write:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        (RUNS_DIR / "repro_result.json").write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
