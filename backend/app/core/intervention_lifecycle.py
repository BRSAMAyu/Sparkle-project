"""D-05 · Intervention → Outcome 关联管线契约 —— 生命周期词表、审查语义与统计谦抑。

冻结声明（v3/07_tasks/cards/D-05.md，Stream DATA，Gate V3-3，locks analytics-intervention）：

- **D-05 是关联层，不是 outcome 真源**：outcome 事实归 D-02 outcome_ledger 五源
  （``app/core/outcome_ledger.py``，(source, source_id) 幂等键 + TruthClass 分级）。
  本模块只拥有「干预生命周期事件（exposure/accept/edit/reject/start/outcome 关联）」
  与「关联摘要的保守统计语义」。intervention 决策事实归 A-01
  ``aurora_decision.v1``——本模块消费其 decision_id（``aurora_<32hex>`` 内容寻址），
  不重述决策内容。
- **灵魂红线（卡面 Work 2）：outcome 必须来自真实行为信号**。关联白名单
  ``OUTCOME_ASSOCIATION_SOURCES`` 是封闭的 D-02 源子集（task 完成 / study 记录 /
  focus 会话 / quiz 判分）；chat reply / sentiment / 模型自评一律不是 outcome。
  白名单被三层钉死：import 期 ⊆ ``OutcomeSource`` 断言 + 契约测试精确字面冻结 +
  运行期 ``FORBIDDEN_OUTCOME_SIGNAL_PATTERNS`` 硬拒绝门（服务层记录前二次检查——
  即使白名单被未来变更污染，含 chat/reply/sentiment/message 字样的源值仍被拒收）。
- **behavioral 源 v1 有意排除**：其 ``routing_effectiveness`` 写入方
  （routing_outcome_service._judge_success）以 chat 信号分数
  （emotional_block/goal_clarity/"no_negative_followup_signal"）作判定——正属
  红线排除的信号族（代码自身注释亦承认其只是 weak behavioral estimate）；
  API 写入方（/interventions/outcomes）是客户端自报 success 布尔。M-06 仍可经
  D-02 ``query(source=BEHAVIORAL)`` 直读该源（D-02 已声明该消费面）；纳入关联
  白名单需 bump 本契约版本并过 reviewer。
- **同一 intervention 不双计**（验收 ①）：生命周期事件的存储身份 =
  (decision_id, event_type, dedupe_subkey)；outcome 关联事件的 dedupe_subkey =
  D-02 outcome_id（``outc_<hash>``），其余事件为空串。唯一约束（存储层）+
  确定性 ``derive_lifecycle_event_id``（``ilfe_<sha256[:32]>``，D-01/D-02 派生
  风格）共同保证「同一 decision + 同一事件类型恰一次」「同一 outcome 对同一
  decision 恰关联一次」。同输入同 id：重放投递可被消费方安全去重。
- **censored/unknown 语义明确区分**（验收 ①）：``ObservationStatus`` 是查询时点
  重算的读模型值（D-02 TruthClass 同款纪律，不是存储的可变状态）：
  - ``observed``：窗口内观察到 ≥1 条白名单 outcome；
  - ``censored_not_yet_due``：观察窗未到期，尚无 outcome——不是失败，不许计入负向；
  - ``censored_window_closed``：窗口已关、无 outcome，但用户在窗口内保持活跃
    （user_last_active_at ≥ window_end）——「在场而未行动」的删失；
  - ``censored_user_churned``：窗口内用户已不活跃（user_last_active_at < window_end
    或缺失）——「无从观察」的删失，比 window_closed 更少信息量，绝不推断为干预失败；
  - ``unknown``：行损坏/输入缺失，无法判定。
  删失计数进摘要的 n_censored_* 面，永不进 positive/negative 分母（生存分析纪律：
  删失 ≠ 负向）。
- **统计谦抑（DATA_FLYWHEEL §5「把相关性写成因果」禁令的机制化）**：
  单次观察低权（``single_observation`` 档）、重复观察升档（``repeated``/
  ``accumulated``，MEMORY_V3 §5「多次一致 outcome 才提高 evidence strength」）、
  rate 带 Wilson 95% 区间（n=0 时上界 > 0——无数据不得宣称 0%）、
  ``causal_claim`` 恒 False、claim 文案出自封闭模板并经禁词表
  （``FORBIDDEN_CLAIM_TERMS``：导致/使得/成功率/caused…）测试钉死。
  TruthClass 加权：actual=1.0 / self_reported=0.5 / estimated=0.25；
  demo/unknown 整体排除（B-02 demo cohort 污染防族，不进任何分子分母）。

切片维度（卡面 Work 2「按 goal/friction/execution_mode 切片」）：
- ``goal_type``：结构派生自 ``app.signals.goal_type_adapter.GOAL_TYPE_PROFILES``
  （6 值封闭集）+ ``unknown``（缺失时）；
- ``friction_tag``：结构派生自 spine ``app.signals.policy_engine._RULE_TABLE`` 的
  12 个 state_key → 10 个 friction family 的全量投影
  （``SPINE_STATE_KEY_TO_FRICTION``，A-02 ``SPINE_STRATEGY_TO_INTERVENTION``
  同款纪律：import 期双向断言，缺项/多项 fail-fast）+ ``unattributed``；
- ``execution_mode``：A-01 契约镜像（human/agent/hybrid；inert 无 mode）。

变更流程：词表/语义属冻结契约，改动需 bump ``INTERVENTION_LIFECYCLE_SCHEMA_VERSION``
并过 reviewer（C-01/D-01/D-02 同款纪律）。
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping, Sequence
from uuid import UUID

from app.core.aurora_decision import (
    _INERT_INTERVENTIONS,
    AURORA_INTERVENTION_TYPES,
)
from app.core.outcome_ledger import OutcomePolarity, OutcomeSource, TruthClass
from app.signals.goal_type_adapter import GOAL_TYPE_PROFILES
from app.signals.policy_engine import _RULE_TABLE

INTERVENTION_LIFECYCLE_SCHEMA_VERSION = "intervention_lifecycle.v1"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展需 bump 契约版本 + reviewer）
# ---------------------------------------------------------------------------


class LifecycleEventType(StrEnum):
    """干预生命周期事件类型（卡面 Work 1 六段：exposure/accept/edit/reject/start/outcome）。

    - ``exposed``：干预对用户可见（漏斗锚点；governance_mode=shadow 的决策不可
      能有 exposure——服务层拒绝）；
    - ``accepted`` / ``edited`` / ``rejected``：用户对干预的即时反馈
      （DATA_FLYWHEEL §4 Immediate loop）；
    - ``started``：用户开始按干预行动（§4 Behavioral loop 的 start）；
    - ``outcome_observed``：一条白名单 outcome 被关联到该干预（D-05 自有的关联
      事实；outcome 本身的真相归 D-02，此处只记 (decision_id, outcome_id) 链接）。
    """

    EXPOSED = "exposed"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"
    STARTED = "started"
    OUTCOME_OBSERVED = "outcome_observed"


#: 全体生命周期事件类型（封闭）。
LIFECYCLE_EVENT_TYPES: frozenset[str] = frozenset(e.value for e in LifecycleEventType)

#: 用户响应事件（漏斗中段；记录前置 = exposure 已存在）。
USER_RESPONSE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        LifecycleEventType.ACCEPTED.value,
        LifecycleEventType.EDITED.value,
        LifecycleEventType.REJECTED.value,
        LifecycleEventType.STARTED.value,
    }
)


class ObservationStatus(StrEnum):
    """一次 exposure 的 outcome 观察状态（读模型值，查询时点重算；见模块 docstring）。"""

    OBSERVED = "observed"
    CENSORED_NOT_YET_DUE = "censored_not_yet_due"
    CENSORED_WINDOW_CLOSED = "censored_window_closed"
    CENSORED_USER_CHURNED = "censored_user_churned"
    UNKNOWN = "unknown"


#: 观察窗（align 既有 InterventionOutcomeTracker 的 72h follow-up；边界 [1h, 30d]）。
DEFAULT_OBSERVATION_WINDOW_HOURS = 72
MIN_OBSERVATION_WINDOW_HOURS = 1
MAX_OBSERVATION_WINDOW_HOURS = 24 * 30

# ---------------------------------------------------------------------------
# 切片词表（结构派生 + fail-fast；A-02 纪律）
# ---------------------------------------------------------------------------

#: friction family 封闭集（spine state_key 的粗粒度归并；语义判据逐键可评审）。
INTERVENTION_FRICTION_TAGS: frozenset[str] = frozenset(
    {
        "execution_friction",  # 任务粒度/节奏失配（启动阻力的结构面）
        "knowledge_bottleneck",  # 知识迁移失败（学会→会用断裂）
        "material_gap",  # 材料/资源在库未用
        "deadline_pressure",  # goal 模式层面的时限压力（考试抢救族）
        "overload_crisis",  # 危机模式（负荷/风险最小过线）
        "cognitive_overload",  # 认知负荷过高
        "affective_pressure",  # 情绪/情感压力
        "engagement_momentum",  # 动量维持/再点燃
        "recall_gap",  # 记忆召回缺口（spaced recall）
        "community_gap",  # 同侪/社群缺口
        "unattributed",  # 无 spine 信号锚点的 exposure（缺省，不算分析失败）
    }
)

#: spine state_key → friction family 全量投影（key 集 == ``_RULE_TABLE`` key 集，
#: import 期双向断言）。语义判据：
#: - task_granularity_fit → execution_friction；knowledge_transfer → knowledge_bottleneck；
#: - material_utilization → material_gap；goal_mode → deadline_pressure；
#: - crisis_mode → overload_crisis；cognitive_load → cognitive_overload；
#: - affective_pressure → affective_pressure；growth_momentum → engagement_momentum；
#: - recall_needed → recall_gap；
#: - community_{cohort_pattern,partner_feedback,resource_recommendation} → community_gap。
SPINE_STATE_KEY_TO_FRICTION: dict[str, str] = {
    "task_granularity_fit": "execution_friction",
    "knowledge_transfer": "knowledge_bottleneck",
    "material_utilization": "material_gap",
    "goal_mode": "deadline_pressure",
    "crisis_mode": "overload_crisis",
    "cognitive_load": "cognitive_overload",
    "affective_pressure": "affective_pressure",
    "growth_momentum": "engagement_momentum",
    "recall_needed": "recall_gap",
    "community_cohort_pattern": "community_gap",
    "community_partner_feedback": "community_gap",
    "community_resource_recommendation": "community_gap",
}

# 完整性守卫（import 期）：spine _RULE_TABLE 演进（新增/改名 state_key）时，
# 投影缺项/多项即刻暴露，而非运行期静默落 unattributed。
assert set(SPINE_STATE_KEY_TO_FRICTION) == set(_RULE_TABLE), (
    "SPINE_STATE_KEY_TO_FRICTION must exactly cover the spine _RULE_TABLE state keys"
)
assert set(SPINE_STATE_KEY_TO_FRICTION.values()) <= INTERVENTION_FRICTION_TAGS - {"unattributed"}

#: goal 切片词表：结构派生自 goal_type_adapter 权威 + unknown（缺失档）。
GOAL_SLICE_TYPES: frozenset[str] = frozenset(GOAL_TYPE_PROFILES) | {"unknown"}

#: execution_mode 切片词表：A-01 契约镜像三值 + unattributed（inert/缺失档）。
EXECUTION_MODE_SLICES: frozenset[str] = frozenset({"human", "agent", "hybrid", "unattributed"})

# ---------------------------------------------------------------------------
# outcome 关联白名单（灵魂红线；三层钉死见模块 docstring）
# ---------------------------------------------------------------------------

#: 关联白名单（封闭；D-02 五源的子集，v1 有意排除 behavioral——见模块 docstring）。
OUTCOME_ASSOCIATION_SOURCES: frozenset[OutcomeSource] = frozenset(
    {
        OutcomeSource.TASK_COMPLETION,
        OutcomeSource.STUDY_RECORD,
        OutcomeSource.FOCUS_SESSION,
        OutcomeSource.QUIZ_FEEDBACK,
    }
)

#: 运行期硬拒绝门：源值含这些字样一律拒收（即使白名单被未来变更污染）。
#: 这是「禁止用 chat reply/sentiment 当 outcome」的机制化下限，而非仅测试约定。
FORBIDDEN_OUTCOME_SIGNAL_PATTERNS: tuple[str, ...] = (
    "chat",
    "reply",
    "message",
    "sentiment",
    "emotion",
    "self_eval",
    "model_score",
)

# import 期断言：白名单是 D-02 封闭枚举的子集，且不含任何禁用字样。
assert OUTCOME_ASSOCIATION_SOURCES <= set(OutcomeSource), (
    "OUTCOME_ASSOCIATION_SOURCES must be a subset of the D-02 OutcomeSource vocabulary"
)
assert not any(
    pattern in source.value for source in OUTCOME_ASSOCIATION_SOURCES for pattern in FORBIDDEN_OUTCOME_SIGNAL_PATTERNS
), "OUTCOME_ASSOCIATION_SOURCES must never contain chat/reply/sentiment-class sources"

#: TruthClass → 关联证据权重（统计谦抑的加权面；demo/unknown 整体排除）。
TRUTH_CLASS_ASSOCIATION_WEIGHTS: dict[TruthClass, float] = {
    TruthClass.ACTUAL: 1.0,
    TruthClass.SELF_REPORTED: 0.5,
    TruthClass.ESTIMATED: 0.25,
    TruthClass.DEMO: 0.0,
    TruthClass.UNKNOWN: 0.0,
}

#: claim 文案禁词（因果与成功宣称族；测试对全部档位模板扫描钉死）。
FORBIDDEN_CLAIM_TERMS: tuple[str, ...] = (
    "导致",
    "使得",
    "因为",
    "成功率",
    "有效率",
    "证明了",
    "cause",
    "caused",
    "leads to",
    "proves",
    "guarantees",
)

_DECISION_ID_RE = re.compile(r"^aurora_[0-9a-f]{32}$")

#: 证据档位（MEMORY_V3 §5：单次低权、重复提升）。
EVIDENCE_TIER_INSUFFICIENT = "insufficient"
EVIDENCE_TIER_SINGLE = "single_observation"
EVIDENCE_TIER_REPEATED = "repeated"
EVIDENCE_TIER_ACCUMULATED = "accumulated"

#: 升档到 accumulated 所需观察数（多次一致 outcome 的「多次」下限取 5）。
ACCUMULATED_TIER_MIN_OBSERVATIONS = 5


def is_exposable_intervention(intervention_type: str, governance_mode: str | None) -> tuple[bool, str]:
    """exposure 可行性判定（纯函数）：inert 与 shadow 决策不可能被暴露给用户。

    - intervention_type ∉ A-01 目录 → 拒（词表外）；
    - inert（no_action/abstain）→ 拒（A-01：不行动没有用户可见载体）；
    - governance_mode="shadow" → 拒（A-01 契约：shadow 不得作用于用户可见行为，
      因此 exposure 事件在契约上不可能合法存在——记录它即伪造漏斗锚点）。
    """
    if intervention_type not in AURORA_INTERVENTION_TYPES:
        return False, f"intervention_type {intervention_type!r} out of A-01 vocabulary"
    if intervention_type in _INERT_INTERVENTIONS:
        return False, f"inert intervention {intervention_type!r} has no user-visible surface"
    if governance_mode == "shadow":
        return False, "shadow-governance decision must never be exposed to user-visible behavior"
    return True, ""


def is_whitelisted_outcome_source(source: OutcomeSource | str) -> bool:
    """白名单 + 硬拒绝门（服务层记录前调用；两层都在此函数内）。"""
    try:
        value = OutcomeSource(source).value
    except (ValueError, TypeError):
        return False
    if OutcomeSource(source) not in OUTCOME_ASSOCIATION_SOURCES:
        return False
    # 硬拒绝门：即使未来白名单被污染，禁用字样仍在此拦截。
    return not any(pattern in value for pattern in FORBIDDEN_OUTCOME_SIGNAL_PATTERNS)


def friction_tag_from_state_key(state_key: str | None) -> str:
    """spine state_key → friction family；未知/缺失 → ``unattributed``（防御性降级）。"""
    if not state_key:
        return "unattributed"
    return SPINE_STATE_KEY_TO_FRICTION.get(str(state_key), "unattributed")


def goal_slice(goal_type: str | None) -> str:
    """goal 切片值：落在 goal_type_adapter 封闭集内即返回，否则 ``unknown``。"""
    if not goal_type:
        return "unknown"
    value = str(goal_type).strip().lower()
    return value if value in GOAL_SLICE_TYPES else "unknown"


def execution_mode_slice(execution_mode: str | None) -> str:
    """execution_mode 切片值（human/agent/hybrid；缺失 → ``unattributed``）。"""
    if not execution_mode:
        return "unattributed"
    value = str(execution_mode).strip().lower()
    return value if value in EXECUTION_MODE_SLICES else "unattributed"


def clamp_observation_window_hours(hours: int | float | None) -> int:
    """观察窗钳制到 [MIN, MAX]；缺失/非法 → DEFAULT（72h，与既有 tracker 对齐）。"""
    try:
        value = int(hours)
    except (TypeError, ValueError):
        return DEFAULT_OBSERVATION_WINDOW_HOURS
    return max(MIN_OBSERVATION_WINDOW_HOURS, min(MAX_OBSERVATION_WINDOW_HOURS, value))


# ---------------------------------------------------------------------------
# 幂等键
# ---------------------------------------------------------------------------


def derive_lifecycle_event_id(
    *,
    decision_id: str,
    event_type: LifecycleEventType | str,
    dedupe_subkey: str = "",
) -> str:
    """确定性生命周期事件幂等 id（``ilfe_<sha256[:32]>``，D-01/D-02 派生风格）。

    同一 (decision_id, event_type, dedupe_subkey) 恒产同 id：重放投递可被消费方
    安全去重；存储层另有唯一约束兜底并发（M-07 FOR UPDATE+复查的唯一约束同法）。
    decision_id 必须是 A-01 内容寻址形态（``aurora_<32hex>``）——D-05 只消费
    A-02/A-04 决策产物，不接受裸 UUID 或自由串。
    """
    value = LifecycleEventType(event_type).value
    if not _DECISION_ID_RE.match(str(decision_id)):
        raise ValueError(f"decision_id must be aurora_<32hex> (A-01 content-addressed): {decision_id!r}")
    seed = json.dumps(
        {
            "schema": INTERVENTION_LIFECYCLE_SCHEMA_VERSION,
            "decision_id": str(decision_id),
            "event_type": value,
            "dedupe_subkey": str(dedupe_subkey or ""),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "ilfe_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]


def linkage_keys(
    *,
    task_id: UUID | str | None = None,
    plan_id: UUID | str | None = None,
    node_id: UUID | str | None = None,
    intervention_request_id: UUID | str | None = None,
) -> dict[str, str]:
    """exposure 时刻捕获的关联键（canonical UUID str；无效值剔除不炸）。

    outcome 侧（D-02 ``OutcomeEntry.correlation``）与 exposure 侧以此对齐：
    任一共同键 + 窗口内时序 = 关联候选。behavioral 源的 intervention_id 键
    v1 不参与匹配（该源整体不在白名单）。
    """
    keys: dict[str, str] = {}
    for name, value in (
        ("task_id", task_id),
        ("plan_id", plan_id),
        ("node_id", node_id),
        ("intervention_request_id", intervention_request_id),
    ):
        if value is None:
            continue
        try:
            keys[name] = str(UUID(str(value)))
        except (ValueError, TypeError, AttributeError):
            continue
    return keys


def outcome_links_exposure(
    exposure_linkage: Mapping[str, str],
    outcome_correlation: Mapping[str, Any],
) -> bool:
    """关联判定（纯函数）：outcome.correlation 与 exposure.linkage 有共同键值。

    只比对四类关联键；outcome_correlation 中的其余键（session_id 等）不构成
    干预关联依据。脏值（非 canonical UUID str）不匹配，不抛异常。
    """
    if not exposure_linkage:
        return False
    for key in ("task_id", "plan_id", "node_id", "intervention_request_id"):
        exposure_value = exposure_linkage.get(key)
        outcome_value = outcome_correlation.get(key) if outcome_correlation else None
        if not exposure_value or not outcome_value:
            continue
        if str(exposure_value) == str(outcome_value):
            return True
    return False


# ---------------------------------------------------------------------------
# 审查语义（censored/unknown；纯函数）
# ---------------------------------------------------------------------------


def resolve_observation_status(
    *,
    exposed_at: datetime | None,
    window_hours: int | None,
    outcome_times: Sequence[datetime] = (),
    now: datetime,
    user_last_active_at: datetime | None = None,
    exposure_valid: bool = True,
) -> ObservationStatus:
    """单次 exposure 的观察状态（验收 ①；查询时点重算的读模型值）。

    判定顺序（确定性，逐条短路）：
    1. 行损坏（exposure_valid=False 或 exposed_at 缺失）→ UNKNOWN；
    2. 存在窗口内 outcome（exposed_at ≤ t ≤ exposed_at + window）→ OBSERVED
       （窗口外 outcome 不是本 exposure 的观察——服务层拒记窗口外关联，
       本函数对调用方传入的列表同样只认窗口内）；
    3. now < 窗口末 → CENSORED_NOT_YET_DUE；
    4. 窗口已关：
       - user_last_active_at ≥ 窗口末（用户在场而未行动）→ CENSORED_WINDOW_CLOSED；
       - user_last_active_at < 窗口末或缺失（用户已离开，无从观察）→
         CENSORED_USER_CHURNED。
    """
    if not exposure_valid or exposed_at is None:
        return ObservationStatus.UNKNOWN
    window = clamp_observation_window_hours(window_hours)
    window_end = exposed_at.timestamp() + window * 3600
    exposed_ts = exposed_at.timestamp()
    for occurred in outcome_times:
        try:
            occurred_ts = occurred.timestamp()
        except (AttributeError, ValueError, OSError):
            continue
        if exposed_ts <= occurred_ts <= window_end:
            return ObservationStatus.OBSERVED
    now_ts = now.timestamp()
    if now_ts < window_end:
        return ObservationStatus.CENSORED_NOT_YET_DUE
    if user_last_active_at is None:
        return ObservationStatus.CENSORED_USER_CHURNED
    try:
        active_ts = user_last_active_at.timestamp()
    except (AttributeError, ValueError, OSError):
        return ObservationStatus.CENSORED_USER_CHURNED
    if active_ts >= window_end:
        return ObservationStatus.CENSORED_WINDOW_CLOSED
    return ObservationStatus.CENSORED_USER_CHURNED


# ---------------------------------------------------------------------------
# 统计谦抑（Wilson 区间 / 档位 / claim 模板；纯函数，stdlib-only）
# ---------------------------------------------------------------------------


def wilson_interval(positives: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% 区间（默认 z=1.96）。

    保守性：n ≤ 0 → (0.0, 1.0)（无数据时不得宣称 0%——上界保持 1）；边界钳到
    [0, 1]。选 Wilson 而非 Beta 分位数是为保持 stdlib-only（无 scipy 依赖）。
    """
    if n <= 0:
        return 0.0, 1.0
    p = positives / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, centre - margin), min(1.0, centre + margin)


