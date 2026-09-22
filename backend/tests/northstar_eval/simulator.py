"""NORTHSTAR · 三臂旅程确定性参考模拟（contract-simulation surrogate）。

诚实边界（先读这段再读结果）：

- 本模块是**纯函数参考实现**：把 SCENARIO.md 的旅程契约编码为可执行推演，用于
  ①钉住每个 checkpoint 的判定路径、②给 C 线真实闭环测试提供同一套观测/metrics 面。
  它**不是**后端生产代码，推演结果**不构成学习增益证据**。
- ``ARM_PRIORS`` 是**假设先验**（hypothesis priors）：臂间差异的方向由 EVAL_FRAMEWORK
  的结构性论证给出，数值仅用于打通测量管线与冒烟；真实数值只能来自对照协议实测。
- 真实 LLM 0 次；真实墙钟/真人自报判据（CP-98/CP-99）由 grading 判 unsupported。
- 随机性只来自显式 seed 派生的 ``random.Random``，同 seed 逐字节一致。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from .journey_schema import ARM_CONTROL_DSK, ARM_CONTROL_GPT, ARM_SPARKLE, Journey

# ---------------------------------------------------------------------------
# 臂效应假设先验（hypothesis priors — 仅用于管线冒烟，非增益证据）
# ---------------------------------------------------------------------------

#: targeting: weighted=按 exam_weight×(1−mastery) 定向（星图驱动）；round_robin=无考纲账本轮换。
#: effective_fraction: 有效学习时间占比（无结构 → 组织/检索开销吃掉更多墙钟）。
#: retention_per_day: 未复习内容的每日保持率（无间隔复习调度 → 衰减更快）。
#: review: 是否有遗忘曲线调度复习（裸 Chatbot 无此结构）。
#: adaptive: 次日计划是否依据前日结果重算（计划闭环）。
#: memory_pollution_events: 记忆污染事件（M-02..M-07 守卫面；结构上 Sparkle 臂应为 0）。
ARM_PRIORS: dict[str, dict[str, Any]] = {
    ARM_SPARKLE: {
        "targeting": "weighted",
        "k_nodes_per_day": 3,
        "effective_fraction": 0.90,
        "gain_per_node_hour": 0.35,
        "retention_per_day": 0.995,
        "review": True,
        "adaptive": True,
        "memory_pollution_events": 0,
    },
    ARM_CONTROL_GPT: {
        "targeting": "round_robin",
        "k_nodes_per_day": 24,
        "effective_fraction": 0.60,
        "gain_per_node_hour": 0.35,
        "retention_per_day": 0.985,
        "review": False,
        "adaptive": False,
        "memory_pollution_events": 0,
    },
    ARM_CONTROL_DSK: {
        "targeting": "round_robin",
        "k_nodes_per_day": 24,
        "effective_fraction": 0.58,
        "gain_per_node_hour": 0.35,
        "retention_per_day": 0.986,
        "review": False,
        "adaptive": False,
        "memory_pollution_events": 0,
    },
}

#: 判定/噪声参数（与 grading 阈值联动；冻结于此避免两处漂移）。
QUIZ_NOISE_SIGMA = 1.2
POSTTEST_NOISE_SIGMA = 1.0
QUIZ_PASSED_LINE = 0.60  # 节点「通过」线（coverage passed 判定）
REVIEW_RESTORE_MIN = 0.02  # 复习命中后恢复量下限


@dataclass
class JourneyRun:
    """一次旅程推演的结构化观测（checker 只读 observations；metrics 由 metrics 层派生）。"""

    observations: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)


def _plan_targets(nodes: list[dict[str, Any]], mastery: dict[str, float], prior: dict[str, Any], day: int) -> list[str]:
    """当日计划节点选择：weighted 定向 vs round_robin（无账本匀速推进）。"""
    if prior["targeting"] == "weighted":
        ranked = sorted(nodes, key=lambda node: node["exam_weight"] * (1.0 - mastery[node["node_id"]]), reverse=True)
        return [node["node_id"] for node in ranked[: prior["k_nodes_per_day"]]]
    # round_robin：按固定顺序每天推进固定个数的未过线节点（无考纲权重概念）。
    ordered = [node["node_id"] for node in nodes]
    start = (day * prior["k_nodes_per_day"]) % len(ordered)
    rotated = ordered[start:] + ordered[:start]
    return rotated[: prior["k_nodes_per_day"]]


def simulate_journey(journey: Journey, arm: str, seed: int) -> JourneyRun:
    """按 SCENARIO Day0..DayN(+3 天重测) 推演一条旅程（同 seed 逐字节一致）。"""
    prior = ARM_PRIORS[arm]
    rng = random.Random(seed)
    nodes = [
        {
            "node_id": node.node_id,
            "exam_weight": node.exam_weight,
            "difficulty": node.difficulty,
            "trainability": node.trainability,
        }
        for node in journey.nodes
    ]
    node_ids = [node["node_id"] for node in nodes]
    base_mastery = journey.pretest_score / 100.0
    mastery: dict[str, float] = {node_id: base_mastery + rng.uniform(-0.02, 0.02) for node_id in node_ids}
    weight_of = {node["node_id"]: node["exam_weight"] for node in nodes}

    total_minutes = journey.horizon_days * journey.daily_minutes
    study_days = journey.horizon_days - 1  # Day0 诊断 + DayN 模拟考，中间为学习日
    study_minutes_per_day = journey.daily_minutes * prior["effective_fraction"]

    days: list[dict[str, Any]] = []
    quiz_scores: list[float] = []
    error_book: list[dict[str, Any]] = []
    mistake_synced = 0
    review_hits = 0
    review_total = 0
    adaptive_change_days = 0
    studied_ever: set[str] = set()
    previous_plan: list[str] | None = None
    stale_memory_surfaces = prior["memory_pollution_events"]

    # Day0：摸底入账 + 考纲→星图映射 + 计划草案确认。
    days.append({"day": 0, "phase": "diagnose", "plan_targets": _plan_targets(nodes, mastery, prior, 0)})
    plan_confirmed = True  # SCENARIO 0.4：草案→用户改 1 处→确认（两臂同流程）

    for day in range(1, study_days + 1):
        plan = _plan_targets(nodes, mastery, prior, day)
        if previous_plan is not None and prior["adaptive"] and plan != previous_plan:
            adaptive_change_days += 1
        previous_plan = plan

        # 学习段：定向节点按节点小时数增益（trainability 调制；difficulty 是 spec 形状字段，
        # 骨架推演不消费——C 线接入真实自适应难度分层时再进入模型）。
        hours_per_node = (study_minutes_per_day / 60.0) / max(len(plan), 1)
        for node_id in plan:
            node = next(item for item in nodes if item["node_id"] == node_id)
            gain = prior["gain_per_node_hour"] * hours_per_node * node["trainability"]
            mastery[node_id] = min(1.0, mastery[node_id] + gain)
            studied_ever.add(node_id)

        # 自测段：考纲比例抽样 5 题的标准化形成性测验（确定性判卷 + 判卷噪声）。
        sampled = rng.sample(node_ids, k=min(5, len(node_ids)))
        quiz = sum(mastery[node_id] for node_id in sampled) / len(sampled) * 100.0 + rng.gauss(0.0, QUIZ_NOISE_SIGMA)
        quiz = round(quiz, 2)
        quiz_scores.append(quiz)

        # 错题沉淀：抽样中未过线节点落错题本；Sparkle 臂触发 mastery 同步（error_book_mastery_sync）。
        missed = [node_id for node_id in sampled if mastery[node_id] < QUIZ_PASSED_LINE]
        for node_id in missed:
            error_book.append({"day": day, "node_id": node_id})
            if arm == ARM_SPARKLE:
                mistake_synced += 1  # 同步面守卫下 100% 落账

        # 复习段：到期重测（昨日+更早错题/过期节点）首答判定。
        if prior["review"]:
            due = sorted(studied_ever - set(plan))
            for node_id in due:
                review_total += 1
                if mastery[node_id] >= QUIZ_PASSED_LINE:
                    review_hits += 1
                    mastery[node_id] = min(1.0, mastery[node_id] + REVIEW_RESTORE_MIN)

        # 遗忘：未复习内容按臂保持率衰减。
        for node_id in node_ids:
            mastery[node_id] *= prior["retention_per_day"]

        days.append({"day": day, "phase": "study", "plan_targets": plan, "quiz": quiz, "missed": missed})

    # DayN：全真模拟考（卷 B，考纲全覆盖）。
    posttest = sum(weight_of[node_id] * mastery[node_id] for node_id in node_ids) * 100.0
    posttest = round(posttest + rng.gauss(0.0, POSTTEST_NOISE_SIGMA), 2)

    # +3 天重测（卷 A′ 等价）：无复习维持下的衰减。
    decayed = {node_id: mastery[node_id] * (ARM_PRIORS[arm]["retention_per_day"] ** 3) for node_id in node_ids}
    retest = round(sum(weight_of[node_id] * decayed[node_id] for node_id in node_ids) * 100.0, 2)

    # 加权覆盖率：covered=出现过在计划卡 ∧ passed=末态 mastery 过线。
    covered = [node_id for node_id in node_ids if node_id in studied_ever]
    passed = [node_id for node_id in covered if mastery[node_id] >= QUIZ_PASSED_LINE]
    total_weight = sum(weight_of[node_id] for node_id in node_ids)
    weighted_coverage = sum(weight_of[node_id] for node_id in passed) / total_weight

    # 星图校准：末态 mastery 与「模拟考逐节点得分率」（这里以 mastery 自身+噪声代理真卷）。
    calibration_probe = {node_id: max(0.0, mastery[node_id] + rng.gauss(0.0, 0.05)) for node_id in node_ids}
    calibration_error = sum(abs(mastery[node_id] - calibration_probe[node_id]) for node_id in node_ids) / len(node_ids)

    observations: dict[str, Any] = {
        "arm": arm,
        "pretest_score": journey.pretest_score,
        "baseline_recorded": True,  # Day0 摸底入账（两臂同流程）
        "node_map_count": len(node_ids),
        "node_total": len(node_ids),
        "plan_targets_weighted": prior["targeting"] == "weighted",
        "plan_human_confirmed": plan_confirmed,
        "quiz_scores": quiz_scores,
        "error_book_entries": len(error_book),
        "mistake_synced": mistake_synced,
        "review_hits": review_hits,
        "review_total": review_total,
        "adaptive_change_days": adaptive_change_days,
        "study_days": study_days,
        "covered_count": len(covered),
        "passed_count": len(passed),
        "node_total_weight": total_weight,
        "weighted_coverage": weighted_coverage,
        "posttest_score": posttest,
        "retest_score": retest,
        "total_minutes": total_minutes,
        "study_minutes": study_days * study_minutes_per_day,
        "stale_memory_surfaces": stale_memory_surfaces,
        "mastery_calibration_error": calibration_error,
        "days": days,
    }
    return JourneyRun(observations=observations)
