"""A-05 · Bounded Policy Patches 契约 —— 六面白名单 + 生命周期状态机 + 版本/缓存键（纯函数层）。

AURORA_V3 §4 Bounded Plasticity 的机制化：Aurora 可以从 outcome 保存
``PolicyPatchCandidate``，但**只有白名单 policy surface 可生效，其他字段拒绝**
（fail-closed——提示词边界不是边界，A-02/X-02 已论证；本模块把「可塑性面」
也做成代码边界）。

════════════════════════════════════════════════════════════════════════
灵魂红线：白名单封闭（本卡的灵魂）
════════════════════════════════════════════════════════════════════════
1. **六面白名单封闭**（``POLICY_PATCH_SURFACES``，冻结）：granularity /
   clarification / explanation / intervention_preference / proactive_cadence /
   allocation_preference——**恰好六面**，精确集 + sha256 被契约测试双钉。
   任何 patch 请求 surface 不在集合内 → ``V1.surface_not_whitelisted``
   拒绝（fail-closed）。「改 prompt / 改代码 / 改模型参数」不是面——它们
   没有合法的 surface 名，走不到任何写路径（变异守卫：放开白名单必红）。
2. **payload 封闭**：每面有自己的键集与值域（``SURFACE_PAYLOAD_SCHEMAS``，
   冻结）。未知键 → ``V2.payload_field_unknown``；词表外值 →
   ``V3.payload_value_out_of_vocabulary``。patch 不能夹带任意字段。
3. **patch 是决策输入，不是代码**：六个面的消费契约全部是确定性投影——
   3 面进 A-02 提名重排（intervention_preference/granularity/clarification）、
   1 面进 X-02 因子（allocation_preference → ``AllocationFactors.user_preference``
   既有入参，不绕过 A-04 联合约束层）、1 面进 proactive 门因子
   （proactive_cadence）、1 面进解释参数化（explanation）。不存在任何
   「patch 生效 = 修改 prompt/代码/模型参数」路径。

════════════════════════════════════════════════════════════════════════
生命周期状态机（卡面 Work 2）
════════════════════════════════════════════════════════════════════════
``candidate → evidenced → active → expire/revoke``（+ rejected 终态）：

- ``candidate``：已提议、证据未验证（携带 evidence_refs 声明，但尚未对真源核验）；
- ``evidenced``：证据门通过——evidence_refs **对真实证据源核验**（M-06
  experience memory 投影记录 / D-05 outcome 关联行，非自报），且达到最低
  档位（≥ single_observation）。档位 ≥ repeated（AUTO_ACTIVATE_TIERS）→
  允许自动激活；single_observation → 需用户确认（confirm(若需)）；
- ``active``：生效（进入 effective 集、参与版本计算与决策输入投影）；
- ``expired``：active 且 ``now ≥ expires_at``（读时门 + 显式 sweep 双保险）；
- ``revoked``：用户纠正撤销——**即时生效**（effective 集立即排除；版本立即
  bump），审计历史（transition_history）保留；revoked 是终态，复活需新 patch
  （M-01 supersede 指针哲学：不复活行，另立后继）；
- ``rejected``：证据门确定性失败（无可解析证据 / 档位不足），终态。

迁移表（``POLICY_PATCH_TRANSITIONS``，冻结）：非法迁移 → ``T6.illegal_transition``
拒绝（状态机封闭，无自由跳转）。

════════════════════════════════════════════════════════════════════════
证据语义（真源 = M-06 / D-05，本层零重建）
════════════════════════════════════════════════════════════════════════
- evidence_refs 封闭 scheme：``memory://experience/<expmem_id>``（M-06
  ``ExperienceMemoryRecord.record_id``）与 ``decision://aurora_<32hex>``
  （A-01 内容寻址 decision_id / D-05 lifecycle 行锚）。两者均落在
  ``AURORA_DECISION_REF_SCHEMES`` 的既有 scheme 内（``memory``/``decision``），
  可直接进 A-01 契约的 evidence_refs（词表零新名）。
- **方向敏感面**（prefer/demote 族）：prefer 需 ≥1 条正向共同出现证据
  （``has_positive_association_evidence``）；demote 需 ≥1 条负向
  （``has_negative_association_evidence``，失败等价保留——M-06 红线 3）。
- 档位真源是 D-05 ``association_evidence_tier``；本层消费 M-06 记录的
  ``completeness_adjusted_strength``（FIX-31 P2-1：截断降档后的保守值），
  多条证据取梯上最高档。
- 服务层（``app/services/policy_patch_service.py``）负责对真源核验；本层
  只定义门槛常量与判定纯函数。

════════════════════════════════════════════════════════════════════════
policy version 与缓存失效（卡面 Work 3；A-01 契约/缓存既有模式）
════════════════════════════════════════════════════════════════════════
- ``compute_policy_patch_version(entries)``：active 集的内容寻址版本号
  （``polpatch_<sha256[:16]>``；空集 = ``POLICY_PATCH_EMPTY_VERSION`` 常量）。
  active 集任一变化（激活/撤销/过期）→ 版本必然变化。
- ``patch_cache_key(base_key, version)``：消费方缓存键并入版本——版本 bump
  → 键变 → **缓存不命中**（A-01 ``input_context_hash`` 同款纪律：策略版本
  是决策输入的一部分，必须进入上下文/缓存键）。
- 决策载荷归因：``policy_patch_annotations``（服务层组装）把
  ``policy_patch_version`` + 生效 patch 引用并入契约 annotations（A-01
  annotations 是自由 Mapping，extend-only，零新冻结面）。

与既有权威的关系（不重建、不清重）：
- 证据真源：M-06 ``experience_memory_projector`` + D-05 ``intervention_lifecycle``
  （本层与服务层只消费，零重聚合）；
- 干预选择：A-02 ``evaluate_intervention_policy``（patch 经提名重排进入，
  守卫/feasible set 语义不变——patch 只能改变提名**顺序**，永远不能把非法
  干预变合法）；
- 分配：X-02 ``AllocationFactors.user_preference`` 既有入参（A-04 联合约束
  层 J 码照常生效——allocation_preference 不绕过联合约束）；
- 词表 39 零新名（本卡零事件、零 outbox、零 registry 变更；审计走
  transition_history 自包含面）。

变更流程：本模块任何词表/状态机/档位语义改动需 bump
``POLICY_PATCH_SCHEMA_VERSION`` 并过两位 reviewer（A-02/D-05 同款纪律）。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence

from app.core.aurora_decision import _INERT_INTERVENTIONS, AURORA_INTERVENTION_TYPES
from app.core.intervention_lifecycle import (
    EVIDENCE_TIER_ACCUMULATED,
    EVIDENCE_TIER_INSUFFICIENT,
    EVIDENCE_TIER_REPEATED,
    EVIDENCE_TIER_SINGLE,
    GOAL_SLICE_TYPES,
    INTERVENTION_FRICTION_TAGS,
)

POLICY_PATCH_SCHEMA_VERSION = "aurora_policy_patch.v1"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展需 bump 契约版本 + 两位 reviewer）
# ---------------------------------------------------------------------------

#: 六面 patch surface 白名单（本卡灵魂；精确集 + sha256 双钉）。
POLICY_PATCH_SURFACES: frozenset[str] = frozenset(
    {
        "granularity",  # 任务粒度偏好（finer/coarser → split 族的提名重排）
        "clarification",  # 澄清行为偏好（ask_more/ask_less → clarify 的提名重排）
        "explanation",  # 解释风格偏好（examples_first/… → 回复层参数化面）
        "intervention_preference",  # 干预偏好（prefer/demote 目录成员 → 提名重排）
        "proactive_cadence",  # 主动触达节奏（minimal/reduced/increased → proactive 门因子）
        "allocation_preference",  # 执行分配偏好（prefer_agent/… → X-02 user_preference 因子）
    }
)

#: 生命周期状态（封闭）。
POLICY_PATCH_STATES: frozenset[str] = frozenset(
    {
        "candidate",  # 已提议、证据未核验
        "evidenced",  # 证据门通过（真实证据 + 档位 ≥ single_observation）
        "active",  # 生效
        "expired",  # 已过期（终态）
        "revoked",  # 用户纠正撤销（终态；即时生效 + 审计保留）
        "rejected",  # 证据门确定性失败（终态）
    }
)

#: 生命周期动作（封闭）。
POLICY_PATCH_ACTIONS: frozenset[str] = frozenset(
    {
        "admit_evidence",  # 证据门判定（candidate → evidenced/rejected）
        "auto_activate",  # 档位达标自动激活（evidenced → active）
        "confirm",  # 用户确认激活（evidenced → active；confirm(若需)）
        "revoke",  # 用户纠正撤销（candidate/evidenced/active → revoked；即时生效）
        "expire",  # 过期结算（active → expired；读时门 + 显式 sweep）
    }
)

#: 拒绝/迁移 reason codes（封闭）。前缀语义：V*=验证（fail-closed 白名单门）·
#: G*=证据门 · T*=状态迁移。
POLICY_PATCH_REASONS: frozenset[str] = frozenset(
    {
        # 白名单验证（fail-closed；本卡灵魂）
        "V1.surface_not_whitelisted",
        "V2.payload_field_unknown",
        "V3.payload_value_out_of_vocabulary",
        "V4.evidence_ref_malformed",
        "V5.scope_value_out_of_vocabulary",
        "V6.inert_intervention_not_patchable",
        "V7.provenance_not_whitelisted",
        # 证据门（真实证据，非自报）
        "G1.no_resolved_evidence",
        "G2.evidence_tier_insufficient",
        "G3.evidence_direction_mismatch",
        # 状态迁移
        "T1.evidence_admitted",
        "T2.auto_activated",
        "T3.user_confirmed_activated",
        "T4.revoked_by_user_correction",
        "T5.expired",
        "T6.illegal_transition",
    }
)

#: 每面 payload schema：键集（恰一键）与值域（封闭）。
SURFACE_PAYLOAD_SCHEMAS: Mapping[str, frozenset[str]] = {
    "granularity": frozenset({"finer", "coarser"}),
    "clarification": frozenset({"ask_more", "ask_less"}),
    "explanation": frozenset({"examples_first", "definitions_first", "step_by_step", "analogy"}),
    "intervention_preference": None,  # 值域 = A-01 目录非 inert 成员（特殊：见 _payload_schema_of）
    "proactive_cadence": frozenset({"minimal", "reduced", "increased"}),
    "allocation_preference": None,  # 值域 = X-02 USER_PREFERENCES 镜像（见下）
}

#: allocation_preference 值域：X-02 ``USER_PREFERENCES`` 的核心镜像（服务层
#: import 期断言与 X-02 精确相等——漂移即 fail-fast，D-05 spine 投影同款纪律）。
ALLOCATION_PREFERENCE_VALUES: frozenset[str] = frozenset({"prefer_agent", "prefer_human", "prefer_mixed"})

#: 每面的 payload 主语义键（intervention_preference 另携 ``direction`` 副键；
#: 其余五面恰一个语义键；未知键 = V2 拒绝）。
SURFACE_PAYLOAD_KEYS: Mapping[str, str] = {
    "granularity": "adjustment",
    "clarification": "mode",
    "explanation": "style",
    "intervention_preference": "intervention",
    "proactive_cadence": "cadence",
    "allocation_preference": "preference",
}

#: intervention_preference 的副语义键（方向；prefer/demote）。
INTENTION_DIRECTION_KEY = "direction"

#: 提名重排族：三个 surface 映射到 (目标干预, 方向) —— prefer=升序位，demote=降序位。
#: granularity: finer → 偏好更细拆分（split 升）；coarser → split 降。
#: clarification: ask_more → clarify 升；ask_less → clarify 降。
RANKING_SURFACE_TARGETS: Mapping[str, Mapping[str, tuple[str, str]]] = {
    "granularity": {"finer": ("split", "prefer"), "coarser": ("split", "demote")},
    "clarification": {"ask_more": ("clarify", "prefer"), "ask_less": ("clarify", "demote")},
}

#: 提名方向（intervention_preference payload 的 direction 键 + 值域）。
INTENTION_DIRECTIONS: frozenset[str] = frozenset({"prefer", "demote"})

#: provenance 白名单（patch 的提议来源；封闭）。
POLICY_PATCH_PROVENANCES: frozenset[str] = frozenset(
    {
        "l4_async_analysis",  # AURORA_V3 决策环 L4 后台分析（policy candidate 产地面）
        "decision_loop",  # 交互内决策环提名
        "user_action",  # 用户显式动作（确认/设置偏好入口）
    }
)

#: 自动激活档位（无需用户确认；single_observation 需 confirm(若需)）。
AUTO_ACTIVATE_TIERS: frozenset[str] = frozenset({EVIDENCE_TIER_REPEATED, EVIDENCE_TIER_ACCUMULATED})

#: 档位阶梯（顺序 = 证据强度单调不降；与 M-06 _TIER_LADDER 同构）。
_TIER_LADDER: tuple[str, ...] = (
    EVIDENCE_TIER_INSUFFICIENT,
    EVIDENCE_TIER_SINGLE,
    EVIDENCE_TIER_REPEATED,
    EVIDENCE_TIER_ACCUMULATED,
)


def highest_tier(tiers: Iterable[str]) -> str:
    """多条证据取梯上最高档（未知档位视为 insufficient——保守）。"""
    best = EVIDENCE_TIER_INSUFFICIENT
    for tier in tiers:
        value = str(tier)
        if value in _TIER_LADDER and _TIER_LADDER.index(value) > _TIER_LADDER.index(best):
            best = value
    return best


# ---------------------------------------------------------------------------
# 迁移表（冻结）
# ---------------------------------------------------------------------------

#: 合法迁移：action → {from_state: to_state}。不在表内 = T6 非法迁移。
POLICY_PATCH_TRANSITIONS: Mapping[str, Mapping[str, str]] = {
    "admit_evidence": {"candidate": "evidenced"},  # 失败分支（G 码）由 admit 函数落 rejected
    "auto_activate": {"evidenced": "active"},
    "confirm": {"evidenced": "active"},
    "revoke": {"candidate": "revoked", "evidenced": "revoked", "active": "revoked"},
    "expire": {"active": "expired"},
}


# ---------------------------------------------------------------------------
# 证据 ref 形态（封闭 scheme；落在 A-01 既有 ref scheme 内，零新名）
# ---------------------------------------------------------------------------

MEMORY_EVIDENCE_PREFIX = "memory://experience/"
DECISION_EVIDENCE_RE_LENGTH = len("aurora_") + 32  # decision://aurora_<32hex>


def is_valid_evidence_ref(ref: Any) -> bool:
    """evidence_ref 形态校验（纯格式；真源核验归服务层）。"""
    if not isinstance(ref, str):
        return False
    if ref.startswith(MEMORY_EVIDENCE_PREFIX):
        rest = ref[len(MEMORY_EVIDENCE_PREFIX) :]
        return (
            len(rest) == len("expmem_") + 16
            and rest.startswith("expmem_")
            and all(c in "0123456789abcdef" for c in rest[7:])
        )
    if ref.startswith("decision://"):
        rest = ref[len("decision://") :]
        return (
            rest.startswith("aurora_")
            and len(rest) == DECISION_EVIDENCE_RE_LENGTH
            and all(c in "0123456789abcdef" for c in rest[len("aurora_") :])
        )
    return False


def evidence_ref_of_record(record_id: str) -> str:
    """M-06 经验记录 → ``memory://experience/<record_id>`` 引用。"""
    return f"{MEMORY_EVIDENCE_PREFIX}{record_id}"