def association_evidence_tier(n_observed: int) -> str:
    """证据档位：0 → insufficient；1 → single_observation；2–4 → repeated；≥5 → accumulated。

    MEMORY_V3 §5「单次低权、多次一致才提升」的机制化。档位只看观察数，
    不看方向——negative 观察同样积累证据（失败保留，DATA_FLYWHEEL §4）。
    """
    if n_observed <= 0:
        return EVIDENCE_TIER_INSUFFICIENT
    if n_observed == 1:
        return EVIDENCE_TIER_SINGLE
    if n_observed < ACCUMULATED_TIER_MIN_OBSERVATIONS:
        return EVIDENCE_TIER_REPEATED
    return EVIDENCE_TIER_ACCUMULATED


def association_claim(
    tier: str,
    *,
    n_observed: int,
    n_positive: int,
    n_negative: int,
    scope_label: str = "该范围",
) -> str:
    """非因果 claim 模板（封闭文案；禁词由契约测试对全部档位扫描钉死）。

    措辞只允许「共同出现/相关」族词汇；方向分解（正/负向计数）交由结构化字段，
    文案不翻译成评价性断言。
    """
    if tier == EVIDENCE_TIER_INSUFFICIENT or n_observed <= 0:
        return f"{scope_label}尚无足够的观察样本，不能判断该帮助与此情境下结果的关联。"
    if tier == EVIDENCE_TIER_SINGLE:
        return f"{scope_label}在相似情境下观察到 1 次与该帮助共同出现的结果（单次观察，低权重，非因果结论）。"
    if tier == EVIDENCE_TIER_REPEATED:
        return (
            f"{scope_label}在相似情境下 {n_observed} 次观察到该帮助与结果共同出现"
            f"（重复观察，相关性证据，非因果结论）。"
        )
    return (
        f"{scope_label}在相似情境下累计 {n_observed} 次观察到该帮助与结果共同出现"
        f"（较一致的相关证据，仍非因果宣称）。"
    )


