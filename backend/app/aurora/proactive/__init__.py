"""
Aurora proactive pipeline (P-01): event → deterministic filter → Aurora.

组合出口：
- :class:`ProactiveTrigger` / ``classify_event`` — 七类触发的确定性分类器
  （白名单零新事件名）。
- :class:`SuppressionSnapshot` / ``evaluate_suppression`` — 六步纯函数抑制链
  （quiet_hours → mute → daily_cap → cooldown → recent_rejection → novelty，
  零 LLM）。
- :class:`ProactiveSuppressionStore` — 抑制状态的 Redis 快照存取（live/shadow
  scope 隔离）。
- :class:`ProactiveEventPipeline` — 管线主体 + EventBus 消费者组接入 +
  shadow 审计（metrics / recent_records / sink）。
"""

from app.aurora.proactive.pipeline import (
    DecisionSink,
    ProactiveDecisionRecord,
    ProactiveEventPipeline,
)
from app.aurora.proactive.state import (
    LIVE_SCOPE,
    SHADOW_SCOPE,
    ProactiveStateUnavailable,
    ProactiveSuppressionStore,
)
from app.aurora.proactive.suppression import (
    SUPPRESSION_STEPS,
    SuppressionDecision,
    SuppressionSnapshot,
    evaluate_suppression,
)
from app.aurora.proactive.triggers import (
    WHITELISTED_EVENT_NAMES,
    ProactiveTrigger,
    TriggerClassification,
    classify_event,
)

__all__ = [
    "ProactiveTrigger",
    "TriggerClassification",
    "classify_event",
    "WHITELISTED_EVENT_NAMES",
    "SUPPRESSION_STEPS",
    "SuppressionSnapshot",
    "SuppressionDecision",
    "evaluate_suppression",
    "ProactiveSuppressionStore",
    "ProactiveStateUnavailable",
    "LIVE_SCOPE",
    "SHADOW_SCOPE",
    "ProactiveDecisionRecord",
    "ProactiveEventPipeline",
    "DecisionSink",
]