# ---------------------------------------------------------------------------
# 数据载体（冻结 dataclass；存储行投影）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PolicyPatch:
    """一条 policy patch（存储行的只读投影；生命周期字段随行更新）。

    - ``payload``：单键字典，键/值域由面 schema 封闭（V2/V3 fail-closed）；
    - ``evidence_refs``：封闭 scheme 引用（真源核验归服务层证据门）；
    - ``transition_history``：append-only 审计（每次迁移 {at, action, from,
      to, reason, actor}；revoke 即时生效且审计永久保留）。
    """

    patch_id: str
    user_id: str
    surface: str
    payload: Mapping[str, str]
    state: str
    scope_goal_type: str | None = None
    scope_friction_tag: str | None = None
    evidence_refs: tuple[str, ...] = ()
    evidence_tier: str | None = None
    evidence_verified_at: datetime | None = None
    user_confirmed: bool = False
    provenance: str = "decision_loop"
    created_at: datetime | None = None
    activated_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    revoke_reason: str | None = None
    transition_history: tuple[Mapping[str, Any], ...] = ()

    @property
    def is_inert_state(self) -> bool:
        return self.state in {"expired", "revoked", "rejected"}

    def is_effective(self, now: datetime | None = None) -> bool:
        """生效判定（读时门）：state=active 且未过期（expires_at 含边界）。"""
        if self.state != "active":
            return False
        if self.expires_at is None or now is None:
            return self.state == "active"
        return now < self.expires_at

    def scope_matches(self, *, goal_type: str | None, friction_tag: str | None) -> bool:
        """情境 scope 匹配：已约束维度精确相等才生效（D-05 签名匹配同律）。

        「同 scope」语义（验收 ③）：patch 的 scope 约束与决策情境的
        goal/friction 维度精确匹配（未约束维度放行）。
        """
        if self.scope_goal_type is not None and self.scope_goal_type != (goal_type or ""):
            return False
        if self.scope_friction_tag is not None and self.scope_friction_tag != (friction_tag or ""):
            return False
        return True

    def canonical_digest(self) -> str:
        """内容寻址摘要（patch_id 派生 + 版本计算的共同基）。"""
        return json.dumps(
            {
                "v": POLICY_PATCH_SCHEMA_VERSION,
                "user_id": str(self.user_id),
                "surface": self.surface,
                "payload": dict(sorted((str(k), str(v)) for k, v in self.payload.items())),
                "scope_goal_type": self.scope_goal_type,
                "scope_friction_tag": self.scope_friction_tag,
                "evidence_refs": sorted(self.evidence_refs),
                "provenance": self.provenance,
            },
            sort_keys=True,
            separators=(",", ":"),
        )


