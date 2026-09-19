"""A-04 · Aurora 联合决策核心 —— intervention（A-02）× allocation（X-02）联合空间（aurora_joint_decision.v1）。

本卡解决的问题：A-02（选哪个干预）与 X-02（谁执行）此前是两个各自猜测的系统——
A-02 只镜像一个平铺的 ``allocation_mode`` 字符串，X-02 不知道自己选出的 mode 会
把哪些干预变得不可交付。本模块把两者放进**一个联合可行空间**：

    joint_feasible = { (intervention, mode) :
        intervention ∈ A-02 feasible（R0..R9 守卫后）
        ∧ pair(intervention, mode) 通过联合结构约束（J 码）
        ∧ allocation 事实成立（X-02 是 mode 的唯一权威） }

确定性裁决序（对抗面钉死，两系统结论冲突时按此序落锤）：

1. **显式用户意图最高**（X-02 X1「我自己做」/ X2「帮我做」；A-02 X1 显式请求）——
   系统提名不得翻盘用户主权；硬守卫仍不可越（X-02 X2.delegate_downgraded_by_guard
   先例：学习守卫降级显式委托）。
2. **结构性守卫不可越**（X-02 R1..R6/G1；A-02 R0..R5）——任何组合不得绕过。
3. **分配事实优先于干预提名**（D3.conflict_allocation_precedence）：J1 冲突时
   干预让位（X-02 是「谁执行」的 rubric 权威——mode 是事实输入，不是谈判对象）。
   冲突归因完整记录：哪个提名被哪个 J 码排除、背后的 allocation why 是什么。
4. **交付再分配可救则救**（D4.delivery_reallocation_applied）：被提名的步绑定
   干预若与任务步分配冲突，但交付兼容 mode 仍在 X-02 可行集内，则以**交付锚定
   因子**重跑一次 ``decide_allocation``（仍是 X-02 权威，非第二套 rubric——只改
   变锚定的步骤语义，学习/风险/隐私/具身因子原样保留，守卫恒同）。救得回则
   联合决策携带再分配后的 mode + allocation_ref；救不回落回 D3。
5. **确定性缺省**：合法提名序内取第一个联合合法者（D1）；无 → no_action（D2）。

联合结构约束（J 码，纯表驱动）：
- **步绑定干预**（delivery = 步骤执行本身：rescope/split/schedule/practice/
  review/delegate/execute/co_execute）：mode 必须落在 ``JOINT_STEP_BOUND_DELIVERY_MODES``
  的允许集内（如 practice 需要 hybrid——agent 备练用户练，纯 agent 是代写矛盾、
  纯 human 无准备面；delegate/execute 需要 agent；co_execute 需要 hybrid）。
  其中 requires_allocation 三项与 A-02 目录 ``allocation_modes`` import 期互检
  （漂移即 fail-fast）。
- **系统面干预**（clarify/explain/retrieve/reflect/connect_peer/pause/remind）：
  由系统面（chat/llm_generate/scheduler/peer）交付，不绑定任务步执行权——
  A-02 自身守卫已判（提醒不受任务 mode 牵连：human 执行的任务照样能提醒）。
  mode 镜像 = 目录标称值，不携带 allocation_ref（A-01 边界：纯对话域控制决策
  可独占携带 mode）。

P3-7/P3-8 硬化（A-01 R2 回执登记项，本卡机制化）：
- ``read_decision_contract``：统一读门——重构 + ``validate()``（P3-7 None 通道
  机制化）+ allocation 一致性硬校验 + shadow 治理门（shadow 决策不得作用于用户
  可见行为）。
- ``enforce_allocation_consistency``：比 A-01 ``consistent_with_allocation`` 更严
  ——allocation_ref 已指向分配决策时，分配缺 mode 不再静默放行（P3-8）；
  步绑定 actionable 干预经联合链产出时必须携带 allocation_ref（镜像值必须有
  分配支撑）。
- decision_id 内容寻址纪律（P3-4）：本模块产出/消费的一切 occurrence 记录以
  occurrence_id（uuid）为发生键；decision_id 只作内容锚（跨 occurrence 复用同号
  是 by design）。``JointDecisionRecord.occurrence_id`` 恒携带。

与既有权威的关系（不重建、不清重）：
- mode 词表 = ExecutionMode；分配判定 = X-02 decide_allocation（本模块只调用、
  永不重算 guard）；干预可行性 = A-02 evaluate_intervention_policy（同）；
  契约形状 = A-01 AuroraDecisionContract（extend-only 消费）；
  cognitive_ownership = X-02 recommended_cognitive_ownership 镜像（永不落 X-01 F5
  矛盾集——X-02 构造保证，本模块透传）。
- 事件名复用 ``decision.recorded``（D-01 registry 既有 reserved 名，零新名）；
  metadata 走 ``build_event_metadata`` shared-fields 契约（X-02 同款）。

韧性契约（A-02/X-02 同款）：``decide_joint`` 同步、确定性、无 IO、对任何输入
（含脏值）不 raise——内部异常降级 no_action + ``E1.degraded_to_rule_default``。

冻结声明：``JOINT_REASONS`` / ``JOINT_STEP_BOUND_DELIVERY_MODES`` 封闭词表被
backend/tests/contract/test_joint_decision_contract.py 双冻结（精确集 + sha256）；
扩词表需 bump ``JOINT_DECISION_VERSION`` 并过两位 reviewer。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Callable, Mapping
from uuid import UUID, uuid4

from loguru import logger

from app.aurora.intervention_catalog import INTERVENTION_CATALOG
from app.aurora.intervention_policy import (
    INTERVENTION_POLICY_VERSION,
    InterventionPolicyEvaluation,
    InterventionPolicyFactors,
    evaluate_intervention_policy,
)
from app.core.aurora_decision import (
    AURORA_COGNITION_TIERS,
    AURORA_DECISION_REF_SCHEMES,
    AURORA_GOVERNANCE_MODES,
    AURORA_INTERVENTION_TYPES,
    AuroraDecisionContract,
    aurora_decision_from_dict,
)
from app.core.event_registry import EventSource, build_event_metadata
from app.models.execution_intent import ExecutionMode
from app.services.action_allocation_policy import (
    ALLOCATION_POLICY_VERSION,
    AllocationDecision,
    AllocationFactors,
    decide_allocation,
)

JOINT_DECISION_VERSION = "aurora_joint_decision.v1"

JOINT_DECISION_EVENT_NAME = "decision.recorded"  # D-01 既有 reserved 名，零新增

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展需 bump 版本 + 两位 reviewer）
# ---------------------------------------------------------------------------

#: 联合决策 reason codes。前缀语义：J*=联合结构约束 · D*=确定性选择/裁决 ·
#: X*=显式用户意图 · E*=降级。
JOINT_REASONS: frozenset[str] = frozenset(
    {
        # 联合结构约束（两系统结论的交叉面；确定性排除，永不被 LLM/提名绕过）
        "J1.delivery_mode_incompatible",  # 步绑定干预的交付 mode 与分配 mode 冲突（如 practice 需 hybrid 而分配为 human）
        "J2.mode_outside_allocation_feasible",  # 传入分配的 mode 不在其自身 feasible 集内（脏分配防御）
        "J3.inert_must_not_carry_mode",  # inert 干预携带执行方（no_action/abstain 无执行权域）
        "J4.learning_deskilling_pair",  # 学习守卫生效 × agent 交付组合（联合层防代写交叉判定）
        "J5.requires_allocation_unbacked",  # 执行面干预缺分配支撑（A-02 R4 的联合层对偶）
        # 确定性选择 / 冲突裁决
        "D1.first_legal_joint_nominee",  # 提名序内第一个联合合法者入选
        "D2.no_legal_joint_nominee_no_action",  # 无联合合法提名 → no_action 确定性出口
        "D3.conflict_allocation_precedence",  # 冲突裁决：分配事实优先，干预让位（归因随 exclusions）
        "D4.delivery_reallocation_applied",  # 交付再分配生效（X-02 以交付锚定因子重判，守卫恒同）
        # 显式用户意图（联合面：意图驱动结果时随行归因）
        "X1.explicit_user_request_priority",
        # 降级
        "E1.degraded_to_rule_default",
    }
)

#: 联合决策产层（A-02/X-02 同款语义）。
JOINT_LAYERS: frozenset[str] = frozenset({"rule", "semantic", "semantic_fallback", "error_degraded"})

#: 步绑定干预：交付 = 步骤执行本身 → mode 必须落在允许交付集内。
#: 语义判据（逐项可评审）：
#: - delegate/execute：任务交 agent 执行 → agent（=目录 allocation_modes，import 互检）；
#: - co_execute：人机协作（agent 备/用户核心/agent 校）→ hybrid（=目录）；
#: - practice：agent 备练 + 用户自己练（获得能力是干预本体）→ hybrid——
#:   纯 agent = 代写矛盾（X-02 G1 同向），纯 human = 无准备面（llm_generate 无载体）；
#: - review：agent 批改用户产出 / 人机共评 → {agent, hybrid}；用户独自自评不是
#:   本干预（无系统行为）；
#: - rescope/split/schedule：计划结构变更经用户确认（A-01 L2 接线先例
#:   execution_mode=HYBRID；plan_adjust 走确认管道）→ hybrid。
#: 不在此表 = 系统面干预（clarify/explain/retrieve/reflect/connect_peer/pause/
#: remind）：由系统面交付，不绑定任务步执行权（提醒/澄清与任务谁执行正交）。
JOINT_STEP_BOUND_DELIVERY_MODES: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "delegate": frozenset({"agent"}),
        "execute": frozenset({"agent"}),
        "co_execute": frozenset({"hybrid"}),
        "practice": frozenset({"hybrid"}),
        "review": frozenset({"agent", "hybrid"}),
        "rescope": frozenset({"hybrid"}),
        "split": frozenset({"hybrid"}),
        "schedule": frozenset({"hybrid"}),
    }
)

_ALLOCATION_REASONS_EXPLICIT = frozenset(
    {"X1.explicit_self_request", "X2.explicit_delegate_request"}
)


class JointDecisionError(RuntimeError):
    """联合词表与相邻真源失配（import 时 fail-fast，拼写漂移不可能存活）。"""


def _validate_joint_vocabularies() -> None:
    unknown = set(JOINT_STEP_BOUND_DELIVERY_MODES) - set(AURORA_INTERVENTION_TYPES)
    if unknown:
        raise JointDecisionError(f"delivery table has non-catalog interventions: {sorted(unknown)}")
    for name, modes in JOINT_STEP_BOUND_DELIVERY_MODES.items():
        if not modes or not modes <= {"human", "agent", "hybrid"}:
            raise JointDecisionError(f"{name}: delivery modes must be a non-empty subset of ExecutionMode")
        item = INTERVENTION_CATALOG[name]
        if item.is_inert:
            raise JointDecisionError(f"{name}: inert intervention cannot be step-bound")
        if item.requires_allocation and modes != item.allocation_modes:
            # requires_allocation 三项的交付集必须精确等于 A-02 目录 allocation_modes
            # （目录是冻结真源；本表漂移即 import 红）。
            raise JointDecisionError(
                f"{name}: delivery modes {sorted(modes)} != catalog allocation_modes "
                f"{sorted(item.allocation_modes)}"
            )


_validate_joint_vocabularies()


# ---------------------------------------------------------------------------
# 输出形状
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JointExclusion:
    """一条联合排除：对象 + 联合码 + 双系统归因（冲突如何落锤的可审计记录）。"""

    target: str
    reason: str  # JOINT_REASONS 成员（联合面）
    allocation_mode: str | None = None  # 冲突时的分配 mode（X-02 事实）
    allocation_why: tuple[str, ...] = ()  # 冲突时的 X-02 why（归因）
    policy_reasons: tuple[str, ...] = ()  # A-02 面已有的剔除码（上下文）

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "reason": self.reason,
            "allocation_mode": self.allocation_mode,
            "allocation_why": list(self.allocation_why),
            "policy_reasons": list(self.policy_reasons),
        }


@dataclass(frozen=True)
class JointDecision:
    """一次联合决策：intervention + mode + cognitive ownership + 双系统归因。

    - ``selected``：恒为封闭目录成员；联合无合法提名时为 ``no_action``；
    - ``mode``：inert → None；步绑定 → 分配 mode（D4 再分配后为交付分配）；
      系统面 → 目录标称镜像（无 allocation_ref 绑定）；
    - ``cognitive_ownership``：X-02 ``recommended_cognitive_ownership`` 镜像
      （X-02 构造保证永不落 X-01 F5 矛盾集；无分配事实时 None）；
    - ``allocation_ref``：联合记录面恒 None（不携带占位串）；步绑定 actionable
      干预的真实 ``decision://alloc_<id>`` 支撑引用由 ``build_joint_contract``
      在契约面回填并硬校验（P3-8：镜像值必须有分配支撑）；系统面/inert 同样
      为 None（A-01 边界）；
    - ``occurrence_id``：本次发生键（uuid；P3-4——decision_id 是内容寻址，
      跨 occurrence 复用同号，episode 关联不得拿 decision_id 当唯一发生键）；
    - ``joint_feasible_pairs``：联合可行 (intervention, mode) 集（语义层硬边界）。
    """

    selected: str
    mode: str | None
    cognitive_ownership: str | None
    why: tuple[str, ...]  # JOINT_REASONS 成员，保序
    joint_feasible_pairs: tuple[tuple[str, str | None], ...]
    exclusions: tuple[JointExclusion, ...]
    policy_evaluation: InterventionPolicyEvaluation
    allocation: AllocationDecision | None
    allocation_ref: str | None
    task_allocation: AllocationDecision | None  # D4 时的原始任务步分配（对照保留）
    requires_human_approval: bool
    requires_user_authored_evidence: bool
    layer: str = "rule"
    semantic_eligible: bool = False
    occurrence_id: str = field(default_factory=lambda: str(uuid4()))
    annotations: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", MappingProxyType(dict(self.annotations)))

    @property
    def is_step_bound(self) -> bool:
        return self.selected in JOINT_STEP_BOUND_DELIVERY_MODES

    def to_dict(self) -> dict[str, Any]:
        """结构化决策记录（M-07/X-05 审计同构：版本 + 双系统 why + 发生键随行）。"""
        return {
            "schema_version": JOINT_DECISION_VERSION,
            "occurrence_id": self.occurrence_id,
            "selected": self.selected,
            "mode": self.mode,
            "cognitive_ownership": self.cognitive_ownership,
            "why": list(self.why),
            "joint_feasible_pairs": [
                {"intervention": i, "mode": m} for i, m in self.joint_feasible_pairs
            ],
            "exclusions": [entry.to_dict() for entry in self.exclusions],
            "allocation": None if self.allocation is None else self.allocation.to_dict(),
            "allocation_policy_version": None if self.allocation is None else ALLOCATION_POLICY_VERSION,
            "allocation_ref": self.allocation_ref,
            "task_allocation": None if self.task_allocation is None else self.task_allocation.to_dict(),
            "requires_human_approval": self.requires_human_approval,
            "requires_user_authored_evidence": self.requires_user_authored_evidence,
            "intervention_policy_version": INTERVENTION_POLICY_VERSION,
            "layer": self.layer,
            "semantic_eligible": self.semantic_eligible,
            "annotations": dict(self.annotations),
        }


# ---------------------------------------------------------------------------
# 分配事实的防御性读取（X-02 是权威；此处只做形状校验，不重算）
# ---------------------------------------------------------------------------


def _allocation_mode_of(allocation: Any) -> str | None:
    if allocation is None:
        return None
    mode = getattr(allocation, "mode", None)
    if isinstance(mode, str) and mode in {"human", "agent", "hybrid"}:
        return mode
    return None


def _allocation_feasible_of(allocation: Any) -> tuple[str, ...]:
    raw = getattr(allocation, "feasible_modes", ()) or ()
    return tuple(m for m in raw if isinstance(m, str) and m in {"human", "agent", "hybrid"})


def _allocation_learning_guard(allocation: Any) -> bool:
    annotations = getattr(allocation, "annotations", None) or {}
    try:
        return bool(annotations.get("learning_guard", False))
    except AttributeError:
        return False


# ---------------------------------------------------------------------------
# 联合规则核心（纯函数）
# ---------------------------------------------------------------------------


def _pair_guard_reasons(
    intervention: str,
    mode: str | None,
    allocation: AllocationDecision | None,
) -> tuple[str, ...]:
    """单 (intervention, mode) 对的联合结构约束码（保序 J1..J5；纯表驱动）。"""
    item = INTERVENTION_CATALOG[intervention]
    reasons: list[str] = []
    if item.is_inert:
        if mode is not None:
            reasons.append("J3.inert_must_not_carry_mode")
        return tuple(reasons)
    if item.requires_allocation and mode is None:
        # A-02 R4 已在 policy 面剔除；联合层对偶防御（语义通道/手工构造路径）。
        reasons.append("J5.requires_allocation_unbacked")
        return tuple(reasons)
    if intervention in JOINT_STEP_BOUND_DELIVERY_MODES:
        assert mode is not None
        if mode not in JOINT_STEP_BOUND_DELIVERY_MODES[intervention]:
            reasons.append("J1.delivery_mode_incompatible")
        if allocation is not None and mode not in _allocation_feasible_of(allocation):
            reasons.append("J2.mode_outside_allocation_feasible")
        if allocation is not None and _allocation_learning_guard(allocation) and mode == "agent":
            # X-02 G1 交叉校验：学习守卫下 agent 交付（X-02 语义层改 mode 后的
            # 组合、或手工脏分配）在联合面确定性排除——防代写是联合不变式。
            reasons.append("J4.learning_deskilling_pair")
    return tuple(reasons)


def _joint_mode_for(intervention: str, allocation: AllocationDecision | None) -> str | None:
    """联合 mode 镜像：inert → None；步绑定 → 分配 mode；系统面 → 目录标称。"""
    item = INTERVENTION_CATALOG[intervention]
    if item.is_inert:
        return None
    if intervention in JOINT_STEP_BOUND_DELIVERY_MODES:
        return _allocation_mode_of(allocation)
    return item.nominal_execution_mode


def _no_allocation_decision() -> AllocationDecision:
    """缺分配事实时的保守缺省（X-02 R0 灰区：hybrid + insufficient——对话域控制
    决策不强制分配前提，A-01 L2 接线先例同款；步绑定执行面干预仍被 A-02 R4/
    J5 挡在门外）。"""
    return decide_allocation(AllocationFactors())


def _build_joint_decision(
    policy_evaluation: InterventionPolicyEvaluation,
    allocation: AllocationDecision | None,
    *,
    task_allocation: AllocationDecision | None = None,
    reallocated: bool = False,
) -> JointDecision:
    mode_of = _allocation_mode_of(allocation)
    feasible_pairs: list[tuple[str, str | None]] = []
    exclusions: list[JointExclusion] = []
    allocation_why = tuple(getattr(allocation, "why", ()) or ()) if allocation is not None else ()

    for name in policy_evaluation.feasible_interventions:
        pair_mode = _joint_mode_for(name, allocation)
        pair_reasons = _pair_guard_reasons(name, pair_mode, allocation)
        if pair_reasons:
            policy_reasons = tuple(
                reason for target, reason in policy_evaluation.exclusions if target == name
            )
            exclusions.append(
                JointExclusion(
                    target=name,
                    reason=pair_reasons[0],
                    allocation_mode=mode_of,
                    allocation_why=allocation_why,
                    policy_reasons=policy_reasons,
                )
            )
        else:
            feasible_pairs.append((name, pair_mode))

    feasible_by_name = {name for name, _ in feasible_pairs}
    selected: str | None = None
    for nominee in policy_evaluation.annotations.get("nominated", ()) or ():
        if isinstance(nominee, str) and nominee in feasible_by_name:
            selected = nominee
            break

    why: list[str] = []
    if selected is not None:
        why.append("D1.first_legal_joint_nominee")
    else:
        selected = "no_action"
        why.append("D2.no_legal_joint_nominee_no_action")
        # 冲突归因：存在 policy-可行但联合不可行的提名 → 分配事实优先的确定性裁决
        conflicted = [
            entry.target
            for entry in exclusions
            if entry.target in set(policy_evaluation.annotations.get("nominated", ()) or ())
        ]
        if conflicted:
            why.append("D3.conflict_allocation_precedence")
        if policy_evaluation.no_action_reason is None:
            # A-02 层选中了非 inert 干预、被联合层（J 码）降为 no_action 时，
            # 评估镜像缺 inert 原因——补词表内缺省（精确归因在 joint.why +
            # exclusions 的 J 码/allocation_why；不扩 A-01 冻结词表）。
            policy_evaluation = replace(
                policy_evaluation, no_action_reason="no_matching_pattern"
            )
    if reallocated:
        why.append("D4.delivery_reallocation_applied")
    if allocation is not None and any(code in allocation_why for code in _ALLOCATION_REASONS_EXPLICIT):
        # 卡面 Work 3：用户显式 delegation/keep-for-me 驱动了分配 → 联合面随行归因
        why.append("X1.explicit_user_request_priority")

    item = INTERVENTION_CATALOG[selected]
    final_mode = _joint_mode_for(selected, allocation)
    if not item.is_inert and selected in JOINT_STEP_BOUND_DELIVERY_MODES:
        pair_check = _pair_guard_reasons(selected, final_mode, allocation)
        if pair_check:  # 不可达防御：selected 来自 feasible_pairs，必过对约束
            selected = "no_action"
            final_mode = None
            why = ["E1.degraded_to_rule_default"]

    no_action_mode_ok = selected == "no_action" and final_mode is None
    semantic_eligible = (
        selected == "no_action"
        and any(not INTERVENTION_CATALOG[name].is_inert for name, _ in feasible_pairs)
        and no_action_mode_ok
    )

    allocation_ref: str | None = None
    # P3-8：步绑定 actionable 干预的镜像值必须有分配支撑——本字段在联合记录面
    # 恒为 None（不得泄漏占位串），真实 ``decision://alloc_<id>`` 引用由
    # ``build_joint_contract(allocation_decision_id=...)`` 在契约面回填（构造门
    # 强制步绑定必须传入 allocation_decision_id）。

    annotations: dict[str, Any] = {
        "nominated": tuple(policy_evaluation.annotations.get("nominated", ()) or ()),
        "allocation_why": list(allocation_why),
        "policy_why": list(policy_evaluation.why),
        "policy_exclusions": [
            {"target": target, "reason": reason} for target, reason in policy_evaluation.exclusions
        ],
        "allocation_layer": getattr(allocation, "layer", None) if allocation is not None else None,
    }

    return JointDecision(
        selected=selected,
        mode=final_mode,
        cognitive_ownership=(
            getattr(allocation, "recommended_cognitive_ownership", None) if allocation is not None else None
        ),
        why=tuple(dict.fromkeys(why)),
        joint_feasible_pairs=tuple(feasible_pairs),
        exclusions=tuple(exclusions),
        policy_evaluation=policy_evaluation,
        allocation=allocation,
        allocation_ref=allocation_ref,
        task_allocation=task_allocation,
        requires_human_approval=bool(getattr(allocation, "requires_human_approval", False))
        if allocation is not None
        else False,
        requires_user_authored_evidence=bool(getattr(allocation, "requires_user_authored_evidence", False))
        if allocation is not None
        else False,
        layer=policy_evaluation.layer if policy_evaluation.layer in JOINT_LAYERS else "rule",
        semantic_eligible=semantic_eligible,
        annotations=annotations,
    )


def decide_joint(
    intervention_factors: InterventionPolicyFactors | Mapping[str, Any] | None,
    allocation: AllocationDecision | None,
    *,
    inert_reason: str | None = None,
) -> JointDecision:
    """单步联合决策核心：干预因子 + 分配事实 → 联合决策（纯函数，NEVER raises）。

    内部异常降级 no_action + ``E1.degraded_to_rule_default``（韧性契约）。裁决序、
    冲突归因、联合可行集见模块 docstring；对抗面（两系统结论冲突）由
    ``D3.conflict_allocation_precedence`` + ``exclusions`` 归因钉死。
    """
    try:
        factors = InterventionPolicyFactors.coerce(intervention_factors)
        if inert_reason is not None:
            factors = replace(factors, inert_reason=inert_reason)
        effective_allocation = allocation if allocation is not None else _no_allocation_decision()
        # 分配 mode 是 A-02 的输入事实（R4/R5 据此先行剔除执行面干预）。
        policy = evaluate_intervention_policy(
            replace(factors, allocation_mode=_allocation_mode_of(effective_allocation))
        )
        return _build_joint_decision(policy, effective_allocation)
    except Exception as exc:  # noqa: BLE001 — resilience contract
        logger.warning("Joint decision internal error, degrading to no_action: {}", exc)
        fallback_policy = evaluate_intervention_policy(InterventionPolicyFactors())
        return JointDecision(
            selected="no_action",
            mode=None,
            cognitive_ownership=None,
            why=("E1.degraded_to_rule_default",),
            joint_feasible_pairs=(("abstain", None), ("no_action", None)),
            exclusions=(),
            policy_evaluation=fallback_policy,
            allocation=None,
            allocation_ref=None,
            task_allocation=None,
            requires_human_approval=False,
            requires_user_authored_evidence=False,
            layer="error_degraded",
            annotations={"degraded": True},
        )


# ---------------------------------------------------------------------------
# 交付再分配（D4）：X-02 以交付锚定因子重判（守卫恒同，非第二套 rubric）
# ---------------------------------------------------------------------------


#: 交付锚定投影：任务步因子 → 干预交付步因子。只改「锚定的步骤语义」维度
#: （ownership / tool_advantage / task_ref），学习、风险、隐私、具身、置信、
#: 显式意图、偏好**原样保留**——X-02 的全部硬守卫输入不变，守卫结论恒同；
#: 改变的只是选择层把「这一步」认成什么（练习准备是高工具优势的机械准备面）。
def derive_delivery_factors(
    task_factors: AllocationFactors | Mapping[str, Any] | None,
    intervention: str,
) -> AllocationFactors:
    base = AllocationFactors.coerce(task_factors)
    raw: dict[str, Any] = {
        "task_ref": base.task_ref,
        "task_type": base.task_type,
        "task_summary": base.task_summary,
        "learning_goal": base.learning_goal,
        "cognitive_ownership": base.cognitive_ownership,
        "tool_advantage": base.tool_advantage,
        "risk_class": base.risk_class,
        "reversible": base.reversible,
        "explicit_intent": base.explicit_intent,
        "embodiment_required": base.embodiment_required,
        "privacy": base.privacy,
        "confidence": base.confidence,
        "time_pressure": base.time_pressure,
        "user_preference": base.user_preference,
    }
    item = INTERVENTION_CATALOG.get(intervention)
    if item is not None and "llm_generate" in item.capability_requirements:
        # practice/review/explain 族：交付步是「系统准备针对性材料」——机械准备面
        # 工具优势为 high（能力需求即优势声明）；学习信号保留（G1 照常剔除 agent）。
        raw["tool_advantage"] = "high"
    if intervention in {"rescope", "split", "schedule", "co_execute"}:
        # 计划结构/协作族：交付步是「人机共同调整」——ownership 锚 shared
        # （学习信号保留：user_core 仍按学习守卫归位）。
        if base.cognitive_ownership != "user_core":
            raw["cognitive_ownership"] = "shared"
    return AllocationFactors.coerce(raw)


def decide_joint_two_step(
    intervention_factors: InterventionPolicyFactors | Mapping[str, Any] | None,
    task_factors: AllocationFactors | Mapping[str, Any] | None,
    *,
    task_allocation: AllocationDecision | None = None,
    decide_allocation_fn: Callable[[Any], AllocationDecision] = decide_allocation,
    inert_reason: str | None = None,
) -> JointDecision:
    """两步联合：任务步分配 → 冲突可救则交付再分配（D4）→ 联合决策。

    裁决序落锤点（对抗面「A-02 说 practice、X-02 说 human-only」）：
    1. 以任务步分配跑联合（practice J1 排除 → D3 归因）；
    2. 若被提名的步绑定干预存在交付兼容 mode 且该 mode ∈ 任务分配可行集，
       以 ``derive_delivery_factors`` 交付锚定因子重跑 X-02（守卫输入不变）；
    3. 再分配 mode ∈ 交付集 → 采用（D4，allocation_ref 指向交付分配；
       task_allocation 对照保留）；否则维持第 1 步结果（D3，分配优先）。
    纯函数（``decide_allocation_fn`` 可注入；生产用 X-02 真核心）。
    """
    try:
        allocation = (
            task_allocation
            if task_allocation is not None
            else decide_allocation_fn(AllocationFactors.coerce(task_factors))
        )
        first = decide_joint(intervention_factors, allocation, inert_reason=inert_reason)

        if first.selected == "no_action" and "D3.conflict_allocation_precedence" in first.why:
            nominated = tuple(first.annotations.get("nominated", ()) or ())
            conflicted_targets = [
                entry.target
                for entry in first.exclusions
                if entry.reason == "J1.delivery_mode_incompatible" and entry.target in set(nominated)
            ]
            original_feasible = set(_allocation_feasible_of(allocation))
            for target in conflicted_targets:
                delivery_modes = JOINT_STEP_BOUND_DELIVERY_MODES.get(target, frozenset())
                rescue_modes = delivery_modes & original_feasible
                if not rescue_modes:
                    continue  # 分配可行集本身不含交付 mode → 无可救（restricted/G1 等守卫所致）
                delivery_allocation = decide_allocation_fn(
                    derive_delivery_factors(task_factors, target)
                )
                delivery_mode = _allocation_mode_of(delivery_allocation)
                # 守卫恒同断言的机制化形态：再分配结果必须仍以原可行集为界
                # （derive 只动选择层维度；若越界说明上游守卫因子被污染，弃用）。
                if delivery_mode in rescue_modes:
                    rescued = decide_joint(intervention_factors, delivery_allocation, inert_reason=inert_reason)
                    if rescued.selected == target:
                        # why 时序序：冲突（D3）→ 再分配生效（D4）→ 终选与随行
                        # 归因（rescued.why：D1/X1）。rescued 自身不含 D3（D3 仅在
                        # no_action 支路产生），dict.fromkeys 兜底去重。
                        return replace(
                            rescued,
                            task_allocation=allocation,
                            why=tuple(
                                dict.fromkeys(
                                    (
                                        "D3.conflict_allocation_precedence",
                                        "D4.delivery_reallocation_applied",
                                        *rescued.why,
                                    )
                                )
                            ),
                        )
        return first
    except Exception as exc:  # noqa: BLE001 — resilience contract
        logger.warning("Joint two-step decision error, degrading: {}", exc)
        return decide_joint(intervention_factors, None)


# ---------------------------------------------------------------------------
# 契约投影（A-01 冻结形状）+ P3-7/P3-8 硬化
# ---------------------------------------------------------------------------


def allocation_decision_ref(allocation_decision_id: str) -> str:
    """X-02 分配决策的 decision:// 引用（P3-8 allocation_ref 回填）。"""
    return f"decision://{allocation_decision_id}"