def truth_class_weight(truth_class: TruthClass | str | None) -> float:
    """TruthClass → 关联证据权重；demo/unknown → 0（整体排除，不入分子分母）。"""
    if truth_class is None:
        return 0.0
    try:
        return TRUTH_CLASS_ASSOCIATION_WEIGHTS[TruthClass(truth_class)]
    except (ValueError, TypeError):
        return 0.0


# ---------------------------------------------------------------------------
# 情境签名与摘要载体（M-06 Experience projector 消费面）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SituationSignature:
    """MEMORY_V3 §5 situation signature 的 D-05 投影（切片四元组）。

    M-06 以此作「相似情境」检索键；与 SliceSummary.group_key 一致。
    """

    intervention_type: str
    goal_type: str
    friction_tag: str
    execution_mode: str

    def as_tuple(self) -> tuple[str, str, str, str]:
        return (self.intervention_type, self.goal_type, self.friction_tag, self.execution_mode)

    def as_dict(self) -> dict[str, str]:
        return {
            "intervention_type": self.intervention_type,
            "goal_type": self.goal_type,
            "friction_tag": self.friction_tag,
            "execution_mode": self.execution_mode,
        }


@dataclass(frozen=True)
class SliceSummary:
    """一个情境切片的保守关联摘要（统计谦抑结构的原子单位）。

    - ``n_exposed``：去重后的 exposure 数（每 decision 恰一次）；
    - ``n_accepted`` / ``n_started``：漏斗中段计数；
    - ``n_positive`` / ``n_negative``：观察到的白名单 outcome 方向分解
      （negative 是真实负向结果如 quiz_failed，不是删失）；
    - ``n_censored_*``：三类删失 + unknown（永不进 rate 分母）；
    - ``positive_association_rate``：n_positive / n_observed（观察子集内的
      相关率；命名禁用 success rate）；
    - ``rate_interval``：Wilson 95%（对 n_observed 计算）；
    - ``weighted_positive_rate``：TruthClass 加权面（actual=1.0/self_reported=0.5/
      estimated=0.25；demo/unknown 排除）；
    - ``evidence_strength`` / ``claim`` / ``causal_claim=False``：谦抑措辞层。
    """

    signature: SituationSignature
    n_exposed: int
    n_accepted: int = 0
    n_started: int = 0
    n_positive: int = 0
    n_negative: int = 0
    n_censored_not_yet_due: int = 0
    n_censored_window_closed: int = 0
    n_censored_user_churned: int = 0
    n_unknown: int = 0
    weighted_positive: float = 0.0
    weighted_total: float = 0.0
    positive_association_rate: float = 0.0
    rate_interval: tuple[float, float] = (0.0, 1.0)
    weighted_positive_rate: float = 0.0
    evidence_strength: str = EVIDENCE_TIER_INSUFFICIENT
    claim: str = ""
    causal_claim: bool = False

    @property
    def n_observed(self) -> int:
        return self.n_positive + self.n_negative

    @property
    def group_key(self) -> tuple[str, str, str, str]:
        return self.signature.as_tuple()

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "signature": self.signature.as_dict(),
            "n_exposed": self.n_exposed,
            "n_accepted": self.n_accepted,
            "n_started": self.n_started,
            "n_observed": self.n_observed,
            "n_positive": self.n_positive,
            "n_negative": self.n_negative,
            "n_censored_not_yet_due": self.n_censored_not_yet_due,
            "n_censored_window_closed": self.n_censored_window_closed,
            "n_censored_user_churned": self.n_censored_user_churned,
            "n_unknown": self.n_unknown,
            "weighted_positive": round(self.weighted_positive, 6),
            "weighted_total": round(self.weighted_total, 6),
            "positive_association_rate": round(self.positive_association_rate, 6),
            "rate_interval": [round(self.rate_interval[0], 6), round(self.rate_interval[1], 6)],
            "weighted_positive_rate": round(self.weighted_positive_rate, 6),
            "evidence_strength": self.evidence_strength,
            "claim": self.claim,
            "causal_claim": self.causal_claim,
        }
        return payload