def derive_policy_patch_id(
    *,
    user_id: str,
    surface: str,
    payload: Mapping[str, str],
    evidence_refs: Sequence[str],
    scope_goal_type: str | None = None,
    scope_friction_tag: str | None = None,
    provenance: str = "decision_loop",
) -> str:
    """确定性 patch id（``polpatch_<sha256[:32]>``；同内容重提议幂等）。"""
    patch = PolicyPatch(
        patch_id="",
        user_id=str(user_id),
        surface=str(surface),
        payload=dict(payload),
        state="candidate",
        scope_goal_type=scope_goal_type,
        scope_friction_tag=scope_friction_tag,
        evidence_refs=tuple(evidence_refs),
        provenance=provenance,
    )
    return "polpatch_" + hashlib.sha256(patch.canonical_digest().encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# 白名单验证（fail-closed；灵魂红线）
# ---------------------------------------------------------------------------


def _payload_schema_of(surface: str) -> frozenset[str] | None:
    """面的值域（intervention_preference/allocation_preference 特判）。"""
    if surface == "intervention_preference":
        return frozenset(AURORA_INTERVENTION_TYPES - _INERT_INTERVENTIONS)
    if surface == "allocation_preference":
        return ALLOCATION_PREFERENCE_VALUES
    return SURFACE_PAYLOAD_SCHEMAS.get(surface)


def validate_patch_request(
    *,
    surface: Any,
    payload: Any,
    evidence_refs: Any = (),
    scope_goal_type: Any = None,
    scope_friction_tag: Any = None,
    provenance: Any = "decision_loop",
) -> tuple[str, ...]:
    """patch 请求验证（fail-closed；返回 violations，空 = 合法）。

    任何越界（surface/payload 键/payload 值/evidence ref 形态/scope 值/
    provenance）都返回非空 violations——**没有静默修正**（fail-closed 而非
    fail-open：非法 patch 永远进不了存储层）。
    """
    violations: list[str] = []

    if not isinstance(surface, str) or surface not in POLICY_PATCH_SURFACES:
        violations.append(f"V1.surface_not_whitelisted: {surface!r}")
        return tuple(violations)  # surface 非法时后续判定无意义

    # payload：本面语义键集（intervention_preference 双键，其余单键），未知键 = V2
    if not isinstance(payload, Mapping):
        violations.append(f"V2.payload_field_unknown: payload is not a mapping: {payload!r}")
    else:
        expected_key = SURFACE_PAYLOAD_KEYS[surface]
        allowed_keys = (
            {expected_key, INTENTION_DIRECTION_KEY} if surface == "intervention_preference" else {expected_key}
        )
        keys = {str(key) for key in payload}
        if keys - allowed_keys:
            violations.append(f"V2.payload_field_unknown: expected only {sorted(allowed_keys)}, got {sorted(keys)}")
        if expected_key not in keys:
            violations.append(f"V2.payload_field_unknown: missing required key {expected_key!r}")
        else:
            value = payload[expected_key]
            if surface == "intervention_preference":
                # intervention_preference 双键面：intervention + direction
                if not isinstance(value, str) or value not in AURORA_INTERVENTION_TYPES:
                    violations.append(f"V3.payload_value_out_of_vocabulary: intervention {value!r} not in A-01 catalog")
                elif value in _INERT_INTERVENTIONS:
                    violations.append(f"V6.inert_intervention_not_patchable: {value!r}")
                direction = payload.get(INTENTION_DIRECTION_KEY)
                if surface == "intervention_preference" and INTENTION_DIRECTION_KEY not in keys:
                    violations.append(f"V2.payload_field_unknown: missing required key {INTENTION_DIRECTION_KEY!r}")
                elif direction not in INTENTION_DIRECTIONS:
                    violations.append(f"V3.payload_value_out_of_vocabulary: direction {direction!r}")
            else:
                schema = _payload_schema_of(surface)
                if not isinstance(value, str) or value not in schema:
                    violations.append(
                        f"V3.payload_value_out_of_vocabulary: {expected_key} {value!r} not in {sorted(schema)}"
                    )

    refs = evidence_refs if isinstance(evidence_refs, (list, tuple)) else ()
    if not refs:
        violations.append("V4.evidence_ref_malformed: at least one evidence ref is required")
    for ref in refs:
        if not is_valid_evidence_ref(ref):
            violations.append(f"V4.evidence_ref_malformed: {ref!r}")

    if scope_goal_type is not None and scope_goal_type not in GOAL_SLICE_TYPES:
        violations.append(f"V5.scope_value_out_of_vocabulary: goal_type {scope_goal_type!r}")
    if scope_friction_tag is not None and scope_friction_tag not in INTERVENTION_FRICTION_TAGS:
        violations.append(f"V5.scope_value_out_of_vocabulary: friction_tag {scope_friction_tag!r}")
    if provenance not in POLICY_PATCH_PROVENANCES:
        violations.append(f"V7.provenance_not_whitelisted: {provenance!r}")
    return tuple(violations)


# ---------------------------------------------------------------------------
# 生命周期状态机（纯函数）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionOutcome:
    """一次迁移判定：新状态（不变 = 拒绝）+ reasons（封闭码）。"""

    new_state: str
    reasons: tuple[str, ...]
    transitioned: bool = False
    history_entry: Mapping[str, Any] | None = None


def apply_transition(
    *,
    state: str,
    action: str,
    now: datetime,
    actor: str,
    reasons_extra: tuple[str, ...] = (),
) -> TransitionOutcome:
    """状态迁移判定（纯函数；非法迁移 T6 拒绝，状态不变）。

    ``reasons_extra``：调用方携带的门判定码（证据门 G 码等）随历史审计。
    """
    if state not in POLICY_PATCH_STATES:
        return TransitionOutcome(state, ("T6.illegal_transition",))
    if action not in POLICY_PATCH_ACTIONS:
        return TransitionOutcome(state, ("T6.illegal_transition",))
    target = POLICY_PATCH_TRANSITIONS.get(action, {}).get(state)
    if target is None:
        return TransitionOutcome(state, ("T6.illegal_transition",))

    reason_by_action = {
        "admit_evidence": "T1.evidence_admitted",
        "auto_activate": "T2.auto_activated",
        "confirm": "T3.user_confirmed_activated",
        "revoke": "T4.revoked_by_user_correction",
        "expire": "T5.expired",
    }
    reasons = tuple(dict.fromkeys((reason_by_action[action], *reasons_extra)))
    entry = {
        "at": now.isoformat() if hasattr(now, "isoformat") else str(now),
        "action": action,
        "from": state,
        "to": target,
        "reason": reason_by_action[action],
        "actor": str(actor),
    }
    return TransitionOutcome(target, reasons, True, entry)


def admit_decision(
    *,
    resolved_ref_count: int,
    direction_satisfied: bool,
    tier: str,
) -> tuple[bool, tuple[str, ...]]:
    """证据门判定（纯函数；服务层核验真源后调用）。

    - 无可解析证据 → 拒（G1）；
    - 方向敏感面（prefer/demote 族）方向不满足 → 拒（G3）；
    - 档位 insufficient → 拒（G2）；
    - 通过 → (True, ())；调用方再按 AUTO_ACTIVATE_TIERS 决定 auto_activate
      还是等待 confirm（confirm(若需)：single_observation 需用户确认）。
    """
    if resolved_ref_count <= 0:
        return False, ("G1.no_resolved_evidence",)
    if not direction_satisfied:
        return False, ("G3.evidence_direction_mismatch",)
    if tier not in _TIER_LADDER or tier == EVIDENCE_TIER_INSUFFICIENT:
        return False, ("G2.evidence_tier_insufficient",)
    return True, ()


def may_auto_activate(tier: str) -> bool:
    """档位达 AUTO_ACTIVATE_TIERS（repeated/accumulated）→ 免确认激活。"""
    return tier in AUTO_ACTIVATE_TIERS


# ---------------------------------------------------------------------------
# policy version 与缓存键（卡面 Work 3）
# ---------------------------------------------------------------------------

#: 空 active 集的版本常量（确定性；无 patch 用户的稳定版本号）。
POLICY_PATCH_EMPTY_VERSION = "polpatch_none"


def compute_policy_patch_version(patches: Iterable[PolicyPatch]) -> str:
    """active 集内容寻址版本（``polpatch_<sha256[:16]>``；空集 = 常量）。

    版本输入 = 每条 patch 的 (patch_id, surface, payload, scope, activated_at)
    规范化排序——active 集任一变化（激活/撤销/过期/确认激活时序变化）→
    版本必然变化（内容寻址，无碰撞豁免路径）。
    """
    entries = sorted(
        json.dumps(
            {
                "patch_id": p.patch_id,
                "surface": p.surface,
                "payload": dict(sorted((str(k), str(v)) for k, v in p.payload.items())),
                "scope_goal_type": p.scope_goal_type,
                "scope_friction_tag": p.scope_friction_tag,
                "activated_at": p.activated_at.isoformat() if p.activated_at else None,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        for p in patches
        if p.state == "active"
    )
    if not entries:
        return POLICY_PATCH_EMPTY_VERSION
    digest = hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()[:16]
    return f"polpatch_{digest}"


def patch_cache_key(base_key: str, version: str) -> str:
    """消费方缓存键并入 policy version（版本 bump → 键变 → 缓存不命中）。

    A-01 ``input_context_hash`` 同款纪律：策略版本是决策输入的一部分。
    """
    return f"{base_key}|polpatch={version}"


# ---------------------------------------------------------------------------
# 提名重排（3 个 surface 的确定性消费契约；A-02 守卫语义不变）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RankingMove:
    """一次提名重排的归因记录（可审计 + 可进决策 annotations）。"""

    patch_id: str
    surface: str
    intervention: str
    direction: str
    from_rank: int
    to_rank: int
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class RankingOutcome:
    """重排结果：新提名序 + 归因 + 未生效 patch 的跳过原因。"""

    nominated: tuple[str, ...]
    moves: tuple[RankingMove, ...]
    skipped: tuple[tuple[str, str], ...]  # (patch_id, reason code)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)


def _ranking_target_of(patch: PolicyPatch) -> tuple[str, str] | None:
    """patch → (目标干预, 方向)；非重排面返回 None。"""
    if patch.surface == "intervention_preference":
        intervention = patch.payload.get("intervention")
        direction = patch.payload.get("direction")
        if intervention and direction in INTENTION_DIRECTIONS:
            return (str(intervention), str(direction))
        return None
    mapped = RANKING_SURFACE_TARGETS.get(patch.surface, {})
    value = patch.payload.get(SURFACE_PAYLOAD_KEYS[patch.surface]) if patch.surface in SURFACE_PAYLOAD_KEYS else None
    if value is not None and str(value) in mapped:
        return mapped[str(value)]
    return None


def reorder_nominations(
    nominated: Sequence[str],
    patches: Iterable[PolicyPatch],
    *,
    goal_type: str | None = None,
    friction_tag: str | None = None,
    now: datetime | None = None,
    evidence_records: Iterable[Any] = (),
) -> RankingOutcome:
    """按生效 patch 重排 A-02 提名序（纯函数、确定性）。

    规则（全部确定性，可审计）：
    - 只考虑 ``state=active`` 且未过期且 **scope 匹配** 的 patch（同 scope 语义）；
    - 重排目标干预必须有真实方向证据（``evidence_records``：M-06 记录鸭子面
      ``intervention`` / ``has_positive_association_evidence`` /
      ``has_negative_association_evidence``）——无证据的 patch 记入
      ``skipped``（G3 码），**不改变排序**（证据缺位 = 不动，绝不凭空偏好）；
    - prefer → 移到序首（多条 prefer 按 (证据计数降序, patch_id 升序) 稳定排列；
      计数取自该干预全部正向证据记录）；demote → 移到序尾（同稳定性）；
    - 未被任何 patch 触及的提名保持相对序（稳定重排）。

    A-02 语义不变式：本函数只改变提名**顺序**——feasible set / 守卫 / inert
    地板全部照旧（把非法干预提名到首位也只会被 R 码剔除 → no_action，
    patch 永远不能把非法变合法）。
    """
    ordered = [str(n) for n in nominated if isinstance(n, str) and n.strip()]
    records = [r for r in evidence_records if r is not None]
    pos_evidence: dict[str, tuple[str, ...]] = {}
    neg_evidence: dict[str, tuple[str, ...]] = {}
    pos_count: dict[str, int] = {}
    neg_count: dict[str, int] = {}
    for record in records:
        intervention = getattr(record, "intervention", None)
        if not intervention:
            continue
        refs = pos_evidence.setdefault(intervention, [])
        neg_refs = neg_evidence.setdefault(intervention, [])
        if getattr(record, "has_positive_association_evidence", False):
            refs.append(evidence_ref_of_record(getattr(record, "record_id", "")))
            pos_count[intervention] = pos_count.get(intervention, 0) + int(getattr(record, "evidence_count", 0) or 0)
        if getattr(record, "has_negative_association_evidence", False):
            neg_refs.append(evidence_ref_of_record(getattr(record, "record_id", "")))
            neg_count[intervention] = neg_count.get(intervention, 0) + int(getattr(record, "evidence_count", 0) or 0)

    effective = [
        p
        for p in patches
        if p.state == "active"
        and p.is_effective(now)
        and p.scope_matches(goal_type=goal_type, friction_tag=friction_tag)
    ]
    moves: list[RankingMove] = []
    skipped: list[tuple[str, str]] = []
    result = list(ordered)

    prefers: list[tuple[int, str, str]] = []  # (‑evidence_count, patch_id, intervention)
    demotes: list[tuple[int, str, str]] = []
    for patch in effective:
        target = _ranking_target_of(patch)
        if target is None:
            continue
        intervention, direction = target
        if intervention not in result:
            # 提名序里没有该干预：重排无对象（不凭空注入提名——A-02 上游提名
            # 权在 spine/L2/决策环，patch 不新增动作，只调序）。
            skipped.append((patch.patch_id, "G1.no_resolved_evidence"))
            continue
        evidence_refs = (
            tuple(pos_evidence.get(intervention, ()))
            if direction == "prefer"
            else tuple(neg_evidence.get(intervention, ()))
        )
        count = pos_count.get(intervention, 0) if direction == "prefer" else neg_count.get(intervention, 0)
        if not evidence_refs:
            skipped.append((patch.patch_id, "G3.evidence_direction_mismatch"))
            continue
        entry = (-count, patch.patch_id, intervention)
        if direction == "prefer":
            prefers.append(entry)
        else:
            demotes.append(entry)

    all_refs: list[str] = []

    # 处理序：demote 先做（后做 prefer 会把 promote 目标放最前，二者互不干扰）。
    # 每族按 (证据计数降序, patch_id 升序) 的**倒序**逐个安置——顺序 insert(0)/
    # append 会让最后安置者占据端点，倒序处理使证据最多者落在最端点
    # （prefer 的首位 / demote 的最尾），族内相对序 = 证据强度序。
    for _, patch_id, intervention in sorted(demotes, key=lambda e: (-e[0], e[1])):
        from_rank = result.index(intervention)
        result.remove(intervention)
        result.append(intervention)
        refs = tuple(neg_evidence.get(intervention, ()))
        all_refs.extend(refs)
        moves.append(
            RankingMove(
                patch_id=patch_id,
                surface=next(p.surface for p in effective if p.patch_id == patch_id),
                intervention=intervention,
                direction="demote",
                from_rank=from_rank,
                to_rank=len(result) - 1,
                evidence_refs=refs,
            )
        )
    for _, patch_id, intervention in sorted(prefers, key=lambda e: (-e[0], e[1])):
        if intervention not in result:
            continue  # 防御：收集期已查在场，处理期成员不减少（demote 只移位不删）
        from_rank = result.index(intervention)
        result.remove(intervention)
        result.insert(0, intervention)
        refs = tuple(pos_evidence.get(intervention, ()))
        all_refs.extend(refs)
        moves.append(
            RankingMove(
                patch_id=patch_id,
                surface=next(p.surface for p in effective if p.patch_id == patch_id),
                intervention=intervention,
                direction="prefer",
                from_rank=from_rank,
                to_rank=0,
                evidence_refs=refs,
            )
        )

    return RankingOutcome(
        nominated=tuple(result),
        moves=tuple(moves),
        skipped=tuple(skipped),
        evidence_refs=tuple(dict.fromkeys(all_refs)),
    )


# ---------------------------------------------------------------------------
# 非重排面的确定性消费契约（因子/参数化投影）
# ---------------------------------------------------------------------------


def _latest_patch(patches: Iterable[PolicyPatch], surface: str) -> PolicyPatch | None:
    """同面多 patch 的确定性解冲突：按 (created_at, patch_id) 取最新。"""
    candidates = [p for p in patches if p.surface == surface and p.state == "active"]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.created_at.isoformat() if p.created_at else "", p.patch_id))


def allocation_user_preference(patches: Iterable[PolicyPatch]) -> str | None:
    """allocation_preference 面 → X-02 ``AllocationFactors.user_preference`` 值。

    消费契约：调用方把返回值并入 AllocationFactors（**既有入参**，A-04
    ``derive_delivery_factors`` 原样保留该维度）——X-02 八维 rubric 与 A-04
    联合约束层（J 码）照常生效，patch 不绕过任何守卫（学习守卫 G1 仍可压过
    prefer_agent——用户偏好不高于结构边界，A-02 X1 同律）。
    """
    patch = _latest_patch(patches, "allocation_preference")
    if patch is None:
        return None
    value = patch.payload.get("preference")
    return value if value in ALLOCATION_PREFERENCE_VALUES else None


def proactive_gate_overrides(patches: Iterable[PolicyPatch]) -> Mapping[str, bool]:
    """proactive_cadence 面 → A-02 proactive 门因子的确定性覆盖。

    minimal → proactive_budget_available=False（保守抑制主动触达；显式用户
    请求仍可豁免——A-02 X1 语义不变）；reduced/increased v1 不覆盖预算面
    （节奏细分接线归后续卡；本面 v1 语义 = minimal 才收紧）。
    """
    patch = _latest_patch(patches, "proactive_cadence")
    if patch is None:
        return {}
    cadence = patch.payload.get("cadence")
    if cadence == "minimal":
        return {"proactive_budget_available": False}
    return {}


def explanation_style(patches: Iterable[PolicyPatch]) -> str | None:
    """explanation 面 → 回复层解释风格参数（AURORA_V3 §6「Why this?」族）。"""
    patch = _latest_patch(patches, "explanation")
    if patch is None:
        return None
    return patch.payload.get("style")


__all__ = [
    "POLICY_PATCH_SCHEMA_VERSION",
    "POLICY_PATCH_SURFACES",
    "POLICY_PATCH_STATES",
    "POLICY_PATCH_ACTIONS",
    "POLICY_PATCH_REASONS",
    "POLICY_PATCH_TRANSITIONS",
    "POLICY_PATCH_PROVENANCES",
    "SURFACE_PAYLOAD_SCHEMAS",
    "SURFACE_PAYLOAD_KEYS",
    "RANKING_SURFACE_TARGETS",
    "INTENTION_DIRECTIONS",
    "ALLOCATION_PREFERENCE_VALUES",
    "AUTO_ACTIVATE_TIERS",
    "POLICY_PATCH_EMPTY_VERSION",
    "MEMORY_EVIDENCE_PREFIX",
    "PolicyPatch",
    "RankingMove",
    "RankingOutcome",
    "TransitionOutcome",
    "highest_tier",
    "is_valid_evidence_ref",
    "evidence_ref_of_record",
    "derive_policy_patch_id",
    "validate_patch_request",
    "apply_transition",
    "admit_decision",
    "may_auto_activate",
    "compute_policy_patch_version",
    "patch_cache_key",
    "reorder_nominations",
    "allocation_user_preference",
    "proactive_gate_overrides",
    "explanation_style",
]
