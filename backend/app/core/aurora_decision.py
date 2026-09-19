"""A-01 · AuroraDecisionContract —— Aurora 显式控制决策面契约（aurora_decision.v1）。

冻结声明（v3/07_tasks/cards/A-01.md，gate V3-2，locks aurora-contract）：
- **Aurora 管控制决策**：选哪个干预（intervention catalog）、为什么（rationale +
  evidence refs + uncertainties）、用哪一档认知（cognition tier）、或为什么不行动
  （no_action_reason）。本契约是这一「控制决策面」的唯一冻结形状。
- **不重建已有真源**——四边界（详见下节）：证据装配归 C-01，任务结构归 X-01，
  执行分配归 X-02，Aurora 只拥有控制决策本身。
- 契约快照 parity guard：backend/tests/contract/test_aurora_decision_contract.py
  冻结字段集（含 sha256 指纹）与全部封闭词表（精确集 + sha256 钉法）。任何变更
  需要 bump ``AURORA_DECISION_SCHEMA_VERSION`` 并过两位 reviewer。
- 扩展纪律（extend-only，对齐 C-01/M-01）：冻结于 aurora_decision.v1；新增字段
  只允许追加可选尾字段（不改既有字段名/顺序/语义与封闭词表），禁止改写或重排。

════════════════════════════════════════════════════════════════════════
边界声明（acceptance ④：谁拥有什么字段/决策）
════════════════════════════════════════════════════════════════════════
1. **C-01 decision_context.v1（app/core/decision_context.py）＝输入侧证据装配**。
   「哪些 memory/state/goal/plan 材料进入了决策、为何装入、降级了什么」由
   DecisionContext 独占。AuroraDecisionContract 只**引用**（evidence_refs /
   memory_use_receipts 的 ref 必须落在共同封闭 scheme 内），不重述装配过程。
2. **X-01 action_plan.v1（app/core/action_plan.py）＝任务结构**。
   desired_outcome / smallest_useful_step / completion_evidence /
   cognitive_ownership 归 ActionPlanContract（tasks 表 V3 列）。Aurora 决策的
   动作侧只携带指针 ``action_proposal_ref``（task://<id>），**永不内联**任务结构。
3. **X-02 allocation.v1.1（app/services/action_allocation_policy.py）＝执行分配**。
   「谁执行（human/agent/hybrid）」的 rubric 权威是 decide_allocation /
   vet_agent_offer。AuroraDecisionContract.execution_mode 是**生效模式的镜像**
   （供消费方快速读取），当 ``allocation_ref`` 指向一次 AllocationDecision 时，
   二者必须一致（``consistent_with_allocation`` 校验；A-04 联合接线日硬化为硬规则）。
   无 allocation_ref 的纯对话域控制决策（如 clarify/no_action）可独占携带 mode。
4. **AuroraDecisionContract（本模块）＝控制决策面**。
   intervention_type / rationale / uncertainties / cognition_tier /
   governance_mode / no_action_reason 归 Aurora。其他契约不重复定义这些字段。

命名消歧（C-01 对 SituationBrief.decision_context 的同款纪律）：
- ``app.core.aurora_decision.AuroraDecisionContract`` = 本冻结契约（控制决策面，
  schema_version/封闭词表/validate()）；
- ``app.aurora.runtime_v1.decision_loop.AuroraDecision`` = LLM 决策环的
  harness 执行决策（emit_message/wait/schedule_wake/...，运行时内部对象）。
  二者同名近义、分属控制面/执行面，**禁止互相替换或混用**；runtime 对象的
  升级路径见 v3-output/A-01/RUNTIME_MAP.md。

三态 kill switch（card Work 3 的契约化）：
- ``live``   —— 决策已计算并将作用于用户可见行为；
- ``shadow`` —— 决策已计算、仅观测（与 live 可经确定性 decision_id 对比，支撑
  AURORA_V3 §8 评测与 shadow/live 对比验收）；
- ``off``    —— **不存在 AuroraDecisionContract 实例**（治理性关闭不是一种
  决策；C-01 FIX-09 同款纪律：治理开关不得冒充决策语义）。off 态在调用侧
  直接不构造本契约（如 AuroraRuntimeV1Service.plan_turn 的 off 短路）。

确定性 decision_id：``aurora_`` + sha256(规范化核心字段)[:32]。同输入同结论
⇒ 同 id（shadow/live 对比、审计去重、decision://aurora_<id> 引用的锚点）。
created_at / trigger_point / annotations 不参与哈希。
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from app.core.action_plan import ACTION_SOURCE_REF_SCHEMES
from app.models.execution_intent import ExecutionMode

AURORA_DECISION_SCHEMA_VERSION = "aurora_decision.v1"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展需 bump 契约版本并过两位 reviewer）
# ---------------------------------------------------------------------------

#: 干预目录（AURORA_V3 §2，17 项）。目录是语义集合，不要求一类一个 Agent。
AURORA_INTERVENTION_TYPES: frozenset[str] = frozenset(
    {
        "clarify",
        "explain",
        "retrieve",
        "rescope",
        "split",
        "schedule",
        "practice",
        "review",
        "delegate",
        "execute",
        "co_execute",
        "reflect",
        "connect_peer",
        "pause",
        "remind",
        "abstain",
        "no_action",
    }
)

#: evidence/记忆回执的封闭 ref scheme：前 11 个与 X-01 ACTION_SOURCE_REF_SCHEMES
#: **结构对齐**（frozenset 派生，X-01 改动即在此处显现），第 12 个 ``signal`` 为
#: Aurora 域扩展——spine StateRegister / L0 ActionableSignal 观测
#: （signal://<state_key 或 signal_id>）。C-01 五 scheme 语义不变。
AURORA_DECISION_REF_SCHEMES: frozenset[str] = frozenset(ACTION_SOURCE_REF_SCHEMES | {"signal"})

#: 不确定性类型（AURORA_V3 §1 uncertainties[] 的类型化封闭集）。
AURORA_UNCERTAINTY_KINDS: frozenset[str] = frozenset(
    {
        "insufficient_context",  # 证据不足以支撑确定选择（对应 Check sufficiency 未过）
        "stale_signal",  # 输入信号已越过 TTL/新鲜度边界
        "conflicting_evidence",  # 证据互相矛盾（如用户报告 vs 行为信号）
        "unverified_inference",  # 决策依赖未探测/未确认的推断 claim
        "user_model_conflict",  # 用户连续否定系统判断（L3 model_conflict 唤醒族）
        "policy_gap",  # 现行 policy/rules 未覆盖该情形，走了保守默认
    }
)

#: 认知档位（决策由哪一层认知产出；对齐 runtime_v1 L0-L4 分层 + 降级档）。
AURORA_COGNITION_TIERS: frozenset[str] = frozenset(
    {
        "l0_rules",  # 纯确定性规则（deadline/quiet hours）
        "l1_light",  # 逐轮轻量感知（无 LLM）
        "l2_intervention",  # 模式升级干预（无 LLM）
        "l3_full_core",  # 交互式建模会话（高成本、限额）
        "l4_async",  # 后台深度分析（产出 policy candidate，不阻塞对话）
        "rule_fallback",  # 上层失败后的确定性降级路径（X-02 E1 同款语义）
    }
)

#: 不行动原因（与干预目录的 no_action/abstain 配对；治理关闭不在词表内——
#: off = 无契约实例，FIX-09 纪律）。
AURORA_NO_ACTION_REASONS: frozenset[str] = frozenset(
    {
        "materiality_below_threshold",  # 信号未过 materiality 阈值（stay 判定）
        "quiet_hours",  # 静默时段抑制（L0 quiet_hours / 睡眠守卫）
        "cooldown_active",  # 同型干预冷却中（L2 cooldown / proactive 预算）
        "focus_protected",  # 用户专注态受保护，不打断
        "budget_exhausted",  # proactive/成本预算耗尽
        "no_matching_pattern",  # 模式匹配无命中（L2）
        "no_active_states",  # 无可用输入状态（L2 空输入）
    }
)

#: 三态治理（card Work 3）。off 不在其中：off = 不构造契约实例。
AURORA_GOVERNANCE_MODES: frozenset[str] = frozenset({"live", "shadow"})

#: Bounded Plasticity 白名单 policy surface（AURORA_V3 §4：「只有白名单 policy
#: surface 可生效」）。与 policies/v1.0.yaml 的**事实归因**（P2-2 勘误后）：
#: parameter_write_authority 仅 {ux_intent, aurora_presence}；
#: capability_gate 只在 interaction_model_registry 的 writable_policy_scope 出现，
#: 且仅 task_execution / meta_reflection 两个变体（2/4）——按变体生效，非全局
#: 授权；顶层阈值面 {proactive_policy, materiality_threshold}；intervention_preference
#: 是 AURORA_V3 §4 规格层来源，v1.0.yaml 全文不存在（A-04/L4 依赖此差异时须
#: 按变体判 capability_gate 的写权限，不得当作全局白名单）。
AURORA_POLICY_PATCH_SCOPES: frozenset[str] = frozenset(
    {
        "ux_intent",
        "aurora_presence",
        "capability_gate",
        "intervention_preference",
        "proactive_policy",
        "materiality_threshold",
    }
)

_DECISION_ID_RE = re.compile(r"^aurora_[0-9a-f]{32}$")

#: 不携带执行方的不行动型干预（execution_mode 必须为 None 的唯一合法域）。
_INERT_INTERVENTIONS: frozenset[str] = frozenset({"no_action", "abstain"})


def _ref_scheme(ref: str) -> str:
    return ref.split("://", 1)[0] if "://" in ref else ""


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


# ---------------------------------------------------------------------------
# 契约 dataclass（字段集被 tests/contract/test_aurora_decision_contract.py 冻结）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisionUncertainty:
    """单条不确定性：封闭类型 + 自由文本说明（说明可为空，类型必须封闭）。"""

    kind: str
    note: str = ""

    def validate(self) -> tuple[str, ...]:
        violations: list[str] = []
        if self.kind not in AURORA_UNCERTAINTY_KINDS:
            violations.append(f"uncertainty kind {self.kind!r} out of vocabulary")
        return tuple(violations)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "note": self.note}


@dataclass(frozen=True)
class PolicyPatchCandidate:
    """Bounded Plasticity 候选（AURORA_V3 §4）：只允许白名单 surface。

    - scope 必须落在 ``AURORA_POLICY_PATCH_SCOPES``（其他 surface 拒绝）；
    - intervention_preference 为 None 或干预目录成员；
    - 必须携带 ≥1 条封闭 scheme 的证据 ref；
    - 必须有过期时间（bounded：patch 不是永久策略变更）；
    - user_confirmed 默认 False——未确认的 patch 不生效（写路径属 A-04/L4）。
    评估历史（evaluation history）属 L4 运行时状态，不进契约。
    """

    scope: str
    evidence_refs: tuple[str, ...]
    confidence: float
    expires_at: datetime | None
    intervention_preference: str | None = None
    user_confirmed: bool = False

    def validate(self) -> tuple[str, ...]:
        violations: list[str] = []
        if self.scope not in AURORA_POLICY_PATCH_SCOPES:
            violations.append(f"policy patch scope {self.scope!r} not in whitelist surface")
        if self.intervention_preference is not None and self.intervention_preference not in AURORA_INTERVENTION_TYPES:
            violations.append(
                f"policy patch intervention_preference {self.intervention_preference!r} out of vocabulary"
            )
        if not self.evidence_refs:
            violations.append("policy patch must carry at least one evidence ref")
        for ref in self.evidence_refs:
            if _ref_scheme(ref) not in AURORA_DECISION_REF_SCHEMES:
                violations.append(f"policy patch evidence ref has unknown scheme: {ref!r}")
        try:
            confidence = float(self.confidence)
        except (TypeError, ValueError):
            confidence = -1.0
        if not 0.0 <= confidence <= 1.0:
            violations.append(f"policy patch confidence {self.confidence!r} outside [0, 1]")
        if self.expires_at is None:
            violations.append("policy patch must carry expires_at (bounded plasticity)")
        return tuple(violations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "intervention_preference": self.intervention_preference,
            "evidence_refs": list(self.evidence_refs),
            "confidence": self.confidence,
            "expires_at": _iso(self.expires_at),
            "user_confirmed": self.user_confirmed,
        }


@dataclass(frozen=True)
class AuroraDecisionContract:
    """Aurora 控制决策契约（一次 DecisionContext → 一个控制决策的冻结输出形状）。

    交叉字段规则（validate() 强制）：
    - ``no_action_reason`` 当且仅当 intervention_type ∈ {no_action, abstain} 时
      携带，且必须落在封闭词表；
    - ``execution_mode`` 为 None 当且仅当 intervention_type ∈ {no_action, abstain}
      （不行动没有执行方；行动类决策必须携带 ExecutionMode 镜像）；
    - ``clarify`` 决策必须携带 clarifying_question（否则 clarify 无载体）；
    - ``memory_use_receipts ⊆ evidence_refs``（回执的 memory 必须真的进了证据面）；
    - ``action_proposal_ref`` 只认 task://（X-01 边界）、``allocation_ref`` 只认
      decision://（X-02 边界）；
    - ``governance_mode=shadow`` 的实例不得被应用于用户可见行为（调用方纪律，
      A-04 接线日由统一 read 门强制）。
    """

    user_id: UUID
    intervention_type: str
    rationale_summary: str
    cognition_tier: str
    execution_mode: ExecutionMode | None = None
    schema_version: str = AURORA_DECISION_SCHEMA_VERSION
    governance_mode: str = "live"
    decision_id: str | None = None
    trigger_point: str | None = None
    input_context_hash: str | None = None
    evidence_refs: tuple[str, ...] = ()
    uncertainties: tuple[DecisionUncertainty, ...] = ()
    clarifying_question: str | None = None
    action_proposal_ref: str | None = None
    allocation_ref: str | None = None
    memory_use_receipts: tuple[str, ...] = ()
    policy_patch_candidate: PolicyPatchCandidate | None = None
    no_action_reason: str | None = None
    annotations: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        # 冻结 annotations 为只读视图（C-01 FIX-09/F3 同款：防下游突变观测面）。
        object.__setattr__(self, "annotations", MappingProxyType(dict(self.annotations)))

    # -- 校验 --------------------------------------------------------------

    def validate(self) -> tuple[str, ...]:
        violations: list[str] = []
        if self.schema_version != AURORA_DECISION_SCHEMA_VERSION:
            violations.append(f"schema_version mismatch: {self.schema_version!r}")
        if self.intervention_type not in AURORA_INTERVENTION_TYPES:
            violations.append(f"intervention_type {self.intervention_type!r} out of vocabulary")
        if not isinstance(self.cognition_tier, str) or self.cognition_tier not in AURORA_COGNITION_TIERS:
            violations.append(f"cognition_tier {self.cognition_tier!r} out of vocabulary")
        if self.governance_mode not in AURORA_GOVERNANCE_MODES:
            violations.append(f"governance_mode {self.governance_mode!r} out of vocabulary")
        if not (self.rationale_summary or "").strip():
            violations.append("rationale_summary must be non-empty")
        inert = self.intervention_type in _INERT_INTERVENTIONS
        if inert:
            if self.no_action_reason is None:
                violations.append(f"intervention_type {self.intervention_type!r} requires no_action_reason")
            if self.execution_mode is not None:
                violations.append(f"intervention_type {self.intervention_type!r} must not carry execution_mode")
        else:
            if self.no_action_reason is not None:
                violations.append("no_action_reason is only valid for no_action/abstain")
            if self.execution_mode is None:
                violations.append("actionable intervention must carry execution_mode")
            elif not isinstance(self.execution_mode, ExecutionMode):
                violations.append(f"execution_mode must be ExecutionMode, got {self.execution_mode!r}")
        if self.no_action_reason is not None and self.no_action_reason not in AURORA_NO_ACTION_REASONS:
            violations.append(f"no_action_reason {self.no_action_reason!r} out of vocabulary")
        if self.intervention_type == "clarify" and not (self.clarifying_question or "").strip():
            violations.append("clarify intervention must carry clarifying_question")
        for ref in self.evidence_refs:
            if _ref_scheme(ref) not in AURORA_DECISION_REF_SCHEMES:
                violations.append(f"evidence ref has unknown or missing scheme: {ref!r}")
        for ref in self.memory_use_receipts:
            if _ref_scheme(ref) not in AURORA_DECISION_REF_SCHEMES:
                violations.append(f"memory use receipt has unknown or missing scheme: {ref!r}")
        if not set(self.memory_use_receipts) <= set(self.evidence_refs):
            violations.append("memory_use_receipts must be a subset of evidence_refs")
        for entry in self.uncertainties:
            violations.extend(entry.validate())
        if self.action_proposal_ref is not None and _ref_scheme(self.action_proposal_ref) != "task":
            violations.append(f"action_proposal_ref must use task:// scheme (X-01 boundary): {self.action_proposal_ref!r}")
        if self.allocation_ref is not None and _ref_scheme(self.allocation_ref) != "decision":
            violations.append(
                f"allocation_ref must use decision:// scheme (X-02 boundary): {self.allocation_ref!r}"
            )
        if self.policy_patch_candidate is not None:
            violations.extend(self.policy_patch_candidate.validate())
        if self.decision_id is not None and not _DECISION_ID_RE.match(self.decision_id):
            violations.append(f"decision_id malformed (expect aurora_<32hex>): {self.decision_id!r}")
        return tuple(violations)

    # -- 消费便捷接口 --------------------------------------------------------

    def decision_id_or_compute(self) -> str:
        """确定性决策 id：未显式携带时按核心字段计算。

        created_at / annotations / governance_mode 不参与哈希——治理档位是部署
        属性而非决策内容，同输入同结论的 shadow 与 live 实例共享同一 id
        （shadow/live 对比的锚点）。
        """
        if self.decision_id is not None:
            return self.decision_id
        seed = json.dumps(
            {
                "schema_version": self.schema_version,
                "user_id": str(self.user_id),
                "intervention_type": self.intervention_type,
                "execution_mode": None if self.execution_mode is None else self.execution_mode.value,
                "rationale_summary": self.rationale_summary,
                "cognition_tier": self.cognition_tier,
                "input_context_hash": self.input_context_hash,
                "evidence_refs": sorted(self.evidence_refs),
                "no_action_reason": self.no_action_reason,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return "aurora_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]

    def decision_ref(self) -> str:
        """canonical 引用（X-01 decision:// scheme 共享命名空间，前缀 aurora_）。"""
        return f"decision://{self.decision_id_or_compute()}"

    def consistent_with_allocation(self, allocation: Any) -> tuple[str, ...]:
        """与 X-02 AllocationDecision 的一致性检查（A-04 联合接线日的硬化前置）。

        allocation_ref 已指向一次分配决策时，execution_mode 镜像必须与其 mode
        一致；未指向时返回空（对话域控制决策可独占携带 mode）。
        """
        if self.allocation_ref is None or self.execution_mode is None:
            return ()
        allocation_mode = getattr(allocation, "mode", None)
        if allocation_mode is not None and allocation_mode != self.execution_mode.value:
            return (
                f"execution_mode {self.execution_mode.value!r} != allocation mode {allocation_mode!r}",
            )
        return ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "user_id": str(self.user_id),
            "intervention_type": self.intervention_type,
            "rationale_summary": self.rationale_summary,
            "cognition_tier": self.cognition_tier,
            "execution_mode": None if self.execution_mode is None else self.execution_mode.value,
            "governance_mode": self.governance_mode,
            "decision_id": self.decision_id_or_compute(),
            "trigger_point": self.trigger_point,
            "input_context_hash": self.input_context_hash,
            "evidence_refs": list(self.evidence_refs),
            "uncertainties": [entry.to_dict() for entry in self.uncertainties],
            "clarifying_question": self.clarifying_question,
            "action_proposal_ref": self.action_proposal_ref,
            "allocation_ref": self.allocation_ref,
            "memory_use_receipts": list(self.memory_use_receipts),
            "policy_patch_candidate": (
                None if self.policy_patch_candidate is None else self.policy_patch_candidate.to_dict()
            ),
            "no_action_reason": self.no_action_reason,
            "annotations": dict(self.annotations),
            "created_at": _iso(self.created_at),
        }