@dataclass(frozen=True)
class AssociationSummary:
    """per-user / per-scope 的历史结果摘要（验收 ②的载体）。

    ``scope``：``("user", <uuid>)`` 单用户；``("global",)`` 跨用户聚合
    （排除 seed/guest cohort，语义与 D-02 exclude_seed_cohort 一致）。
    ``watermark``：单调性印记（max event id + 计数），供 M-06 Context
    retrieval 侧做缓存失效判断（性能要求：摘要可增量/可缓存）。
    """

    scope: tuple[str, ...]
    generated_at: datetime
    since: datetime | None
    until: datetime | None
    watermark: str
    slices: tuple[SliceSummary, ...] = field(default_factory=tuple)

    @property
    def n_exposures_total(self) -> int:
        return sum(s.n_exposed for s in self.slices)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": INTERVENTION_LIFECYCLE_SCHEMA_VERSION,
            "scope": list(self.scope),
            "generated_at": self.generated_at.isoformat(),
            "since": self.since.isoformat() if self.since else None,
            "until": self.until.isoformat() if self.until else None,
            "watermark": self.watermark,
            "n_exposures_total": self.n_exposures_total,
            "slices": [s.to_dict() for s in self.slices],
        }


__all__ = [
    "INTERVENTION_LIFECYCLE_SCHEMA_VERSION",
    "ACCUMULATED_TIER_MIN_OBSERVATIONS",
    "DEFAULT_OBSERVATION_WINDOW_HOURS",
    "MIN_OBSERVATION_WINDOW_HOURS",
    "MAX_OBSERVATION_WINDOW_HOURS",
    "LifecycleEventType",
    "LIFECYCLE_EVENT_TYPES",
    "USER_RESPONSE_EVENT_TYPES",
    "ObservationStatus",
    "INTERVENTION_FRICTION_TAGS",
    "SPINE_STATE_KEY_TO_FRICTION",
    "GOAL_SLICE_TYPES",
    "EXECUTION_MODE_SLICES",
    "OUTCOME_ASSOCIATION_SOURCES",
    "FORBIDDEN_OUTCOME_SIGNAL_PATTERNS",
    "TRUTH_CLASS_ASSOCIATION_WEIGHTS",
    "FORBIDDEN_CLAIM_TERMS",
    "EVIDENCE_TIER_INSUFFICIENT",
    "EVIDENCE_TIER_SINGLE",
    "EVIDENCE_TIER_REPEATED",
    "EVIDENCE_TIER_ACCUMULATED",
    "SituationSignature",
    "SliceSummary",
    "AssociationSummary",
    "association_claim",
    "association_evidence_tier",
    "clamp_observation_window_hours",
    "derive_lifecycle_event_id",
    "execution_mode_slice",
    "friction_tag_from_state_key",
    "goal_slice",
    "is_exposable_intervention",
    "is_whitelisted_outcome_source",
    "linkage_keys",
    "outcome_links_exposure",
    "resolve_observation_status",
    "truth_class_weight",
    "wilson_interval",
]
