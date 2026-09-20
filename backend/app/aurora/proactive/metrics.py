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

from app.core.metrics import get_or_create_metric
from prometheus_client import Counter

__all__ = ["PROACTIVE_PIPELINE_DECISIONS_TOTAL"]

PROACTIVE_PIPELINE_DECISIONS_TOTAL: Counter = get_or_create_metric(
    Counter,
    "sparkle_proactive_pipeline_decisions_total",
    "Proactive pipeline decisions by trigger, event, decision and suppression reason",
    ["trigger", "event_name", "decision", "reason"],
)