def aurora_decision_from_dict(payload: Mapping[str, Any] | None) -> AuroraDecisionContract | None:
    """从 to_dict() 载荷重构契约（A-04/X-05/D-02 消费面；脏载荷返回 None，不 raise）。

    与 ``AuroraDecisionContract.validate()`` 共同构成读侧门：重构后必须
    ``validate() == ()`` 才可信。已知字段缺失/类型不符 → None（可观测降级由
    调用方留痕，本函数保持纯函数）。
    """
    if not isinstance(payload, Mapping):
        return None
    try:
        raw_mode = payload.get("execution_mode")
        mode = None if raw_mode is None else ExecutionMode(str(raw_mode))
        raw_patch = payload.get("policy_patch_candidate")
        patch = None
        if isinstance(raw_patch, Mapping):
            expires_raw = raw_patch.get("expires_at")
            patch = PolicyPatchCandidate(
                scope=str(raw_patch["scope"]),
                intervention_preference=raw_patch.get("intervention_preference"),
                evidence_refs=tuple(str(ref) for ref in raw_patch.get("evidence_refs") or ()),
                confidence=float(raw_patch["confidence"]),
                expires_at=datetime.fromisoformat(str(expires_raw)) if expires_raw else None,
                user_confirmed=bool(raw_patch.get("user_confirmed", False)),
            )
        created_raw = payload.get("created_at")
        return AuroraDecisionContract(
            user_id=UUID(str(payload["user_id"])),
            intervention_type=str(payload["intervention_type"]),
            rationale_summary=str(payload.get("rationale_summary") or ""),
            cognition_tier=str(payload["cognition_tier"]),
            execution_mode=mode,
            schema_version=str(payload.get("schema_version") or AURORA_DECISION_SCHEMA_VERSION),
            governance_mode=str(payload.get("governance_mode") or "live"),
            decision_id=payload.get("decision_id"),
            trigger_point=payload.get("trigger_point"),
            input_context_hash=payload.get("input_context_hash"),
            evidence_refs=tuple(str(ref) for ref in payload.get("evidence_refs") or ()),
            uncertainties=tuple(
                DecisionUncertainty(kind=str(entry["kind"]), note=str(entry.get("note") or ""))
                for entry in payload.get("uncertainties") or ()
                if isinstance(entry, Mapping) and "kind" in entry
            ),
            clarifying_question=payload.get("clarifying_question"),
            action_proposal_ref=payload.get("action_proposal_ref"),
            allocation_ref=payload.get("allocation_ref"),
            memory_use_receipts=tuple(str(ref) for ref in payload.get("memory_use_receipts") or ()),
            policy_patch_candidate=patch,
            no_action_reason=payload.get("no_action_reason"),
            annotations=dict(payload.get("annotations") or {}),
            created_at=datetime.fromisoformat(str(created_raw)) if created_raw else None,
        )
    except (KeyError, TypeError, ValueError):
        return None


# 供消费方做字段集自检的便捷导出（契约真源是 dataclass 本身）
DECISION_UNCERTAINTY_FIELDS: tuple[str, ...] = tuple(f.name for f in dataclasses.fields(DecisionUncertainty))
POLICY_PATCH_CANDIDATE_FIELDS: tuple[str, ...] = tuple(f.name for f in dataclasses.fields(PolicyPatchCandidate))
AURORA_DECISION_FIELDS: tuple[str, ...] = tuple(f.name for f in dataclasses.fields(AuroraDecisionContract))
