"""
Aurora proactive pipeline — auditable decision metrics (P-01/P-02).

每个事件决定（notify / suppressed / no_action / ignored）按
``trigger × event_name × decision × reason`` 落 Prometheus 计数——shadow
模式的"可审"验收就靠它：任何抑制/不打扰决定都能按原因聚合回放。
label 取值有界（trigger 7 种 / event_name 白名单 9 种 / decision 4 种 /
reason：P-01 抑制 7 种 + ignored 1 种 + none + P-02 相关性封闭五值
RELEVANCE_REASONS），无用户维度，无基数风险。
"""

from __future__ import annotations

from prometheus_client import Counter

from app.core.metrics import get_or_create_metric

__all__ = [
    "PROACTIVE_PIPELINE_DECISIONS_TOTAL",
    "PROACTIVE_BUDGET_DECISIONS_TOTAL",
    "get_or_create_budget_counter",
]

PROACTIVE_PIPELINE_DECISIONS_TOTAL: Counter = get_or_create_metric(
    Counter,
    "sparkle_proactive_pipeline_decisions_total",
    "Proactive pipeline decisions by trigger, event, decision and suppression reason",
    ["trigger", "event_name", "decision", "reason"],
)

#: V4-P01 统一预算闸门决定计数。label 有界：channel 2 值（nudge/spine）×
#: decision 2 值（allowed/suppressed）× reason 封闭词表
#: （unified_budget.BUDGET_DECISION_REASONS），无用户维度。
PROACTIVE_BUDGET_DECISIONS_TOTAL: Counter = get_or_create_metric(
    Counter,
    "sparkle_proactive_budget_decisions_total",
    "Unified proactive budget gate decisions by channel, decision and reason",
    ["channel", "decision", "reason"],
)


def get_or_create_budget_counter() -> Counter | None:
    """取统一预算决定计数器；指标面不可用时返回 None（调用方静默跳过）。"""
    try:
        return PROACTIVE_BUDGET_DECISIONS_TOTAL
    except Exception:  # noqa: BLE001 — metrics 永不影响判定主链
        return None
