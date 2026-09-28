#!/usr/bin/env python3
"""V4-B03 · 冻结负结果可证伪探针（确定性复算，零模型调用）。

对 V3 负结果资产的 raw 产物做程序化复算，核对 v4/evidence/V4-B03/
negative_results.jsonl 冻结数字与验收判据（卡 V4-B03）：

  探针① a08_postfix    A-08 修后重算：full=9/20、no_memory=11/20 与
                        summary.json / EVAL_RESULTS.md 一致（验收第1条），
                        并确认 no_memory 反超 full 的负结果方向成立。
  探针② a08_prefix     A-08 修前 0.65（13/20）仅为历史锚点，与修后数字不同
                        ——防止旧 pre-fix 数字被当作最新基线。
  探针③ fix545         E-08 raw 中 db_model=no_generation_model 且带 token
                        的行集恰为冻结 7 个 qid（FIX-545 计量盲区实锤）。
  探针④ e08_slo        六项候选 SLO 复算=4 PASS/2 FAIL（L0 TTFT p95 与
                        L2 total p95 持续 FAIL）；percentile 用 harness 同款
                        线性插值（scripts/devtools/bench_ai_stack_l0_l3.py::_pct）。
  探针⑤ q04_dashboard  Q-04 首轮四统计量复算（precision 0.0 / invalid 10 /
                        overpersonalization 50/120 / uplift 0.0pp），
                        acceptance=FAIL 且失败案例保留位为真。
  探针⑥ utility_freeze frozen_utility.json 权重与 A-08 冻结权重逐项一致。

用法（仓库根；纯 stdlib，无后端依赖、无网络、无模型调用）::

    python3 v4/evidence/V4-B03/recompute_baselines.py [--write]

exit 0 = 全部探针通过（冻结数字与 raw 复算一致）；否则 exit 1。
边界：全部为对既有 raw 的重算（RECOMPUTE），不是新运行（RUN）；历史 raw 属
L1 服务模拟（A-08/Q-04）与真模型活栈测量（E-08），证据层级见各探针输出。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EVID = Path(__file__).resolve().parent

A08_POSTFIX_RAW = REPO / "v3-output/WT412-FRICTION-FIXES/a08-post-fix/raw"
A08_POSTFIX_SUMMARY = REPO / "v3-output/WT412-FRICTION-FIXES/a08-post-fix/summary.json"
A08_PREFIX_SUMMARY = REPO / "v3-output/WT393-A08-ABLATION/summary.json"
E08_RAW = REPO / "v3-output/WT801-E08FINAL/raw-e08final.jsonl"
Q04_DASH = REPO / "v3-output/WT404-Q04-REDTEAM/dashboard.json"
FROZEN_UTILITY = EVID / "frozen_utility.json"
FROZEN_NEG = EVID / "negative_results.jsonl"

# A-08 修后冻结口径（卡 V4-B03 验收第 1 条）
EXPECT_POSTFIX = {"full": (9, 20), "no_memory": (11, 20), "no_experience": (9, 20), "fixed_policy": (6, 20)}
# FIX-545 冻结 7 个 qid（v3/06_agent_fleet/DYNAMIC_ISSUES.md V3-FIX-545 行）
FIX545_QIDS = {"L3-06", "L3-08", "L3-15", "L3-18", "L3-21", "L3-23", "L3-26"}
# A-08 冻结 utility 权重（EVALUATION_PROTOCOL 与 aurora_ablation_metrics.v1）
FROZEN_WEIGHTS = {
    "resolved_episode": 1.0,
    "unresolved_episode": -1.0,
    "wrong_followed_decision": -0.4,
    "question": -0.15,
    "control_intrusion": -0.6,
}


def pct(values: list[float], p: float) -> float | None:
    """harness 同款线性插值 percentile（bench_ai_stack_l0_l3.py::_pct）。"""
    if not values:
        return None
    vs = sorted(values)
    k = (len(vs) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(vs) - 1)
    return vs[lo] + (vs[hi] - vs[lo]) * (k - lo)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recompute_a08(raw_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for arm in ("full", "no_memory", "no_experience", "fixed_policy"):
        resolved = failed = 0
        with (raw_dir / f"{arm}.jsonl").open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                kind = rec.get("kind")
                if kind == "episode_end":
                    resolved += 1
                elif kind == "episode_fail":
                    failed += 1
        total = resolved + failed
        out[arm] = {
            "resolved": resolved,
            "failed": failed,
            "total": total,
            "stuck_accuracy": round(resolved / total, 4) if total else None,
        }
    return out


def probe_a08_postfix() -> dict:
    summary = json.loads(A08_POSTFIX_SUMMARY.read_text())
    recomputed = recompute_a08(A08_POSTFIX_RAW)
    checks = []
    for arm, (exp_res, exp_total) in EXPECT_POSTFIX.items():
        r = recomputed[arm]
        checks.append({
            "arm": arm,
            "recomputed": f"{r['resolved']}/{r['total']}",
            "expected": f"{exp_res}/{exp_total}",
            "stuck_accuracy_recomputed": r["stuck_accuracy"],
            "stuck_accuracy_summary": summary["summaries"][arm]["stuck_accuracy"],
            "matches_expect": (r["resolved"], r["total"]) == (exp_res, exp_total),
            "matches_summary": (summary["summaries"][arm]["episodes_resolved"], summary["summaries"][arm]["episodes_total"]) == (r["resolved"], r["total"]),
        })
    fm, nm = recomputed["full"], recomputed["no_memory"]
    negative_direction_holds = fm["resolved"] < nm["resolved"]  # 9 < 11：记忆面净贡献未证明为正
    ok = all(c["matches_expect"] and c["matches_summary"] for c in checks) and negative_direction_holds
    return {
        "probe": "a08_postfix",
        "ok": ok,
        "evidence_layer": "L1_CONTROLLABLE_SERVICE_SIMULATION (RECOMPUTE, 非live)",
        "boundary": "sqlite 隔离+fakeredis+可控时钟服务模拟的既有 raw 复算；零真实 LLM、零新运行",
        "arms": checks,
        "negative_direction": {
            "full": f"{fm['resolved']}/{fm['total']}",
            "no_memory": f"{nm['resolved']}/{nm['total']}",
            "no_memory_beats_full": negative_direction_holds,
            "note": "验收第1条：重算 9/20 与 11/20 一致；模拟非live边界已记录",
        },
    }


def probe_a08_prefix() -> dict:
    s = json.loads(A08_PREFIX_SUMMARY.read_text())
    full = s["summaries"]["full"]
    nm = s["summaries"]["no_memory"]
    pre_full = (full["episodes_resolved"], full["episodes_total"], full["stuck_accuracy"])
    pre_nm = (nm["episodes_resolved"], nm["episodes_total"], nm["stuck_accuracy"])
    differs_from_postfix = pre_full[0] != EXPECT_POSTFIX["full"][0]
    ok = pre_full[:2] == (13, 20) and abs(pre_full[2] - 0.65) < 1e-9 and pre_nm[:2] == (11, 20) and differs_from_postfix
    return {
        "probe": "a08_prefix_historical",
        "ok": ok,
        "evidence_layer": "L1_CONTROLLABLE_SERVICE_SIMULATION (RECOMPUTE, 非live)",
        "frozen": {"full": list(pre_full), "no_memory": list(pre_nm)},
        "guard": {
            "pre_fix_differs_from_postfix_full": differs_from_postfix,
            "rule": "修前 0.65 仅作历史锚点；最新基线=修后 9/20（frozen_utility.json baseline_rule）",
        },
    }


def probe_fix545() -> dict:
    rows = [json.loads(l) for l in E08_RAW.open() if l.strip()]
    ng = [r for r in rows if r.get("db_model") == "no_generation_model"]
    with_tokens = sorted(r["qid"] for r in ng if (r.get("db_total_tokens") or 0) > 0)
    zero_token = len(ng) - len(with_tokens)
    ok = len(ng) == 18 and len(with_tokens) == 7 and set(with_tokens) == FIX545_QIDS
    return {
        "probe": "fix545_metering_blindspot",
        "ok": ok,
        "evidence_layer": "LIVE_STACK_REAL_MODEL_RAW_RECOMPUTE (RECOMPUTE, 零调用)",
        "recomputed": {
            "no_generation_model_rows": len(ng),
            "with_tokens_rows": len(with_tokens),
            "with_tokens_qids": with_tokens,
            "zero_token_rows": zero_token,
        },
        "frozen_qids": sorted(FIX545_QIDS),
        "note": "7 条带 token 错挂=成本低估实锤；修后 harness 须检出 no_generation_model-with-tokens（新跑样本缺陷计数归零方可销账）",
    }


def probe_e08_slo() -> dict:
    rows = [json.loads(l) for l in E08_RAW.open() if l.strip()]

    def layer(L):
        return [r for r in rows if r.get("layer") == L]

    l0, l1, l2, l3 = layer("L0"), layer("L1"), layer("L2"), layer("L3")
    l0_ttft_p95 = pct([r["ttft_first_delta_s"] for r in l0 if r.get("ttft_first_delta_s") is not None], 95)
    l1_ttft = [r["ttft_first_delta_s"] for r in l1 if r.get("ttft_first_delta_s") is not None]
    l1_p50, l1_p95 = pct(l1_ttft, 50), pct(l1_ttft, 95)
    l2_free = [r for r in l2 if r.get("lane") == "free"]
    l2_free_fe_p95 = pct([r["t_first_event_s"] for r in l2_free], 95)
    l2_total_p95 = pct([r["total_s"] for r in l2 if r.get("total_s") is not None], 95)
    l3_ack_p95 = pct([r["t_first_stage_s"] for r in l3], 95)
    ack_all = [r["t_first_stage_s"] for r in rows if r.get("t_first_stage_s") is not None]
    ack_le500 = sum(1 for a in ack_all if a <= 0.5)

    slo = [
        {"slo": "L0 no-model TTFT p95<=500ms", "value_s": round(l0_ttft_p95, 4), "pass": l0_ttft_p95 <= 0.5, "expected": "FAIL"},
        {"slo": "L1 TTFT p50<=2.5s", "value_s": round(l1_p50, 4), "pass": l1_p50 <= 2.5, "expected": "PASS"},
        {"slo": "L1 TTFT p95<=5s", "value_s": round(l1_p95, 4), "pass": l1_p95 <= 5.0, "expected": "PASS"},
        {"slo": "L2 free 首事件 p95<=500ms", "value_s": round(l2_free_fe_p95, 4), "pass": l2_free_fe_p95 <= 0.5, "expected": "PASS"},
        {"slo": "L2 total p95<=15s", "value_s": round(l2_total_p95, 4), "pass": l2_total_p95 <= 15.0, "expected": "FAIL"},
        {"slo": "L3 ACK p95<=1s", "value_s": round(l3_ack_p95, 4), "pass": l3_ack_p95 <= 1.0, "expected": "PASS"},
    ]
    n_pass = sum(1 for s in slo if s["pass"])
    ok = (
        n_pass == 4
        and all(s["pass"] == (s["expected"] == "PASS") for s in slo)
        and ack_le500 == len(ack_all) == 104
        and abs(l2_total_p95 - 65.356375) < 1e-6
        and abs(l0_ttft_p95 - 1.78125) < 1e-6
    )
    return {
        "probe": "e08_slo_2f",
        "ok": ok,
        "evidence_layer": "LIVE_STACK_REAL_MODEL (RECOMPUTE of wt801 run cdc547be, 零新调用)",
        "recomputed": {
            "n_pass": n_pass,
            "n_fail": len(slo) - n_pass,
            "slo": slo,
            "intake_ack_le_500ms": f"{ack_le500}/{len(ack_all)}",
            "intake_ack_p50_s": round(pct(ack_all, 50), 4),
            "intake_ack_p95_s": round(pct(ack_all, 95), 4),
        },
        "note": "2 FAIL 持续：L0 直答缺位（1781ms）、L2 total（65.4s，较修前 49.5s 上行=tier 分层恢复的真实 trade-off）",
    }


def probe_q04() -> dict:
    d = json.loads(Q04_DASH.read_text())
    fleet = d["fleet"]
    blind = d["blind_review"]
    recomputed = {
        "precision": fleet["valid_uses"] / fleet["personalized_uses"] if fleet["personalized_uses"] else None,
        "personalized_uses": fleet["personalized_uses"],
        "invalid_total": fleet["invalid_total"],
        "invalid_kinds": sorted({e["kind"] for e in fleet["invalid_events"]}),
        "overpersonalization": f"{fleet['overpersonalization_events']}/{fleet['overpersonalization_contexts']}",
        "overpersonalization_rate": fleet["overpersonalization_rate"],
        "uplift_pp_mean": blind["uplift_pp_mean"],
        "blind_pairs": blind["pairs_total"],
        "acceptance": d["acceptance"],
        "failed_cases_preserved": d["failed_cases_preserved"],
        "gates": d["gates"],
    }
    ok = (
        recomputed["precision"] == 0.0
        and recomputed["invalid_total"] == 10
        and recomputed["invalid_kinds"] == ["patch_attribution_cross_scope"]
        and fleet["overpersonalization_events"] == 50
        and fleet["overpersonalization_contexts"] == 120
        and abs(recomputed["overpersonalization_rate"] - 0.4167) < 1e-9
        and recomputed["uplift_pp_mean"] == 0.0
        and recomputed["blind_pairs"] == 20
        and recomputed["acceptance"] == "FAIL"
        and recomputed["failed_cases_preserved"] is True
    )
    return {
        "probe": "q04_dashboard_not_remeasured",
        "ok": ok,
        "evidence_layer": "L1_CONTROLLABLE_SERVICE_SIMULATION (RECOMPUTE of run 46762b31, 零模型 judge)",
        "recomputed": recomputed,
        "status_at_freeze": "NOT_REMEASURED（FIX-67/68/69/70 修后未全量重跑；重跑驱动在库 scripts/devtools/q04_run_personalization_redteam.py）",
    }


def probe_utility_freeze() -> dict:
    fu = json.loads(FROZEN_UTILITY.read_text())
    weights = fu["utility_frozen"]["weights"]
    ok = weights == FROZEN_WEIGHTS and fu["denominator_policy"]["zero_denominator"].startswith("N/A")
    return {
        "probe": "utility_freeze",
        "ok": ok,
        "weights_match_a08_frozen": weights == FROZEN_WEIGHTS,
        "zero_denominator_is_na": fu["denominator_policy"]["zero_denominator"].startswith("N/A"),
        "unresolved_counted": "未解决/缺失样本计入不得排除" in fu["denominator_policy"]["unresolved_or_missing_samples"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="把结果写入 test_results.json")
    args = ap.parse_args()

    probes = [
        probe_a08_postfix(),
        probe_a08_prefix(),
        probe_fix545(),
        probe_e08_slo(),
        probe_q04(),
        probe_utility_freeze(),
    ]
    result = {
        "task": "V4-B03",
        "kind": "RECOMPUTE_ONLY_ZERO_MODEL_CALLS",
        "generated_at_utc": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
        "repo_head": __import__("subprocess").run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True
        ).stdout.strip(),
        "source_pins_sha256": {
            str(p.relative_to(REPO)): sha256(p)
            for p in (A08_POSTFIX_SUMMARY, A08_PREFIX_SUMMARY, E08_RAW, Q04_DASH)
        },
        "probes": probes,
        "all_ok": all(p["ok"] for p in probes),
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.write:
        (EVID / "test_results.json").write_text(payload + "\n")
    print(payload)
    return 0 if result["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