def build_joint_contract(
    joint: JointDecision,
    user_id: UUID,
    *,
    cognition_tier: str,
    allocation_decision_id: str | None = None,
    rationale_summary: str | None = None,
    evidence_refs: tuple[str, ...] = (),
    trigger_point: str | None = None,
    input_context_hash: str | None = None,
    clarifying_question: str | None = None,
    governance_mode: str = "live",
    created_at: Any = None,
) -> tuple[AuroraDecisionContract | None, tuple[str, ...]]:
    """联合决策 → ``AuroraDecisionContract``（构造门 + P3-8 硬化）。

    与 A-02 ``build_decision_contract`` 同款构造门（violations 非空 →
    ``(None, violations)``，绝不静默产出非法契约），追加联合面硬化：
    - 步绑定 actionable 干预**必须**携带 allocation_ref（镜像值必须有分配支撑，
      P3-8）；requires_allocation 三项缺 ref 直接违规；
    - allocation_ref 存在时回填真实 X-02 ``decision://alloc_<id>`` 并跑
      ``enforce_allocation_consistency`` 硬校验。
    """
    violations: list[str] = []
    if joint.selected not in INTERVENTION_CATALOG:
        return None, (f"selected {joint.selected!r} not in intervention catalog",)
    if cognition_tier not in AURORA_COGNITION_TIERS:
        return None, (f"cognition_tier {cognition_tier!r} out of vocabulary",)
    if governance_mode not in AURORA_GOVERNANCE_MODES:
        return None, (f"governance_mode {governance_mode!r} out of vocabulary",)
    for ref in evidence_refs:
        if ref.split("://", 1)[0] not in AURORA_DECISION_REF_SCHEMES:
            violations.append(f"evidence ref has unknown or missing scheme: {ref!r}")

    item = INTERVENTION_CATALOG[joint.selected]
    step_bound = joint.selected in JOINT_STEP_BOUND_DELIVERY_MODES and not item.is_inert
    if step_bound:
        if not allocation_decision_id:
            violations.append(
                f"step-bound intervention {joint.selected!r} requires allocation_decision_id (P3-8)"
            )
        elif joint.allocation is None or _allocation_mode_of(joint.allocation) is None:
            violations.append(
                f"step-bound intervention {joint.selected!r} lacks a mode-carrying allocation backing"
            )
        elif joint.mode != _allocation_mode_of(joint.allocation):
            violations.append(
                f"joint mode {joint.mode!r} != allocation mode {_allocation_mode_of(joint.allocation)!r}"
            )

    mode: ExecutionMode | None = None
    if not item.is_inert:
        if joint.mode is None:
            violations.append(f"actionable intervention {joint.selected!r} lacks mode")
        else:
            mode = ExecutionMode(joint.mode)
    carried_question = (clarifying_question or "").strip() or None
    if joint.selected == "clarify" and not carried_question:
        violations.append("clarify intervention must carry clarifying_question")
    if item.is_inert and joint.policy_evaluation.no_action_reason is None:
        violations.append(f"inert intervention {joint.selected!r} lacks no_action_reason")
    if violations:
        return None, tuple(violations)

    rationale = (rationale_summary or "").strip() or f"{item.name}: {item.expected_outcome}"
    contract = AuroraDecisionContract(
        user_id=user_id,
        intervention_type=item.name,
        rationale_summary=rationale,
        cognition_tier=cognition_tier,
        execution_mode=mode,
        governance_mode=governance_mode,
        trigger_point=trigger_point,
        input_context_hash=input_context_hash,
        evidence_refs=tuple(evidence_refs),
        clarifying_question=carried_question if item.name == "clarify" else None,
        allocation_ref=allocation_decision_ref(allocation_decision_id)
        if step_bound and allocation_decision_id
        else None,
        no_action_reason=joint.policy_evaluation.no_action_reason if item.is_inert else None,
        annotations={
            "joint_decision_version": JOINT_DECISION_VERSION,
            "policy_version": joint.policy_evaluation.policy_version,
            "catalog_fingerprint": joint.policy_evaluation.catalog_fingerprint,
            "policy_why": list(joint.policy_evaluation.why),
            "joint_why": list(joint.why),
            "allocation_why": list(joint.annotations.get("allocation_why", ())),
            "occurrence_id": joint.occurrence_id,
            "reallocation_applied": "D4.delivery_reallocation_applied" in joint.why,
        },
        created_at=created_at,
    )
    contract_violations = contract.validate()
    if contract_violations:
        return None, contract_violations
    if step_bound and joint.allocation is not None:
        # P3-8 硬校验：ref 已指向分配 → 镜像必须严格一致（A-01 宽松版的联合面硬化）。
        consistency = enforce_allocation_consistency(contract, joint.allocation)
        if consistency:
            return None, consistency
    return contract, ()


