"""A-04 · 联合决策因子装配投影器 —— C-01/快照/registry/L0/L2/spine → A-02 因子。

A-02 REVIEW_RECEIPT §4.1 登记「最大缺口」：``InterventionPolicyEngine`` 的因子
此前由测试直供，生产无装配路径。本模块是**读侧投影器**（🔵：只读既有真源、
不新建事实）——把分散在五个系统里的决策输入投影为
``InterventionPolicyFactors`` / ``AllocationFactors``，供 ``decide_joint`` 族消费。

投影源（receipt §4.1 逐项对位）：
- **materiality** ← ``decision_fns/materiality.check_materiality``（读侧即投影：
  ``should_route`` 严格布尔）；snapshot/policy 缺失 → 不抑制（缺省保守 True）。
- **quiet_hours** ← R-01 L0 事实（``state_key="quiet_hours_active"``）；
  **budget** ← R-07 proactive 预算（usage vs ``proactive_policy.daily_budget``）。
- **capabilities/permissions** ← interaction_model_registry 变体
  （``VARIANT_CAPABILITY_PROJECTION`` 冻结表）+ privacy kill switch 剥除
  （``privacy_restricted=True`` → 剥敏感面 memory_read/peer_network/
  peer_contact/proactive_contact/model_write）。
- **双提名通道**（receipt §4.2）：L2 命中（``L2_INTERVENTION_TO_CATALOG``，
  内部干预名 → 目录成员）在先；spine 策略（``SPINE_STRATEGY_TO_INTERVENTION``）
  在后——序即优先级（L2 是确定性状态模式命中，置信高于策略启发）。目录外
  串不进 nominated（A-02 R0 的投影面前置：投影器只发目录成员）。

严格布尔纪律（receipt N3 警告 ``coerce`` 宽松）：
``materiality_sufficient`` / ``proactive_budget_available`` /
``quiet_hours`` / ``explicit_user_request`` 输出**恒为 ``bool``**——
- 布尔字段输入只认 ``True``/``False``（``1``/``"yes"``/``[]`` 等 truthy 值
  一律按缺失处理，绝不宽取）；
- 三态语义显式化：「事实缺失」投影为该字段的**保守缺省**并在
  ``projection_annotations`` 登记（可审计：哪个字段是投影缺省、哪个是真值）。

L2 任务步投影（``project_task_factors_from_l2``）：L2 模式命中的
``matched_states`` → 交付步 ``AllocationFactors``。语义判据逐项可评审：
- deadline_pressure → ``time_pressure=urgent``；
- knowledge_bottleneck / transfer_failure → ``learning_goal=True`` +
  ``cognitive_ownership=user_core``（能力修复的交付步本身是学习核心）；
- execution_consistency=task_abandoned / momentum_stalled → ``shared``
  （重建执行节奏是人机协作面）；
- affective_pressure（burnout 族）→ 保守缺省（pause 非 proactive 无预算面，
  任务因子仅作记录）；
- 计划结构调整（rescope/split/schedule 族）可回滚（rollback anchor 先例）
  → ``reversible=True`` + ``risk_class=low``。

韧性契约：两个投影函数对任何输入（含脏值）不 raise——脏输入投影为缺省 +
``projection_annotations["degraded"]`` 登记（联合核心的 NEVER-raises 契约从
装配面就成立）。零 IO（纯函数；redis/db 事实由调用方装配进
``JointFactorSources``）。
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from app.aurora.decision_fns.materiality import check_materiality
from app.aurora.intervention_catalog import SPINE_STRATEGY_TO_INTERVENTION
from app.aurora.intervention_policy import InterventionPolicyFactors
from app.aurora.runtime_v1.l2_intervention import L2_INTERVENTION_TO_CATALOG
from app.aurora.schemas import AuroraPolicyVersion, SignalSnapshot
from app.services.action_allocation_policy import AllocationFactors

#: interaction_model_registry 变体 → 能力面投影（policies/v1.0.yaml 的
#: allowed_tools_base 是工具名域，非能力词表——本表是「变体允许的干预能力面」
#: 的冻结投影；语义判据：default_conversation=纯对话；task_execution=任务
#: 执行面（分解/执行/生成）；meta_reflection=建模会话（生成+读记忆）；
#: holding_mode=情绪支持（仅对话，最小面））。registry 加变体而不更新此表
#: → ``project_joint_factors`` 把未知变体投影为最小面 {chat} 并登记 degraded
#: （不 fail-fast：读侧投影不得炸主管道；契约测试钉死四变体精确映射）。
VARIANT_CAPABILITY_PROJECTION: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "default_conversation": frozenset({"chat"}),
        "task_execution": frozenset({"chat", "llm_generate", "task_write", "tool_execution"}),
        "meta_reflection": frozenset({"chat", "llm_generate", "memory_read"}),
        "holding_mode": frozenset({"chat"}),
    }
)

#: privacy kill switch 生效时剥除的敏感面（receipt §4.1「privacy kill switch 派生」）。
#: 语义：隐私受限期不读用户记忆、不触达同侪、不主动联系、不写模型。
_PRIVACY_STRIPPED_CAPABILITIES: frozenset[str] = frozenset({"memory_read", "peer_network"})
_PRIVACY_STRIPPED_PERMISSIONS: frozenset[str] = frozenset(
    {"memory_read", "peer_contact", "proactive_contact", "model_write"}
)

#: L2 matched state_key → 交付步因子语义（见模块 docstring 判据表）。
_L2_LEARNING_SIGNAL_STATES: frozenset[str] = frozenset({"knowledge_bottleneck", "transfer_failure"})
_L2_SHARED_SIGNAL_STATES: frozenset[str] = frozenset(
    {"execution_consistency", "growth_momentum"}
)
_L2_TIME_PRESSURE_STATES: frozenset[str] = frozenset({"deadline_pressure"})
_L2_AFFECTIVE_STATES: frozenset[str] = frozenset({"affective_pressure"})


def _strict_bool(value: Any) -> bool | None:
    """严格布尔：只认 True/False；其余（含 1/0/'yes'/[]）按缺失返回 None。"""
    if value is True:
        return True
    if value is False:
        return False
    return None


def _note_degraded(notes: dict[str, Any], entry: str) -> None:
    degraded = notes.setdefault("degraded", [])
    if isinstance(degraded, list):
        degraded.append(entry)


def _strict_bool_or(value: Any, default: bool) -> bool:
    """严格布尔 + 显式保守缺省（缺失 → default，不宽取 truthy）。"""
    resolved = _strict_bool(value)
    return default if resolved is None else resolved


@dataclass(frozen=True)
class JointFactorSources:
    """因子装配的显式输入面（调用方装配；投影器零 IO——测试可全量复现）。

    三态纪律：布尔字段允许 None（= 事实缺失 → 保守缺省 + 登记）；文本/结构
    字段 None = 同义。所有字段都有投影缺省——空 sources 投影为全缺省因子
    （联合核心对全缺省因子的行为 = 保守 no_action 地板，见 A-02 R 守卫族）。
    """

    # 提名通道（receipt §4.2 双通道）
    l2_intervention: str | None = None  # L2 内部干预名（error_replan_bridge/adaptive_replan/reduce_load）
    spine_strategies: tuple[str, ...] = ()  # spine 策略键（序即优先级）

    # C-01 / Aurora 快照面（receipt §4.1 materiality 投影）
    snapshot: SignalSnapshot | None = None
    policy: AuroraPolicyVersion | None = None

    # registry + privacy 面（receipt §4.1 capabilities/permissions 派生）
    interaction_model_variant: str | None = None
    privacy_restricted: bool | None = None  # kill switch 派生（True=受限）
    permissions_granted: Iterable[str] = ()  # 调用方权威授予面（如 plan_adjust）

    # R-01 / R-07 面（receipt §4.1 quiet_hours/budget）
    quiet_hours_active: bool | None = None
    proactive_usage_today: int | None = None  # R-07 已用预算（None=无计数事实）

    # 上下文面
    task_context_present: bool | None = None  # has_task_context 事实
    explicit_user_request: bool | None = None
    cooldown_target: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "l2_intervention": self.l2_intervention,
            "spine_strategies": list(self.spine_strategies),
            "has_snapshot": self.snapshot is not None,
            "has_policy": self.policy is not None,
            "interaction_model_variant": self.interaction_model_variant,
            "privacy_restricted": self.privacy_restricted,
            "quiet_hours_active": self.quiet_hours_active,
            "proactive_usage_today": self.proactive_usage_today,
            "task_context_present": self.task_context_present,
            "explicit_user_request": self.explicit_user_request,
            "cooldown_target": self.cooldown_target,
        }


def _project_nominated(sources: JointFactorSources, notes: dict[str, Any]) -> tuple[str, ...]:
    """双提名通道投影：L2 在先、spine 策略在后；只发目录成员（去重保序）。"""
    nominated: list[str] = []
    if sources.l2_intervention is not None:
        catalog_name = L2_INTERVENTION_TO_CATALOG.get(str(sources.l2_intervention).strip())
        if catalog_name is not None:
            nominated.append(catalog_name)
        else:
            notes.setdefault("dropped_l2_nominations", []).append(str(sources.l2_intervention))
    for strategy in sources.spine_strategies:
        catalog_name = SPINE_STRATEGY_TO_INTERVENTION.get(str(strategy).strip())
        if catalog_name is not None and catalog_name not in nominated:
            nominated.append(catalog_name)
    return tuple(nominated)


def _project_capabilities(
    sources: JointFactorSources, notes: dict[str, Any]
) -> frozenset[str]:
    variant = sources.interaction_model_variant
    if variant is None or variant not in VARIANT_CAPABILITY_PROJECTION:
        if variant is not None:
            _note_degraded(notes, f"unknown_interaction_model_variant:{variant}")
        return frozenset({"chat"})  # 最小对话面（未知变体的保守投影）
    return VARIANT_CAPABILITY_PROJECTION[variant]


def project_joint_factors(
    sources: JointFactorSources | None,
) -> tuple[InterventionPolicyFactors, dict[str, Any]]:
    """装配投影：``JointFactorSources`` → ``(factors, projection_notes)``（严格布尔）。

    输出纪律（N3）：布尔字段恒 ``bool``；三态缺失 → 保守缺省并在
    ``projection_notes`` 登记（哪个字段是投影缺省、哪个是真值——调用方可
    随决策记录审计）。**不设 allocation_mode**——分配事实是 X-02 的输出、
    ``decide_joint`` 的第二入参（投影器不猜测分配，防双真源）。
    """
    notes: dict[str, Any] = {}
    if sources is None:
        sources = JointFactorSources()

    nominated = _project_nominated(sources, notes)
    capabilities = _project_capabilities(sources, notes)
    permissions = frozenset(
        str(entry).strip() for entry in sources.permissions_granted if str(entry).strip()
    )

    privacy_restricted = _strict_bool_or(sources.privacy_restricted, default=False)
    if privacy_restricted:
        capabilities = capabilities - _PRIVACY_STRIPPED_CAPABILITIES
        permissions = permissions - _PRIVACY_STRIPPED_PERMISSIONS
        notes["privacy_restricted_applied"] = True

    # materiality：读侧即投影（receipt §4.1）。snapshot/policy 齐备才判；
    # 任一缺失 → 不抑制（保守 True——R8 只剔非显式请求的非 inert 干预，
    # 缺失事实不得变成静默全局抑制）。check_materiality 自身异常同缺省。
    materiality_sufficient = True
    if sources.snapshot is not None and sources.policy is not None:
        try:
            materiality_sufficient = bool(check_materiality(sources.snapshot, sources.policy).should_route)
        except Exception:  # noqa: BLE001 — 投影韧性：脏快照按缺失处理
            materiality_sufficient = True
            _note_degraded(notes, "materiality_projection_failed")
    else:
        notes["materiality_defaulted"] = True

    # proactive budget：R-07 计数 vs policies 顶层 daily_budget（严格比较）。
    proactive_budget_available = True
    if sources.proactive_usage_today is not None and sources.policy is not None:
        try:
            daily_budget = int(sources.policy.proactive_policy.daily_budget)
            proactive_budget_available = bool(int(sources.proactive_usage_today) < daily_budget)
        except (TypeError, ValueError):
            proactive_budget_available = True
            notes["proactive_budget_defaulted"] = True
    elif sources.proactive_usage_today is not None:
        # 有计数但无 policy 面（不应发生——防御）：保守按预算可用，登记。
        notes["proactive_budget_defaulted"] = True

    factors = InterventionPolicyFactors(
        capabilities=capabilities,
        permissions=permissions,
        nominated=nominated,
        has_task_context=_strict_bool_or(sources.task_context_present, default=False),
        quiet_hours=_strict_bool_or(sources.quiet_hours_active, default=False),
        materiality_sufficient=materiality_sufficient,
        proactive_budget_available=proactive_budget_available,
        explicit_user_request=_strict_bool_or(sources.explicit_user_request, default=False),
        cooldown_target=(
            str(sources.cooldown_target).strip() if sources.cooldown_target else None
        ),
    )
    # 投影溯源：装配了什么、缺了什么（调用方可随决策记录审计）。
    if "degraded" not in notes:
        notes["degraded"] = []
    return factors, notes


def project_task_factors_from_l2(
    matched_states: Iterable[str] | None,
    *,
    task_ref: str | None = None,
    task_summary: str = "",
) -> AllocationFactors:
    """L2 模式命中的 matched_states → 交付步 ``AllocationFactors``。

    语义判据见模块 docstring（逐项可评审；脏输入 → 缺省 + 恒不 raise）。
    ``allocation_mode`` 不在此设（X-02 权威——本函数只供因子，mode 由
    ``decide_allocation`` 算出）。
    """
    states = {str(state).strip() for state in (matched_states or ()) if str(state).strip()}
    learning_hit = bool(states & _L2_LEARNING_SIGNAL_STATES)
    shared_hit = bool(states & _L2_SHARED_SIGNAL_STATES)
    urgent_hit = bool(states & _L2_TIME_PRESSURE_STATES)
    affective_hit = bool(states & _L2_AFFECTIVE_STATES)

    cognitive_ownership: str | None = None
    if learning_hit:
        cognitive_ownership = "user_core"  # 能力修复的交付步是学习核心（HUMAN_AGENT_HYBRID §2.1）
    elif shared_hit or affective_hit:
        cognitive_ownership = "shared"  # 节奏重建/降载调整是人机协作面

    return AllocationFactors.coerce(
        {
            "task_ref": task_ref,
            "task_summary": (task_summary or "")[:300],
            "task_type": None,
            "learning_goal": True if learning_hit else None,
            "cognitive_ownership": cognitive_ownership,
            "tool_advantage": None,
            "risk_class": "low",  # 计划结构调整经确认管道可回滚（rollback anchor 先例）
            "reversible": True,
            "explicit_intent": None,
            "embodiment_required": None,
            "privacy": None,
            "confidence": None,
            "time_pressure": "urgent" if urgent_hit else None,
            "user_preference": None,
        }
    )
