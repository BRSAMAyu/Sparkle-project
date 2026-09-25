"""A-08 · raw → summary 确定性指标计算（纯函数；模型 judge 零使用）。

纪律：summary 的每个数字都从 raw 记录程序化复算（``--summarize-only`` 可重
算可复现）；判据全部确定性规则，无模型评分。指标口径冻结在
``METRICS_RULES_VERSION``，改动需 bump 并在 REPORT 声明。
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from tests.aurora_ablation.persona import ABLATION_SPEC_VERSION

__all__ = ["METRICS_RULES_VERSION", "UTILITY_WEIGHTS", "summarize_arm", "compare_arms", "render_markdown", "extract_counterexamples"]

METRICS_RULES_VERSION = "aurora_ablation_metrics.v1"

#: 效用权重（冻结；REPORT §口径。单位：每 resolved 段 +1、每 unresolved 段
#: −1、每次被跟随的错位决策 −0.4、每个问句 −0.15、每次对照侵入 −0.6）。
UTILITY_WEIGHTS = {
    "resolved_episode": 1.0,
    "unresolved_episode": -1.0,
    "wrong_followed_decision": -0.4,
    "question": -0.15,
    "control_intrusion": -0.6,
}

_MATCH_SCORE = {"primary": 1.0, "secondary": 0.5, "wrong": 0.0}


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _records_by_kind(records: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [r for r in records if r.get("kind") == kind]


def summarize_arm(records: list[dict[str, Any]], *, arm: str) -> dict[str, Any]:
    """一个臂的完整 summary（全部由 raw 程序化复算）。"""
    stuck = _records_by_kind(records, "stuck")
    controls = _records_by_kind(records, "control")
    ends = _records_by_kind(records, "episode_end")
    fails = [r for r in records if r.get("kind") == "episode_fail"]

    # -- stuck accuracy / 收敛速度 -------------------------------------------
    episodes_resolved = [e for e in ends if e.get("resolved")]
    episodes_failed = list(fails)
    episodes_total = len(episodes_resolved) + len(episodes_failed)
    sessions_used = [int(e["sessions_used"]) for e in episodes_resolved]

    # -- allocation（分派与 persona 需求匹配规则分）--------------------------
    used_scores = [_MATCH_SCORE.get(str(r.get("match_class")), 0.0) for r in stuck]

    def _surface_score(r: dict[str, Any], surface: str) -> float | None:
        truth = r.get("truth")
        if surface == "journey":
            j = r.get("journey") or {}
            main = j.get("main_intervention")
            iv = main.get("type") if main else None
        else:
            selected = str(((r.get("chat") or {}).get("intervention") or {}).get("selected") or "")
            iv = selected or None if selected not in ("", "no_action", "abstain") else None
        if iv is None:
            return None  # 该面本轮未出行动决策（不计入该面均值）
        from tests.aurora_ablation.persona import match_class

        return _MATCH_SCORE[match_class(iv, str(truth))]

    journey_scores = [s for s in (_surface_score(r, "journey") for r in stuck) if s is not None]
    chat_scores = [s for s in (_surface_score(r, "chat") for r in stuck) if s is not None]
    followed_wrong = sum(1 for r in stuck if r.get("match_class") == "wrong" and r.get("decision_used"))

    # -- overpersonalization（对照侵入 + 不确定行动）-------------------------
    intrusions = [r for r in controls if r.get("control_intrusion")]
    uncertain_acts = [r for r in stuck if r.get("used_uncertain") is True]

    # -- clarification --------------------------------------------------------
    questions = sum(int(r.get("questions_this_session") or 0) for r in stuck)
    asked_sessions = [r for r in stuck if (r.get("questions_this_session") or 0) > 0]
    asked_good = [r for r in asked_sessions if r.get("match_class") in ("primary", "secondary")]

    # -- cost ----------------------------------------------------------------
    counters: dict[str, int] = defaultdict(int)
    for r in stuck + controls:
        chat = r.get("chat") or {}
        if isinstance(chat, dict) and chat:
            counters["chat_turns"] += 2 if chat.get("answer_branch") else 1
        if r.get("journey"):
            counters["journey_starts"] += 1 + (1 if (r.get("journey") or {}).get("answer_branch") is not None else 0)
    engine_calls = len(stuck) * 2 + len(controls)  # stuck: chat+journey 两面；control: chat
    fixed_arm = arm == "fixed_policy"
    if fixed_arm:
        engine_calls = 0
    sessions_consumed = len(stuck)
    cost_per_resolved = (
        round(sessions_consumed / len(episodes_resolved), 4) if episodes_resolved else None
    )

    # -- utility（冻结权重）---------------------------------------------------
    utility = (
        UTILITY_WEIGHTS["resolved_episode"] * len(episodes_resolved)
        + UTILITY_WEIGHTS["unresolved_episode"] * len(episodes_failed)
        + UTILITY_WEIGHTS["wrong_followed_decision"] * followed_wrong
        + UTILITY_WEIGHTS["question"] * questions
        + UTILITY_WEIGHTS["control_intrusion"] * len(intrusions)
    )

    # -- per-persona breakdown ----------------------------------------------
    per_persona: dict[str, dict[str, Any]] = {}
    for persona_id in sorted({str(r.get("persona")) for r in records}):
        p_stuck = [r for r in stuck if r.get("persona") == persona_id]
        p_resolved = [e for e in episodes_resolved if e.get("persona") == persona_id]
        p_failed = [e for e in episodes_failed if e.get("persona") == persona_id]
        p_ctrl = [r for r in controls if r.get("persona") == persona_id]
        per_persona[persona_id] = {
            "episodes": len(p_resolved) + len(p_failed),
            "resolved": len(p_resolved),
            "stuck_accuracy": (
                round(len(p_resolved) / (len(p_resolved) + len(p_failed)), 4)
                if (p_resolved or p_failed)
                else None
            ),
            "questions": sum(int(r.get("questions_this_session") or 0) for r in p_stuck),
            "control_intrusions": sum(1 for r in p_ctrl if r.get("control_intrusion")),
        }

    # -- patch 面（经验回路的可见动作）---------------------------------------
    patch_reordered_turns = sum(
        1
        for r in stuck + controls
        if ((r.get("chat") or {}).get("patch_moves"))
    )
    patch_active_ids = {
        pid
        for r in stuck
        for pid in ((r.get("chat") or {}).get("applied_patch_ids") or [])
    }

    # -- invariants（评估红条件）---------------------------------------------
    invariants = {
        "fixed_arm_zero_engine_calls": (engine_calls == 0) if fixed_arm else None,
        "budget_respected": all(a <= 3 for a in sessions_used) and all(int(e.get("attempts") or 0) <= 3 for e in episodes_failed),
        "resolution_requires_match": all(
            e.get("resolving_match_class") in ("primary", "secondary") for e in episodes_resolved
        ),
    }
    if arm == "no_memory":
        invariants["no_memory_zero_corrections"] = all(not (r.get("correction")) for r in stuck)
    if arm == "no_experience":
        invariants["no_experience_zero_patches"] = all(
            not (r.get("patch_admission")) for r in stuck
        )
        invariants["no_experience_zero_spine"] = all(
            not ((r.get("chat") or {}).get("spine_keys_at_turn")) for r in stuck + controls if r.get("chat")
        )

    return {
        "arm": arm,
        "spec_version": ABLATION_SPEC_VERSION,
        "metrics_rules_version": METRICS_RULES_VERSION,
        "records_total": len(records),
        "stuck_sessions": len(stuck),
        "control_sessions": len(controls),
        "episodes_total": episodes_total,
        "episodes_resolved": len(episodes_resolved),
        "episodes_failed": len(episodes_failed),
        "stuck_accuracy": (
            round(len(episodes_resolved) / episodes_total, 4) if episodes_total else None
        ),
        "sessions_to_resolution_mean": _mean([float(s) for s in sessions_used]),
        "sessions_to_resolution_max": max(sessions_used) if sessions_used else None,
        "allocation_match_followed_mean": _mean(used_scores),
        "allocation_match_journey_surface_mean": _mean(journey_scores),
        "allocation_match_chat_surface_mean": _mean(chat_scores),
        "followed_wrong_decisions": followed_wrong,
        "control_intrusions": len(intrusions),
        "control_intrusion_rate": (
            round(len(intrusions) / len(controls), 4) if controls else None
        ),
        "uncertain_acts": len(uncertain_acts),
        "questions_total": questions,
        "questions_per_episode": (
            round(questions / episodes_total, 4) if episodes_total else None
        ),
        "ask_precision": round(len(asked_good) / len(asked_sessions), 4) if asked_sessions else None,
        "cost": {
            "engine_call_sessions": engine_calls,
            "chat_turns": counters["chat_turns"],
            "journey_starts": counters["journey_starts"],
            "questions": questions,
            "sessions_consumed": sessions_consumed,
            "sessions_per_resolved_episode": cost_per_resolved,
        },
        "utility": round(utility, 4),
        "experience": {
            "patch_reordered_turns": patch_reordered_turns,
            "patch_ids_seen": len(patch_active_ids),
        },
        "per_persona": per_persona,
        "invariants": invariants,
    }


def compare_arms(summaries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """四臂对照表（Δ 相对 full；方向语义由消费方判读）。"""
    rows = []
    full = summaries.get("full") or {}
    for key, label in (
        ("stuck_accuracy", "stuck accuracy（预算内收敛率）"),
        ("sessions_to_resolution_mean", "收敛会话数均值"),
        ("allocation_match_followed_mean", "被跟随决策匹配分"),
        ("allocation_match_journey_surface_mean", "旅程面匹配分"),
        ("allocation_match_chat_surface_mean", "chat 面匹配分"),
        ("control_intrusion_rate", "对照侵入率"),
        ("questions_per_episode", "每段问句数"),
        ("ask_precision", "问后收敛命中率"),
        ("uncertain_acts", "不确定行动数"),
        ("utility", "效用（冻结权重）"),
        ("sessions_per_resolved_episode", "每解决段会话成本"),
    ):
        row: dict[str, Any] = {"metric": label, "key": key}
        for arm in ("full", "no_memory", "no_experience", "fixed_policy"):
            row[arm] = (summaries.get(arm) or {}).get(key)
        fv = full.get(key)
        fixed_v = (summaries.get("fixed_policy") or {}).get(key)
        fv_num = fv if isinstance(fv, (int, float)) and not isinstance(fv, bool) else None
        fixed_num = fixed_v if isinstance(fixed_v, (int, float)) and not isinstance(fixed_v, bool) else None
        row["delta_vs_full_fixed"] = (
            round(fixed_num - fv_num, 4) if fv_num is not None and fixed_num is not None else None
        )
        rows.append(row)
    return rows


def extract_counterexamples(records: list[dict[str, Any]]) -> dict[str, Any]:
    """反例提取（保留不剪；逐条可引用到 raw 行）。"""
    counterexamples: dict[str, Any] = {
        "b1_tie_acts": [],
        "correction_cycles": [],
        "control_intrusions": [],
        "chat_structural_no_action": [],
        "budget_failures": [],
    }
    stuck_by_episode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in _records_by_kind(records, "stuck"):
        stuck_by_episode[str(r.get("episode_id"))].append(r)

    for r in _records_by_kind(records, "control"):
        if r.get("control_intrusion"):
            counterexamples["control_intrusions"].append(
                {
                    "persona": r.get("persona"),
                    "day": r.get("sim_day"),
                    "utterance": r.get("utterance") if "utterance" in r else None,
                    "mode": (r.get("chat") or {}).get("mode"),
                    "question": bool((r.get("chat") or {}).get("question")),
                    "selected": ((r.get("chat") or {}).get("intervention") or {}).get("selected"),
                    "spine_keys": (r.get("chat") or {}).get("spine_keys_at_turn"),
                }
            )

    for r in _records_by_kind(records, "stuck"):
        j = r.get("journey") or {}
        chat = r.get("chat") or {}
        if j.get("uncertain") and j.get("main_intervention"):
            counterexamples["b1_tie_acts"].append(
                {
                    "persona": r.get("persona"),
                    "day": r.get("sim_day"),
                    "truth": r.get("truth"),
                    "journey_type": j.get("friction_type"),
                    "intervention": (j.get("main_intervention") or {}).get("type"),
                    "utterance": r.get("utterance"),
                }
            )
        if chat.get("outcome") == "act" and chat.get("friction_type") not in (None, "unknown"):
            selected = str(((chat.get("intervention") or {}).get("selected")) or "")
            if not selected or selected in ("no_action", "abstain"):
                counterexamples["chat_structural_no_action"].append(
                    {
                        "persona": r.get("persona"),
                        "day": r.get("sim_day"),
                        "truth": r.get("truth"),
                        "diagnosed": chat.get("friction_type"),
                        "note": "诊断命中但 A-02 守卫结构性排除（chat 能力/权限面）",
                    }
                )
    for episode_id, rows in stuck_by_episode.items():
        corrections = [r for r in rows if r.get("correction")]
        if len(corrections) >= 2:
            counterexamples["correction_cycles"].append(
                {
                    "episode_id": episode_id,
                    "truth": rows[0].get("truth"),
                    "walk": [
                        {
                            "day": r.get("sim_day"),
                            "journey_type": (r.get("journey") or {}).get("friction_type"),
                            "corrected": ((r.get("correction") or {}).get("corrected_friction_type")),
                        }
                        for r in corrections
                    ],
                }
            )
    for r in records:
        if r.get("kind") == "episode_fail":
            counterexamples["budget_failures"].append(
                {
                    "episode_id": r.get("episode_id"),
                    "truth": r.get("truth"),
                    "attempts": r.get("attempts"),
                    "decisions": r.get("decisions"),
                }
            )
    return counterexamples


def render_markdown(summaries: dict[str, dict[str, Any]], comparisons: list[dict[str, Any]]) -> str:
    """EVAL_RESULTS.md 渲染（数字全部来自 summaries，无手填）。"""
    lines = [
        "# WT393 · A-08 Aurora 纵向/消融评估 — 结果（程序化生成）",
        "",
        f"- spec `{ABLATION_SPEC_VERSION}` · metrics `{METRICS_RULES_VERSION}` · 效用权重 `{UTILITY_WEIGHTS}`",
        "",
        "## 四臂对照",
        "",
        "| 指标 | full | no_memory | no_experience | fixed_policy | Δ(fixed−full) |",
        "|---|---|---|---|---|---|",
    ]
    for row in comparisons:
        lines.append(
            "| {} | {} | {} | {} | {} | {} |".format(
                row["metric"],
                row["full"],
                row["no_memory"],
                row["no_experience"],
                row["fixed_policy"],
                row["delta_vs_full_fixed"],
            )
        )
    lines += ["", "## 各臂明细", ""]
    for arm in ("full", "no_memory", "no_experience", "fixed_policy"):
        s = summaries[arm]
        lines.append(f"### {arm}")
        lines.append("")
        lines.append(
            f"- episodes {s['episodes_total']}（resolved {s['episodes_resolved']} / failed {s['episodes_failed']}），"
            f"stuck accuracy **{s['stuck_accuracy']}**，收敛会话均值 {s['sessions_to_resolution_mean']}"
        )
        lines.append(
            f"- allocation：followed {s['allocation_match_followed_mean']} · journey 面 {s['allocation_match_journey_surface_mean']} · chat 面 {s['allocation_match_chat_surface_mean']}"
        )
        lines.append(
            f"- overpersonalization：对照侵入 {s['control_intrusions']}/{s['control_sessions']}（rate {s['control_intrusion_rate']}），uncertain 行动 {s['uncertain_acts']}"
        )
        lines.append(
            f"- clarification：问句 {s['questions_total']}（每段 {s['questions_per_episode']}），ask_precision {s['ask_precision']}"
        )
        lines.append(f"- cost：{json.dumps(s['cost'], ensure_ascii=False)}")
        lines.append(f"- utility：**{s['utility']}**")
        lines.append(f"- invariants：{json.dumps(s['invariants'], ensure_ascii=False)}")
        lines.append("")
        lines.append("  persona 明细：")
        lines.append("")
        lines.append("  | persona | episodes | resolved | accuracy | questions | intrusions |")
        lines.append("  |---|---|---|---|---|---|")
        for pid, p in s["per_persona"].items():
            lines.append(
                f"  | {pid} | {p['episodes']} | {p['resolved']} | {p['stuck_accuracy']} | {p['questions']} | {p['control_intrusions']} |"
            )
        lines.append("")
    content = "\n".join(lines) + "\n"
    digest = hashlib.sha256(content.encode()).hexdigest()[:16]
    return content + f"\n（内容摘要 sha256[:16] = {digest}）\n"