def enforce_allocation_consistency(
    contract: AuroraDecisionContract, allocation: Any
) -> tuple[str, ...]:
    """P3-8 硬化：比 A-01 ``consistent_with_allocation`` 更严的联合面校验。

    - allocation_ref 已指向分配决策时：分配缺 mode → 违规（不再静默放行——
      「缺 mode 的分配」不是合法的支撑事实）；
    - 镜像 mode 与分配 mode 不一致 → 违规（A-01 同款，此处为硬规则）；
    - 学习守卫生效 × agent 镜像 → 违规（J4 的读侧对偶：X-02 语义层改 mode 或
      手工构造的脏契约在读门被拦）。
    无 allocation_ref 的纯对话域决策返回空（A-01 边界不变）。
    """
    if contract.allocation_ref is None:
        return ()
    if contract.execution_mode is None:
        return ()  # inert 不携带执行方：无镜像可言（J3 在构造面拦）
    allocation_mode = getattr(allocation, "mode", None)
    if allocation_mode is None:
        return (
            f"allocation_ref {contract.allocation_ref!r} backed by allocation without a mode (P3-8 hard rule)",
        )
    if allocation_mode != contract.execution_mode.value:
        return (
            f"execution_mode {contract.execution_mode.value!r} != allocation mode {allocation_mode!r}",
        )
    if _allocation_learning_guard(allocation) and contract.execution_mode.value == "agent":
        return ("learning guard active: agent execution_mode contradicts anti-deskilling (J4 read-side)",)
    return ()


