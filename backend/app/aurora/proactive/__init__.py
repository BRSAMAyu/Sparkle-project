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

P-04 低风险 auto-execution 授权门（在 P-01 投递决策之后 / side effect 之前）：
- :class:`AutoExecOperation` / ``AUTOEXEC_OPERATION_REGISTRY`` — 低风险操作
  allowlist（封闭词表；高风险/不可逆结构性无表内名字）。
- :class:`AutoExecGrantStore` — 授权 grant/revoke 存储（版本化 → revoke 即时
  生效；fail-closed 读）。
- ``decide_auto_execution`` — auto/proposal 判定纯函数（allowlist 门 → 元数据
  复核门 → 授权门）。
- :class:`ProactiveAutoExecGate` — 执行门（幂等键恰一次 + receipt/notification）。
"""

from app.aurora.proactive.autoexec import (
    AUTOEXEC_EMPTY_VERSION,
    AUTOEXEC_OPERATION_REGISTRY,
    AUTOEXEC_OPERATION_VOCABULARY,
    AUTOEXEC_SCHEMA_VERSION,
    AutoExecDecision,
    AutoExecDecisionReason,
    AutoExecGrantStore,
    AutoExecOperation,
    AutoExecOutcome,
    AutoExecReceipt,
    AutoExecReceiptStore,
    AutoExecRequest,
    AutoExecStateUnavailable,
    ProactiveAutoExecGate,
    build_autoexec_receipt_notification,
    compute_grant_policy_version,
    decide_auto_execution,
    derive_autoexec_idempotency_key,
    grant_cache_key,
    validate_autoexec_allowlist,
)
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
    # P-04 auto-execution authorization gate
    "AUTOEXEC_SCHEMA_VERSION",
    "AUTOEXEC_EMPTY_VERSION",
    "AutoExecOperation",
    "AUTOEXEC_OPERATION_REGISTRY",
    "AUTOEXEC_OPERATION_VOCABULARY",
    "validate_autoexec_allowlist",
    "AutoExecDecision",
    "AutoExecDecisionReason",
    "AutoExecGrantStore",
    "AutoExecStateUnavailable",
    "compute_grant_policy_version",
    "grant_cache_key",
    "derive_autoexec_idempotency_key",
    "decide_auto_execution",
    "AutoExecRequest",
    "AutoExecReceipt",
    "AutoExecReceiptStore",
    "AutoExecOutcome",
    "ProactiveAutoExecGate",
    "build_autoexec_receipt_notification",
]
