"""P-05 · 指标汇总：全部数字由 raw 记录程序化计算（不手填）.

两轴口径（acceptance 要求的量化对照）：

- **恢复轴**：restart 率（停滞 persona 在时间线内出现 ≥1 次真实任务完成）、
  重启中位天数、deadline 达成率（账本全部完成且完成时刻 ≤ 计划截止）、
  期末账本进度均值；
- **负担轴**：建议投放量（人均/最坏）、每次重启的打扰次数、ignore 率
  （silent/dismiss）、mute 率、accept 率，以及正确性计数（mute 后复发=0、
  接受后 24h 内复发=0、授权撤销后 auto=0——违例即红）。

样本量与口径如实随 summary 输出；persona 决策模型参数在 raw
``events_timeline.json`` 中全量披露。
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from typing import Any

__all__ = ["summarize_group", "compare_groups", "render_markdown"]

_ARCS = ("stalled", "deadline", "completion")


def _by_persona(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        out[str(record["persona"])].append(record)
    return dict(out)


def summarize_group(records: list[dict[str, Any]], *, group: str, days: int) -> dict[str, Any]:
    personas = _by_persona(records)
    n = len(personas)
    arc_counts = Counter(str(p[0]["arc"]) for p in personas.values())

    stalled_personas: set[str] = set()
    restart_day: dict[str, int] = {}
    deadline_met: dict[str, bool] = {}
    final_ledger: dict[str, int] = {}
    final_ledger_total: dict[str, int] = {}

    for pid, rows in personas.items():
        first_stalled: int | None = None
        for row in rows:
            if row["kind"] == "day":
                if row.get("stalled") and first_stalled is None:
                    first_stalled = int(row["sim_day"])
                final_ledger[pid] = int(row.get("ledger_done") or 0)
                final_ledger_total[pid] = int(row.get("ledger_total") or 0)
            elif row["kind"] == "lifecycle" and row.get("event") == "intrinsic_restart":
                if row.get("ledger_done") and first_stalled is not None and int(row["sim_day"]) >= first_stalled:
                    restart_day.setdefault(pid, int(row["sim_day"]))
                if row.get("ledger_completed"):
                    deadline_met[pid] = bool(row.get("deadline_met"))
        # suggestion 驱动的重启（行动真实执行才计入）
        for row in rows:
            if row["kind"] != "suggestion" or row.get("disposition") != "accept":
                continue
            actions = ((row.get("action") or {}).get("actions")) or []
            if not any(a.get("executed") and a.get("step") == "COMPLETED" for a in actions):
                continue
            if first_stalled is not None and int(row["sim_day"]) >= first_stalled:
                restart_day.setdefault(pid, int(row["sim_day"]))
            if (row.get("action") or {}).get("ledger_completed"):
                deadline_met[pid] = bool((row.get("action") or {}).get("deadline_met"))
        if first_stalled is not None:
            stalled_personas.add(pid)

    suggestions = [r for r in records if r["kind"] == "suggestion"]
    generations = [r for r in records if r["kind"] == "generation"]
    dispositions = Counter(str(s.get("disposition")) for s in suggestions)
    skip_reasons = Counter(
        (
            f"{r.get('reason')}:{(r.get('suppression') or {}).get('reason')}"
            if r.get("reason") == "suggestion_suppressed"
            else str(r.get("reason"))
        )
        for r in generations
        if r.get("result") == "skipped"
    )

    # 正确性计数（负担面的不变量；违例 >0 即评估红）
    mute_day: dict[str, int] = {}
    revoke_day: dict[str, int] = {}
    for row in records:
        pid = str(row.get("persona"))
        if row["kind"] == "lifecycle" and row.get("event") == "persona_mute":
            mute_day[pid] = int(row["sim_day"])
        if row["kind"] == "lifecycle" and row.get("event") == "auto_revoke":
            revoke_day[pid] = int(row["sim_day"])
        # 决策模型里的 mute（同 suggestion 记录）也是静音日
        if row["kind"] == "suggestion" and row.get("disposition") == "mute":
            mute_day.setdefault(pid, int(row["sim_day"]))
    # 静音「之后」的投放才计违例（mute 当日早间的建议是 mute 的触发者，不算复发）
    post_mute_deliveries = sum(1 for s in suggestions if int(s["sim_day"]) > mute_day.get(str(s["persona"]), 10**9))
    post_revoke_auto_steps = sum(
        1
        for s in suggestions
        for a in ((s.get("action") or {}).get("actions") or [])
        if int(s["sim_day"]) >= revoke_day.get(str(s["persona"]), 10**9) and a.get("mode") == "auto"
    )
    # accept 次日又收到建议（真实 Eligibility: 活动后 days_away<3 → 不应投放）
    redeliver_after_accept = {
        (str(s["persona"]), int(s["sim_day"]) + 1) for s in suggestions if s.get("disposition") == "accept"
    }
    next_day_redeliveries = sum(
        1 for s in suggestions if (str(s["persona"]), int(s["sim_day"])) in redeliver_after_accept
    )
    sub_threshold_deliveries = sum(1 for s in suggestions if int(s.get("days_away") or 0) < 3)
    # 「目标完成后仍投放」以生成时刻的账本状态为准（day 记录 = 当日生成前状态）；
    # sprint 账本完成会触发 auto-archive → 主动面停（正控），此处应为 0
    completed_day_keys = {
        (str(r["persona"]), int(r["sim_day"]))
        for r in records
        if r["kind"] == "day"
        and r.get("ledger_total")
        and r.get("ledger_done") == r.get("ledger_total")
        and r.get("ledger_completed_at") is not None
        and float(r["ledger_completed_at"]) < int(r["sim_day"])
    }
    post_completion_deliveries = sum(
        1 for s in suggestions if (str(s["persona"]), int(s["sim_day"])) in completed_day_keys
    )
    expired_day_keys = {
        (str(r["persona"]), int(r["sim_day"])) for r in records if r["kind"] == "day" and r.get("plan_expired")
    }
    while_expired_deliveries = sum(1 for s in suggestions if (str(s["persona"]), int(s["sim_day"])) in expired_day_keys)
    auto_steps = Counter(
        a.get("mode") for s in suggestions for a in ((s.get("action") or {}).get("actions") or []) if a.get("executed")
    )
    pm_probes = [r for r in generations if r.get("slot") == "pm"]
    pm_cooldown_blocked = sum(
        1
        for r in pm_probes
        if r.get("reason") == "suggestion_suppressed" and (r.get("suppression") or {}).get("reason") == "cooldown"
    )

    restarted = sorted(restart_day)
    deadline_achieved = sorted(pid for pid, ok in deadline_met.items() if ok)
    per_persona_suggestions = [len([s for s in suggestions if s["persona"] == pid]) for pid in personas]

    return {
        "group": group,
        "days": days,
        "personas": n,
        "arc_counts": dict(arc_counts),
        "recovery": {
            "stalled_personas": len(stalled_personas),
            "restarted_personas": len(restarted),
            "restart_rate": round(len(restarted) / n, 4) if n else None,
            "median_days_to_restart": (statistics.median([restart_day[p] for p in restarted]) if restarted else None),
            "deadline_achieved_personas": len(deadline_achieved),
            "deadline_achievement_rate": (round(len(deadline_achieved) / n, 4) if n else None),
            "mean_final_ledger_progress": (
                round(
                    statistics.mean(
                        ((final_ledger.get(pid, 0) / final_ledger_total[pid]) if final_ledger_total.get(pid) else 0.0)
                        for pid in personas
                    ),
                    4,
                )
                if n
                else None
            ),
        },
        "burden": {
            "generation_attempts": len(generations),
            "suggestions_issued": len(suggestions),
            "suggestions_per_persona_mean": (round(statistics.mean(per_persona_suggestions), 3) if n else None),
            "suggestions_per_persona_max": (max(per_persona_suggestions) if per_persona_suggestions else 0),
            "interruptions_per_restarted_persona": (round(len(suggestions) / len(restarted), 3) if restarted else None),
            "dispositions": dict(dispositions),
            "accept_rate": (round(dispositions.get("accept", 0) / len(suggestions), 4) if suggestions else None),
            "silent_ignore_rate": (round(dispositions.get("silent", 0) / len(suggestions), 4) if suggestions else None),
            "dismiss_rate": (round(dispositions.get("dismiss", 0) / len(suggestions), 4) if suggestions else None),
            "mute_rate": (round(dispositions.get("mute", 0) / len(suggestions), 4) if suggestions else None),
            "skip_reasons": dict(skip_reasons),
            "pm_probes": len(pm_probes),
            "pm_probes_cooldown_blocked": pm_cooldown_blocked,
            "correctness": {
                "post_mute_deliveries": post_mute_deliveries,
                "next_day_redeliveries_after_accept": next_day_redeliveries,
                "sub_threshold_deliveries": sub_threshold_deliveries,
                "post_auto_revoke_auto_steps": post_revoke_auto_steps,
                "executed_steps_by_mode": dict(auto_steps),
                "post_ledger_complete_deliveries": post_completion_deliveries,
                "deliveries_while_plan_expired": while_expired_deliveries,
            },
        },
    }


def compare_groups(proactive: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    def delta(key_a: Any, key_b: Any) -> Any:
        if isinstance(key_a, (int, float)) and isinstance(key_b, (int, float)):
            return round(key_a - key_b, 4)
        return None

    return {
        "restart_rate_delta": delta(proactive["recovery"]["restart_rate"], baseline["recovery"]["restart_rate"]),
        "deadline_achievement_rate_delta": delta(
            proactive["recovery"]["deadline_achievement_rate"],
            baseline["recovery"]["deadline_achievement_rate"],
        ),
        "mean_final_ledger_progress_delta": delta(
            proactive["recovery"]["mean_final_ledger_progress"],
            baseline["recovery"]["mean_final_ledger_progress"],
        ),
        "median_days_to_restart": {
            "proactive": proactive["recovery"]["median_days_to_restart"],
            "baseline": baseline["recovery"]["median_days_to_restart"],
        },
    }


def render_markdown(
    summary: dict[str, Any],
    *,
    meta: dict[str, Any],
) -> str:
    """从 raw 计算出的 summary → Markdown 伴生报告（机读 summary.json 为权威）。"""
    proactive = summary["proactive"]
    baseline = summary["baseline"]
    lines: list[str] = []
    lines.append("# P-05 Proactive Longitudinal Evaluation — Results")
    lines.append("")
    lines.append(
        f"- git SHA: `{meta['git_sha']}` ｜ 运行：{meta['ran_at']} ｜ seed={meta['seed']} ｜ "
        f"每组 {proactive['personas']} persona（{proactive['arc_counts']}）× {proactive['days']} 模拟天"
    )
    lines.append("")
    lines.append("## 口径声明（如实）")
    lines.append("")
    lines.append(
        "- 样本：每组同一份 seeded persona 总体（24 = stalled/deadline/completion 各 8），两组唯一差异是主动面开/关。"
    )
    lines.append(
        "- 生成/抑制/投递/行动/授权全部经真实服务（comeback 任务直调 + ActionCommand/Permission/FeedbackService）；"
    )
    lines.append("  模拟时钟以 backdate 换算（活动痕迹/计划窗口/建议时间/cooldown 尾每 tick 重写为真实时间戳）。")
    lines.append(
        "- persona 决策（accept/dismiss/mute/silent）与内在自发重启是 **seeded 显式模型**（参数全量在 events_timeline.json）；"
    )
    lines.append("  量化结论 = 该模型 + 真实主动面行为的联合结果，不是真人 RCT——量级读法见 REPORT。")
    lines.append("")
    lines.append("## 两组对照（恢复轴 × 负担轴）")
    lines.append("")
    lines.append("| 指标 | proactive | baseline | Δ |")
    lines.append("|---|---|---|---|")
    rp, rb = proactive["recovery"], baseline["recovery"]
    bp, bb = proactive["burden"], baseline["burden"]
    lines.append(
        f"| restart 率（停滞→重启） | {rp['restart_rate']} | {rb['restart_rate']} | {summary['compare']['restart_rate_delta']} |"
    )
    lines.append(f"| 重启中位天数 | {rp['median_days_to_restart']} | {rb['median_days_to_restart']} | - |")
    lines.append(
        f"| deadline 达成率 | {rp['deadline_achievement_rate']} | {rb['deadline_achievement_rate']} | {summary['compare']['deadline_achievement_rate_delta']} |"
    )
    lines.append(
        f"| 期末账本进度均值 | {rp['mean_final_ledger_progress']} | {rb['mean_final_ledger_progress']} | {summary['compare']['mean_final_ledger_progress_delta']} |"
    )
    lines.append(f"| 建议投放量 | {bp['suggestions_issued']} | {bb['suggestions_issued']} | - |")
    lines.append(
        f"| 人均建议（最坏 persona） | {bp['suggestions_per_persona_mean']}（{bp['suggestions_per_persona_max']}） | {bb['suggestions_per_persona_mean']}（{bb['suggestions_per_persona_max']}） | - |"
    )
    lines.append(
        f"| 每重启 persona 打扰次数 | {bp['interruptions_per_restarted_persona']} | {bb['interruptions_per_restarted_persona']} | - |"
    )
    lines.append(f"| disposition（accept/silent/dismiss/mute） | {bp['dispositions']} | {bb['dispositions']} | - |")
    lines.append("")
    lines.append("## 主动面正确性计数（违例 >0 即红）")
    lines.append("")
    for key, value in bp["correctness"].items():
        lines.append(f"- {key}: **{value}**")
    lines.append("")
    lines.append("## 跳过原因分布（真源抑制的证据）")
    lines.append("")
    for key, value in sorted(bp["skip_reasons"].items()):
        lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines) + "\n"