def read_decision_contract(
    payload: Mapping[str, Any] | None,
    *,
    allocation_payload: Mapping[str, Any] | None = None,
) -> tuple[AuroraDecisionContract | None, tuple[str, ...]]:
    """统一读门（P3-7 机制化 + shadow 治理门）。

    消费方读取契约载荷的唯一受控入口：
    1. ``aurora_decision_from_dict`` 重构（脏载荷 → None + 违规，不 raise）；
    2. ``validate()``（P3-7：词表封闭是 validate 门——读侧必须机制化调用，
       violations 非空 → 拒收）；
    3. ``enforce_allocation_consistency``（P3-8：allocation_ref 支撑硬校验；
       allocation_payload 提供时启用，缺省跳过——读侧不猜分配内容）；
    4. **shadow 治理门**：``governance_mode != "live"`` → 拒收应用
       （shadow 决策只记录对比，不得作用于用户可见行为——返回专门违规码，
       调用方可与「数据坏」区分观测）。
    """
    if not isinstance(payload, Mapping):
        return None, ("payload is not a mapping",)
    contract = aurora_decision_from_dict(payload)
    if contract is None:
        return None, ("payload failed contract reconstruction",)
    violations = list(contract.validate())
    if not violations and allocation_payload is not None:
        violations.extend(enforce_allocation_consistency(contract, _coerce_allocation_like(allocation_payload)))
    if not violations and contract.governance_mode != "live":
        return None, (f"governance_mode={contract.governance_mode!r} decisions are recorded but never applied",)
    if violations:
        return None, tuple(violations)
    return contract, ()


