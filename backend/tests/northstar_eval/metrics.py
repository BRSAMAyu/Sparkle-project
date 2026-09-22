"""NORTHSTAR · 学习效果代理指标计算（EVAL_FRAMEWORK.md §M1–M9 的机检实现）。

纯函数：JourneyRun.observations → metrics dict。所有比率四舍五入到 4 位。
除零语义：分母为 0 时该指标诚实取 0.0（评分层负责判 fail/unsupported，不在此掩盖）。
"""

from __future__ import annotations

from typing import Any


def _ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def moving_average(values: list[float], window: int) -> list[float]:
    """3 日滑动平均（CP-02 判定用；窗口不足时用现有全部值）。"""
    result: list[float] = []
    for index in range(len(values)):
        lo = max(0, index - window + 1)
        chunk = values[lo : index + 1]
        result.append(sum(chunk) / len(chunk))
    return result


def compute_journey_metrics(obs: dict[str, Any]) -> dict[str, float]:
    """单旅程单臂观测 → 冻结指标面（键集与 EVAL_FRAMEWORK §1 对齐）。"""
    pre = float(obs["pretest_score"])
    post = float(obs["posttest_score"])
    retest = float(obs["retest_score"])
    hours = float(obs["total_minutes"]) / 60.0
    gain = round(post - pre, 2)
    return {
        "pretest_score": round(pre, 2),
        "posttest_score": post,
        "retest_score": retest,
        "gain": gain,
        "gain_per_hour": round(gain / hours, 4) if hours > 0 else 0.0,
        "forgetting_rate": _ratio(max(post - retest, 0.0), post),
        "weighted_coverage": round(float(obs["weighted_coverage"]), 4),
        "review_hit_rate": _ratio(float(obs["review_hits"]), float(obs["review_total"])),
        "mistake_sync_ratio": _ratio(float(obs["mistake_synced"]), float(obs["error_book_entries"])),
        "adaptive_day_ratio": _ratio(float(obs["adaptive_change_days"]), float(obs["study_days"])),
        "quiz_ma_first": (
            round(moving_average([float(v) for v in obs["quiz_scores"]], 3)[0], 2) if obs["quiz_scores"] else 0.0
        ),
        "quiz_ma_last": (
            round(moving_average([float(v) for v in obs["quiz_scores"]], 3)[-1], 2) if obs["quiz_scores"] else 0.0
        ),
        "mastery_calibration_error": round(float(obs["mastery_calibration_error"]), 4),
        "stale_memory_surfaces": float(obs["stale_memory_surfaces"]),
        "covered_nodes": float(obs["covered_count"]),
        "total_hours": round(hours, 2),
    }
