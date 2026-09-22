"""NORTHSTAR · checkpoint 逐项 checker 注册表与诚实判定聚合。

判定规则（与 Q-01 ``tests/v3_scenario_eval/grading.py`` 同构，复用其硬线）：

1. 每个 journey 的 expected 列表逐项查 ``CHECKPOINT_CHECKERS[checkpoint_text]``；
2. 真实世界判据（CP-98 真人量表 / CP-99 真墙钟）→ 该项 ``unsupported``（固定 reason）；
3. attempt verdict：任一项 unsupported ⇒ unsupported；否则任一 fail ⇒ fail；否则 pass；
4. **unsupported 永不计 PASS**——API 级推演永远不足以宣称北极星达成（能跑≠有用），
   需要的正是 C 线真实闭环测试补上 CP-98/CP-99。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_UNSUPPORTED = "unsupported"
VERDICTS = (VERDICT_PASS, VERDICT_FAIL, VERDICT_UNSUPPORTED)

ITEM_PASS = "pass"
ITEM_FAIL = "fail"
ITEM_UNSUPPORTED = "unsupported"

REASON_NO_CHECKER = "no_deterministic_checker"
REASON_REQUIRES_HUMAN_SELF_REPORT = "requires_real_human_self_report"
REASON_REQUIRES_REAL_WALL_CLOCK = "requires_real_exam_wall_clock"

#: 阈值与 EVAL_FRAMEWORK §1 / SCENARIO §3 冻结值一致。
GAIN_MDE = 15.0  # M1：ΔS ≥ +15（MDE 定标假设）
FORGETTING_MAX = 0.2  # M3：F ≤ 0.2
COVERAGE_MIN = 0.8  # M4：加权覆盖 ≥ 0.8
REVIEW_HIT_MIN = 0.7  # M5：复习命中 ≥ 0.7
ADAPT_DAY_MIN = round(5 / 6, 4)  # CP-04：6 个学习日中 ≥5 次真实自适应（与 metrics 同为 4 位舍入）
QUIZ_MA_WINDOW = 3
QUIZ_MA_TOLERANCE = 0.5  # 3 日滑动平均非降容差（判卷噪声裕度）


@dataclass
class ItemResult:
    """单个 checkpoint 的判定。"""

    text: str
    status: str
    detail: str

    def to_payload(self) -> dict[str, Any]:
        return {"text": self.text, "status": self.status, "detail": self.detail}


@dataclass
class AttemptResult:
    """单次 repeat 的判定（含指标）。"""

    attempt: int
    seed: int
    verdict: str
    items: list[ItemResult] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "seed": self.seed,
            "verdict": self.verdict,
            "items": [item.to_payload() for item in self.items],
            "metrics": dict(self.metrics),
        }


#: checker 签名：(obs, metrics) -> (status, detail)
CheckpointChecker = Callable[[dict[str, Any], dict[str, float]], tuple[str, str]]

_CHECKPOINT_OK = (ITEM_PASS, "")
_CHECKPOINT_FAIL = (ITEM_FAIL, "")


def _simple(condition: bool, fail_detail: str) -> tuple[str, str]:
    return _CHECKPOINT_OK if condition else (ITEM_FAIL, fail_detail)


def _cp00_baseline_and_mapping(obs: dict[str, Any], metrics: dict[str, float]) -> tuple[str, str]:
    del metrics
    if not obs["baseline_recorded"]:
        return ITEM_FAIL, "pretest baseline not recorded"
    return _simple(obs["node_map_count"] == obs["node_total"], "syllabus-to-node mapping incomplete")


def _cp01_targeted_plan_confirmed(obs: dict[str, Any], metrics: dict[str, float]) -> tuple[str, str]:
    del metrics
    if not obs["plan_targets_weighted"]:
        return ITEM_FAIL, "plan not targeted by exam_weight x weakness (no syllabus ledger)"
    return _simple(bool(obs["plan_human_confirmed"]), "plan draft not human-confirmed before execution")


def _cp02_quiz_trajectory(obs: dict[str, Any], metrics: dict[str, float]) -> tuple[str, str]:
    first, last = metrics["quiz_ma_first"], metrics["quiz_ma_last"]
    if not obs["quiz_scores"]:
        return ITEM_FAIL, "no quiz samples"
    return _simple(last >= first - QUIZ_MA_TOLERANCE, f"quiz 3-day MA regressed: {first} -> {last}")


def _cp03_mistake_sync(obs: dict[str, Any], metrics: dict[str, float]) -> tuple[str, str]:
    if obs["error_book_entries"] == 0:
        return ITEM_FAIL, "no mistakes landed in error book (no mistake sink)"
    ratio = metrics["mistake_sync_ratio"]
    return _simple(ratio >= 1.0, f"mistake-to-mastery sync ratio {ratio} < 1.0")


def _cp04_adaptive_plan(obs: dict[str, Any], metrics: dict[str, float]) -> tuple[str, str]:
    ratio = metrics["adaptive_day_ratio"]
    return _simple(ratio >= ADAPT_DAY_MIN, f"adaptive plan days ratio {ratio} < {round(ADAPT_DAY_MIN, 4)}")


def _cp05_review_hit(obs: dict[str, Any], metrics: dict[str, float]) -> tuple[str, str]:
    if obs["review_total"] == 0:
        return ITEM_FAIL, "no scheduled review events (no spaced-repetition structure)"
    rate = metrics["review_hit_rate"]
    return _simple(rate >= REVIEW_HIT_MIN, f"review hit rate {rate} < {REVIEW_HIT_MIN}")


def _cp06_coverage(obs: dict[str, Any], metrics: dict[str, float]) -> tuple[str, str]:
    coverage = metrics["weighted_coverage"]
    return _simple(coverage >= COVERAGE_MIN, f"weighted coverage {coverage} < {COVERAGE_MIN}")


def _cp07_gain(obs: dict[str, Any], metrics: dict[str, float]) -> tuple[str, str]:
    del obs
    gain = metrics["gain"]
    return _simple(gain >= GAIN_MDE, f"posttest gain {gain} < MDE {GAIN_MDE}")


def _cp08_forgetting(obs: dict[str, Any], metrics: dict[str, float]) -> tuple[str, str]:
    del obs
    rate = metrics["forgetting_rate"]
    return _simple(rate <= FORGETTING_MAX, f"forgetting rate {rate} > {FORGETTING_MAX}")


# ---------------------------------------------------------------------------
# 冻结注册表：checkpoint_text -> (checker | None, unsupported_reason | None)
# checker 为 None ⇒ 该判据 API 级推演不可判，按 reason 诚实 unsupported。
# ---------------------------------------------------------------------------

CHECKPOINT_CHECKERS: dict[str, tuple[CheckpointChecker | None, str | None]] = {
    "CP-00 baseline recorded and syllabus mapped": (_cp00_baseline_and_mapping, None),
    "CP-01 plan targets weakest exam-weighted nodes with human confirmation": (_cp01_targeted_plan_confirmed, None),
    "CP-02 quiz score trajectory non-decreasing": (_cp02_quiz_trajectory, None),
    "CP-03 mistakes fully land in error book with mastery sync": (_cp03_mistake_sync, None),
    "CP-04 next-day plan adapts to previous outcome": (_cp04_adaptive_plan, None),
    "CP-05 review hit rate at or above threshold": (_cp05_review_hit, None),
    "CP-06 weighted coverage at or above threshold by last study day": (_cp06_coverage, None),
    "CP-07 posttest gain at or above MDE": (_cp07_gain, None),
    "CP-08 forgetting rate at or below threshold": (_cp08_forgetting, None),
    "CP-98 daily cognitive load self-report": (None, REASON_REQUIRES_HUMAN_SELF_REPORT),
    "CP-99 full mock exam wall clock at or below budget": (None, REASON_REQUIRES_REAL_WALL_CLOCK),
}


def grade_attempt(expected: tuple[str, ...], obs: dict[str, Any], metrics: dict[str, float]) -> list[ItemResult]:
    """expected 逐项判定：注册表命中 → checker/reason；未命中 → no_deterministic_checker。"""
    items: list[ItemResult] = []
    for text in expected:
        checker, unsupported_reason = CHECKPOINT_CHECKERS.get(text, (None, None))
        if checker is None:
            items.append(ItemResult(text=text, status=ITEM_UNSUPPORTED, detail=unsupported_reason or REASON_NO_CHECKER))
            continue
        status, detail = checker(obs, metrics)
        items.append(ItemResult(text=text, status=status, detail=detail))
    return items


def attempt_verdict(items: list[ItemResult]) -> str:
    """attempt 级判定：unsupported 优先 → fail → pass（unsupported 永不折算 pass）。"""
    statuses = {item.status for item in items}
    if ITEM_UNSUPPORTED in statuses:
        return VERDICT_UNSUPPORTED
    if ITEM_FAIL in statuses:
        return VERDICT_FAIL
    return VERDICT_PASS


def case_verdict(attempts: list[AttemptResult]) -> str:
    """case 级判定：任一 attempt unsupported ⇒ unsupported；否则任一 fail ⇒ fail。"""
    verdicts = {attempt.verdict for attempt in attempts}
    if VERDICT_UNSUPPORTED in verdicts:
        return VERDICT_UNSUPPORTED
    if VERDICT_FAIL in verdicts:
        return VERDICT_FAIL
    return VERDICT_PASS


def unsupported_must_not_pass(case_payload: dict[str, Any]) -> bool:
    """acceptance 硬线的机检实现：unsupported case 决不允许被判成/计成 pass。"""
    if case_payload["verdict"] == VERDICT_PASS:
        return all(
            item["status"] != ITEM_UNSUPPORTED for attempt in case_payload["attempts"] for item in attempt["items"]
        )
    return True