def _coerce_allocation_like(payload: Mapping[str, Any]) -> Any:
    """读门的分配载荷最小形状适配（不重算 X-02，只读 mode/learning_guard）。"""

    class _AllocationLike:
        __slots__ = ("mode", "annotations")

        def __init__(self, mode: str | None, learning: bool) -> None:
            self.mode = mode
            self.annotations = {"learning_guard": learning}

    mode = payload.get("mode")
    annotations = payload.get("annotations") or {}
    learning = bool(annotations.get("learning_guard", False)) if isinstance(annotations, Mapping) else False
    return _AllocationLike(mode if isinstance(mode, str) else None, learning)


# ---------------------------------------------------------------------------
# 决策事件（复用 D-01 既有名 decision.recorded；零新名）
# ---------------------------------------------------------------------------


def build_joint_decision_event_metadata(
    *,
    user_id: Any,
    joint: JointDecision,
    contract: AuroraDecisionContract | None = None,
    source: EventSource | str = EventSource.SERVER_SERVICE,
    service: str = "aurora_joint_decision",
    correlation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """构造联合决策事件的 outbox metadata（X-02 ``build_allocation_event_metadata``
    同构：shared-fields 契约 + 决策记录本体经 extra 携带；落 outbox 属消费方
    X-05）。事件名复用 ``decision.recorded``（registry 既有 reserved 名）。
    """
    corr: dict[str, Any] = dict(correlation or {})
    decision_id = contract.decision_id_or_compute() if contract is not None else None
    extra: dict[str, Any] = {
        "joint_decision": joint.to_dict(),
        "occurrence_id": joint.occurrence_id,
    }
    if decision_id:
        extra["decision_id"] = decision_id
    return build_event_metadata(
        user_id=user_id,
        source=source,
        service=service,
        event_name=JOINT_DECISION_EVENT_NAME,
        aggregate_type="decision_record",
        aggregate_id=joint.occurrence_id,
        correlation=corr,
        extra=extra,
    )


# ---------------------------------------------------------------------------
# 有状态包装：语义层（可选 LLM 参数化通道；默认关；联合合法集内）
# ---------------------------------------------------------------------------


class JointDecisionEngine:
    """Stateful 包装：联合核心 + 可选语义精化（LLM 只在联合合法集内，默认关）。

    语义层纪律（A-02 ``InterventionPolicyEngine`` / X-02 ``ActionAllocationPolicy``
    同款）：仅对规则层标记 ``semantic_eligible`` 的开放选择生效；LLM 的干预提议
    必须落在**联合可行集**内（(intervention, mode) 对级校验——比 A-02 的
    feasible set 更紧：联合面排除的干预即使 A-02 可行也不可选）；mode 永不由
    LLM 决定（X-02 权威——步绑定 mode 由分配绑定，系统面 mode 由目录标称绑定）。
    任何失败降级规则缺省。

    settings 化（A-02 receipt §4.6，X-02 同款键位）：通道开关
    ``SPARKLE_JOINT_SEMANTIC_ENABLED``（默认 False——收紧零成本）+ model/
    timeout/max_per_minute。构造器注入优先；未注入时 ``_semantic_refine``
    惰性解析 settings + llm_service（开关关则永不触达）。
    """

    _semantic_failures: int = 0
    _semantic_open_until: float = 0.0
    _semantic_calls_this_window: int = 0
    _semantic_window_started_at: float = 0.0

    SEMANTIC_BREAKER_THRESHOLD = 3
    SEMANTIC_BREAKER_COOLDOWN_SECONDS = 300.0

    def __init__(
        self,
        *,
        semantic_llm: Any | None = None,
        semantic_enabled: bool = False,
        semantic_timeout_seconds: float = 5.0,
        semantic_max_per_minute: int = 10,
        now_fn=time.monotonic,
    ):
        self._semantic_llm = semantic_llm
        self._semantic_enabled = semantic_enabled
        self._semantic_timeout = semantic_timeout_seconds
        self._semantic_max_per_minute = semantic_max_per_minute
        self._now_fn = now_fn

    @classmethod
    def _reset_breaker(cls) -> None:
        """测试钩子：清零熔断/限频状态。"""
        cls._semantic_failures = 0
        cls._semantic_open_until = 0.0
        cls._semantic_calls_this_window = 0
        cls._semantic_window_started_at = 0.0

    async def evaluate(
        self,
        intervention_factors: InterventionPolicyFactors | Mapping[str, Any] | None,
        allocation: AllocationDecision | None,
        *,
        inert_reason: str | None = None,
    ) -> JointDecision:
        """全量评估：联合规则核心 + 可选语义精化。NEVER raises。"""
        rule_decision = decide_joint(intervention_factors, allocation, inert_reason=inert_reason)
        if not (self._semantic_enabled and rule_decision.semantic_eligible):
            return rule_decision
        try:
            refined = await self._semantic_refine(rule_decision)
        except Exception as exc:  # noqa: BLE001 — resilience contract
            logger.warning("Joint semantic layer error; rule default kept: {}", exc)
            return rule_decision
        return refined if refined is not None else rule_decision

    def _resolve_semantic_llm(self) -> Any | None:
        """语义 LLM 解析：构造器注入优先；否则惰性读 settings + llm_service。

        通道默认关（``SPARKLE_JOINT_SEMANTIC_ENABLED=False``）——本方法只在
        开关已开且规则层标记 semantic_eligible 时被触达。
        """
        if self._semantic_llm is not None:
            return self._semantic_llm
        try:
            from app.config import settings

            if not getattr(settings, "SPARKLE_JOINT_SEMANTIC_ENABLED", False):
                return None

            from app.services.llm_service import llm_service

            model = str(getattr(settings, "SPARKLE_JOINT_SEMANTIC_MODEL", "qwen3.8-flash"))

            async def _llm(prompt: str):  # pragma: no cover — settings 开启路径
                return await llm_service.chat_json(
                    [{"role": "system", "content": prompt}],
                    model=model,
                    max_tokens=120,
                )

            return _llm
        except Exception as exc:  # noqa: BLE001 — resilience contract
            logger.debug("Joint semantic LLM unavailable: {}", exc)
            return None

    async def _semantic_refine(self, rule_decision: JointDecision) -> JointDecision | None:
        """LLM 开放选择精化：提议干预必须落在联合可行对集内（代码强制）。"""
        import asyncio
        import json

        llm = self._resolve_semantic_llm()
        if llm is None:
            return None

        now = self._now_fn()
        if now < JointDecisionEngine._semantic_open_until:
            return None
        if now - JointDecisionEngine._semantic_window_started_at > 60.0:
            JointDecisionEngine._semantic_window_started_at = now
            JointDecisionEngine._semantic_calls_this_window = 0
        if JointDecisionEngine._semantic_calls_this_window >= self._semantic_max_per_minute:
            return None
        JointDecisionEngine._semantic_calls_this_window += 1

        joint_feasible_names = tuple(
            dict.fromkeys(name for name, _ in rule_decision.joint_feasible_pairs if name)
        )
        prompt = (
            "你是学习系统的联合干预选择器。规则层已算出本轮合法的（干预×执行）联合集合，"
            "你只能从下列干预中选一个（其执行方式已由联合约束绑定）：\n"
            f"{', '.join(joint_feasible_names)}\n\n"
            "只输出 JSON：{\"intervention\": \"<候选之一>\", \"rationale\": \"简短理由\"}"
        )
        try:
            payload = await asyncio.wait_for(llm(prompt), timeout=self._semantic_timeout)
        except TimeoutError:
            self._breaker_record_failure()
            logger.info("Joint semantic refine timed out; rule default kept")
            return None
        except Exception as exc:
            self._breaker_record_failure()
            logger.info("Joint semantic refine failed ({}); rule default kept", exc)
            return None

        proposal = None
        try:
            if isinstance(payload, str):
                payload = json.loads(payload)
            if isinstance(payload, dict):
                proposal = payload.get("intervention")
        except Exception:
            proposal = None
        proposed = proposal.strip().lower() if isinstance(proposal, str) else None
        joint_legal = {name for name, _ in rule_decision.joint_feasible_pairs}
        if proposed not in joint_legal or proposed in {"no_action", "abstain"}:
            # 代码强制边界：LLM 不可越联合可行集（越界 → S2 拒收，不计熔断）。
            logger.info(
                "Joint semantic proposed {} outside joint-legal {}; rejected",
                proposed,
                sorted(joint_legal),
            )
            return replace(
                rule_decision,
                policy_evaluation=replace(
                    rule_decision.policy_evaluation,
                    why=tuple(
                        dict.fromkeys(
                            (*rule_decision.policy_evaluation.why, "S2.semantic_outside_feasible_rejected")
                        )
                    ),
                    layer="semantic_fallback",
                ),
                layer="semantic_fallback",
                annotations={**rule_decision.annotations, "semantic_proposed": proposed},
            )
        JointDecisionEngine._semantic_failures = 0
        for name, mode in rule_decision.joint_feasible_pairs:
            if name == proposed:
                selected_mode = mode
                break
        else:  # pragma: no cover — proposed ∈ joint_legal 保证存在
            return None
        # 语义提升后，规则层为 no_action 结局给出的裁决码（D2/D3）不再描述
        # 结果——剥离（保留在 layer=semantic + annotations.semantic_proposed 的
        # 溯源里，联合记录面 why 恒描述**当前**结局）；X1 显式意图归因随行。
        carried = tuple(
            code
            for code in rule_decision.why
            if code
            not in {
                "D2.no_legal_joint_nominee_no_action",
                "D3.conflict_allocation_precedence",
            }
        )
        return replace(
            rule_decision,
            selected=proposed,
            mode=selected_mode,
            why=("D1.first_legal_joint_nominee", *carried),
            layer="semantic",
            annotations={**rule_decision.annotations, "semantic_proposed": proposed},
        )

    def _breaker_record_failure(self) -> None:
        cls = type(self)
        cls._semantic_failures += 1
        if cls._semantic_failures >= cls.SEMANTIC_BREAKER_THRESHOLD:
            cls._semantic_open_until = self._now_fn() + cls.SEMANTIC_BREAKER_COOLDOWN_SECONDS
            logger.warning(
                "Joint semantic tier circuit opened for {}s after {} consecutive failures",
                cls.SEMANTIC_BREAKER_COOLDOWN_SECONDS,
                cls._semantic_failures,
            )
