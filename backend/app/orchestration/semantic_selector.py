"""V4-I03 复杂表达的受限语义选择器（快慢路之间的受限语义判定层）。

定位（v4/04_tasks/cards/V4-I03.md + v4/03_intelligence/AURORA_SEMANTIC_POLICY.md）：
I09 确定性快路（``deterministic_lane.py``）只吃零信息量形态；其余全部落真模型
慢路。本模块是**快慢路之间**的受限语义判定层：对「多否定 / 时间约束 / 材料不足」
三类复杂表达做**结构化探针**（受限词表 + 多 token 结构规则，决策不由单个关键词
承载），并为语义选择提供**封闭词表校验**——模型只允许在传入白名单内选合法
干预/执行模式/ref/tool，可提出一个缺失变量；引用未知 ref / 目录外 tool 时显式
拒绝澄清，绝不产生「已完成/已执行」类话术（B05 契约反例表同源纪律）。

三面（对应卡验收三条）：
1. ``probe_complex_expression``：复杂表达结构探针——每形态由 ≥2 token 的结构
   单元承载判定，冻结反例保证「单个关键词不翻转」（去任一结构算子即不触发）；
2. ``run_selection``：受限语义选择——schema 校验（``sparkle_semantic_selection.v1``，
   未合规最多修复一次），白名单硬校验（干预/模式/ref scheme+白名单成员/tool
   目录），失败走封闭拒绝码 + 澄清话术，拒绝型结局结构上不携带任何可执行声明；
3. ``run_arm_comparison``：同输入规则臂/语义臂对照——每臂判定、成本（I10 口径
   ``usage_source``/``sub_calls``；零模型=0 实测，未上报用量=None 不冒充）、失败
   形态（封闭词表）留档可审计，落 context/metrics。

词表纪律（不造第二权威）：
- 干预词表 = ``AURORA_INTERVENTION_TYPES``（A-01 契约）；
- 执行模式 = ``ExecutionMode``（X-01/X-02 同源）；
- ref scheme = ``AURORA_DECISION_REF_SCHEMES``（X-01 派生 + signal 扩展）；
- 不确定/弃权原因 = ``AURORA_UNCERTAINTY_KINDS``；
- confidence_band 审慎标签 = B05 §4 同款 {high, medium, low, unknown}，不显示
  虚构精度百分比。

不推翻 I09 词表：本层不参与问候/确认判定，只在实质消息面上做复杂表达判定。
行为开关：``settings.SEMANTIC_SELECTOR_MODE`` ∈ {off, shadow, live}（默认 off；
off = 零行为。shadow = 影子对照记录，永不改变路由；live 语义归下游消费卡
V4-I04/I07，本卡 live 在聊天流内与 shadow 同义——只记录不裁决，如实标注）。
真模型 proposer 本卡不接（费用授权线），语义臂经 ``SemanticProposer`` 协议可插
（测试用 stub）；生产影子对照中语义臂如实记 ``proposer_unavailable`` 失败形态。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from loguru import logger

from app.core.aurora_decision import (
    AURORA_DECISION_REF_SCHEMES,
    AURORA_INTERVENTION_TYPES,
    AURORA_UNCERTAINTY_KINDS,
)
from app.core.metrics import (
    SEMANTIC_SELECTOR_COMPARISON_TOTAL,
    SEMANTIC_SELECTOR_REFUSAL_TOTAL,
)
from app.models.execution_intent import ExecutionMode

SEMANTIC_SELECTOR_VERSION = "semantic_selector.v4.i03.v1"
SELECTION_SCHEMA_VERSION = "sparkle_semantic_selection.v1"

#: schema 修复预算（AURORA_SEMANTIC_POLICY L2：「schema不合法最多修复一次」）。
MAX_SCHEMA_REPAIRS = 1

#: confidence_band 审慎标签（B05 §4 同款；不虚构精度百分比）。
CONFIDENCE_BANDS: frozenset[str] = frozenset({"high", "medium", "low", "unknown"})

#: 惰性干预（A-01 同款：不携带执行方，execution_mode 必须为 None）。
_INERT_INTERVENTIONS: frozenset[str] = frozenset({"no_action"})

# ---------------------------------------------------------------------------
# 面一：复杂表达结构探针（验收①）
# ---------------------------------------------------------------------------


class ComplexForm(StrEnum):
    """复杂表达形态（封闭枚举；metric/对照记录取值域）。"""

    MULTI_NEGATION = "multi_negation"  # 多否定极性翻转（不是不…＝肯定）
    TIME_DEFERRAL = "time_deferral"  # 时间约束·搁置（以后再说）
    DEADLINE_PRESSURE = "deadline_pressure"  # 时间约束·临期（还没…就/还剩N天）
    MATERIAL_INSUFFICIENCY = "material_insufficiency"  # 材料不足（现在没有材料）


@dataclass(frozen=True)
class ProbeEvidence:
    """单条探针命中（结构单元级，不是关键词级）。"""

    form: ComplexForm
    pattern_id: str  # 封闭模式 id（冻结词表成员）
    matched_span: str  # 命中的原文片段（审计用，非判定依据本身）

    def to_dict(self) -> dict[str, str]:
        return {"form": self.form.value, "pattern_id": self.pattern_id, "matched_span": self.matched_span}


# 结构模式（冻结；每个 pattern 是多 token 结构单元：拆掉任一算子即不匹配——
# 这就是「判定不因单个关键词翻转」的实现机制。扩展 = 词表变更，过 reviewer）。
# 统一口径：先按句界（。！？；!?;）切子句，模式只在子句内匹配；缓解词在同一
# 子句内出现则该命中作废（「没有材料也不影响」不构成材料不足阻塞）。
_NEGATION_CONTINUATION = r"(?![，。,.！!？?；;、\s])"  # 否定算子后须紧跟谓词（子句内无停顿）

_MULTI_NEGATION_PATTERNS: tuple[tuple[str, str], ...] = (
    # pattern_id, regex（均为「否定算子×2 + 紧邻谓词」结构）
    ("double_neg_bushi_bu", r"并不是不|并不是没|并不是非"),
    ("double_neg_bushi_bu_short", r"不是" + _NEGATION_CONTINUATION + r"(?:不|没|非|无)"),
    ("double_neg_bingfei", r"并非" + _NEGATION_CONTINUATION + r"(?:不|没|非|无)"),
    ("double_neg_bunengshuo", r"不能说(?:不|没|非|无|缺)"),
    ("double_neg_weiceng", r"未曾不|未尝不|无不"),
)

_TIME_DEFERRAL_PATTERNS: tuple[tuple[str, str], ...] = (
    # 搁置 = 时间指称 + 「再」 + 处置动词 的连续结构（单「以后」/单「再说」
    # 都不算——「以后每天背单词」不触发，「再说一遍」不触发）。
    (
        "deferral_marker_zaishuo",
        r"(?:以后|下次|晚些?时候?|晚点|回头|改天|过阵子|过几天|待会儿|等会儿|之后|明天|后天|周末|放假)"
        r"再(?:说|看|定|讲|弄|搞|处理|安排|决定|考虑|学|练|复习|规划|计划)",
    ),
    ("deferral_xianbu", r"先不(?:弄|搞|做|学|练|管|安排|处理)(?:了|吧)?"),
)

_DEADLINE_PATTERNS: tuple[tuple[str, str], ...] = (
    # 「还没…就」进阶结构：还未完成 + 临近后果（强后续词，防单「就」误挂）。
    ("deadline_haimeijiuyao", r"还没(?:有)?[^，。,.！!？?；;]{0,16}就(?:要|快|得|考|截止|到期|来不及|没时间|要考)"),
    ("deadline_laibuji", r"来不及"),
    (
        "deadline_haisheng",
        r"还(?:剩|有不到|只剩)[0-9０-９一二两三四五六七八九十百半几]{0,4}\s*(?:天|周|个月?|日|小时|分钟|秒)",
    ),
    ("deadline_mashang", r"马上(?:要|就)|眼看(?:要|就)|倒计时|迫在眉睫"),
)

_MATERIAL_NOUN = r"(?:材料|资料|教材|讲义|笔记|课件|课本|书|真题|题目|习题|练习题|参考书|视频课?|音频|档案|文献)"
_MATERIAL_NEGATION = r"(?:没有?|缺(?:少|乏)?|不足|找不到|没找到|没带|还没(?:准备|找到|拿到|整理|下)好?|没下)"
_MATERIAL_INSUFFICIENCY_PATTERNS: tuple[tuple[str, str], ...] = (
    # 否定与材料名词之间允许 ≤4 字修饰（找不到「复习」资料）；停顿即断开。
    ("material_neg_noun", _MATERIAL_NEGATION + r"[^，。,.！!？?；;]{0,4}?" + _MATERIAL_NOUN),
    ("material_noun_neg", _MATERIAL_NOUN + _NEGATION_CONTINUATION + _MATERIAL_NEGATION),
)

# 缓解词（同子句内出现 → 命中作废）：缺口被兜住/自愿继续，不构成阻塞。
_MITIGATION_MARKERS: tuple[str, ...] = (
    "也不影响",
    "不影响",
    "没关系",
    "无所谓",
    "不碍事",
    "照样",
    "也能",
    "也可以",
    "但够",
    "足够",
    "还够",
    "但可以",
    "不过可以",
)

# 有意排除（单关键词零判定力——各形态的反例族）：
# - 单「不/没/以后/再说/还没/材料」等任何单 token：不在任何模式内独立成判。
# - 「不是」后接非否定谓词（不是想学）＝单否定，不翻转。
# - 分句双否定（我不知道，也不想知道）：否定各在不同子句、同极性，不翻转。


@dataclass(frozen=True)
class ComplexExpressionProfile:
    """复杂表达探针结果（形态标志 + 结构证据；可观测、可审计）。"""

    evidence: tuple[ProbeEvidence, ...] = field(default_factory=tuple)

    @property
    def forms(self) -> frozenset[ComplexForm]:
        return frozenset(item.form for item in self.evidence)

    @property
    def has_complex_expression(self) -> bool:
        return bool(self.evidence)

    def has_form(self, form: ComplexForm) -> bool:
        return form in self.forms

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_complex_expression": self.has_complex_expression,
            "forms": sorted(form.value for form in self.forms),
            "evidence": [item.to_dict() for item in self.evidence],
        }


def _clauses(text: str) -> list[str]:
    """按句界切子句（模式只在子句内匹配；跨子句停顿即断开否定辖域）。"""
    return [clause for clause in re.split(r"[。！？；!?;\n]", text) if clause.strip()]


def _mitigated(clause: str) -> bool:
    return any(marker in clause for marker in _MITIGATION_MARKERS)


def probe_complex_expression(text: str) -> ComplexExpressionProfile:
    """复杂表达结构探针（纯规则、零模型、零上游调用）。

    判定机制：冻结结构模式（多 token 连续单元）逐子句匹配；材料不足形态需
    同子句无缓解词。任何形态都不由单关键词承载——测试冻结「去任一算子即
    不触发」的反例族。
    """
    body = str(text or "")
    if not body.strip():
        return ComplexExpressionProfile()

    pattern_groups: tuple[tuple[ComplexForm, tuple[tuple[str, str], ...]], ...] = (
        (ComplexForm.MULTI_NEGATION, _MULTI_NEGATION_PATTERNS),
        (ComplexForm.TIME_DEFERRAL, _TIME_DEFERRAL_PATTERNS),
        (ComplexForm.DEADLINE_PRESSURE, _DEADLINE_PATTERNS),
        (ComplexForm.MATERIAL_INSUFFICIENCY, _MATERIAL_INSUFFICIENCY_PATTERNS),
    )

    evidence: list[ProbeEvidence] = []
    for form, patterns in pattern_groups:
        seen_ids: set[str] = set()
        for clause in _clauses(body):
            if form is ComplexForm.MATERIAL_INSUFFICIENCY and _mitigated(clause):
                continue
            for pattern_id, pattern in patterns:
                if pattern_id in seen_ids:
                    continue
                match = re.search(pattern, clause)
                if match:
                    evidence.append(ProbeEvidence(form=form, pattern_id=pattern_id, matched_span=match.group(0)))
                    seen_ids.add(pattern_id)
    return ComplexExpressionProfile(evidence=tuple(evidence))


# ---------------------------------------------------------------------------
# 面二：受限语义选择（验收②）
# ---------------------------------------------------------------------------


class SelectionVerdict(StrEnum):
    """选择结局（封闭枚举）：selected / refused / abstained。"""

    SELECTED = "selected"
    REFUSED = "refused"
    ABSTAINED = "abstained"


class RefusalCode(StrEnum):
    """拒绝码（封闭词表；扩展 = 词表变更过 reviewer）。"""

    UNKNOWN_REF = "unknown_ref"  # 引用了白名单外/不存在 schemes 的 ref
    OUT_OF_CATALOG_TOOL = "out_of_catalog_tool"  # 目录外 tool 名
    UNKNOWN_INTERVENTION = "unknown_intervention"  # 干预不在契约词表/白名单
    INVALID_EXECUTION_MODE = "invalid_execution_mode"  # 执行模式不在白名单
    SCHEMA_INVALID_AFTER_REPAIR = "schema_invalid_after_repair"  # 修复一次仍不合规
    PROPOSER_UNAVAILABLE = "proposer_unavailable"  # 语义臂不可用（可观测降级）


#: schema 顶层键封闭集（未知键 = 违规，可修复）。
_SCHEMA_KEYS: frozenset[str] = frozenset(
    {
        "selected_intervention_id",
        "execution_mode",
        "used_ref_ids",
        "tool",
        "blocking_factors",
        "missing_decision_variable",
        "question",
        "confidence_band",
        "abstain_reason",
    }
)

_MAX_QUESTION_CHARS = 200
_MAX_MISSING_VAR_CHARS = 64

#: 拒绝澄清话术（冻结文案表；全部显式「先不执行」，零成功话术）。
_REFUSAL_COPY: dict[RefusalCode, str] = {
    RefusalCode.UNKNOWN_REF: "我找不到你引用的任务或目标记录，先不执行；方便确认一下具体是哪一项吗？",
    RefusalCode.OUT_OF_CATALOG_TOOL: "这个工具不在当前可用目录里，先不执行；需要我说明现在能做哪些吗？",
    RefusalCode.UNKNOWN_INTERVENTION: "这个操作类型不在当前允许范围内，先不执行；我们可以换个方式继续。",
    RefusalCode.INVALID_EXECUTION_MODE: "这个执行方式不在当前允许范围，先不执行；你想自己做、我做，还是一起？",
    RefusalCode.SCHEMA_INVALID_AFTER_REPAIR: "我还没弄清楚这次该选什么，先不执行；可以再说具体一点吗？",
    RefusalCode.PROPOSER_UNAVAILABLE: "选择器暂不可用，先不执行；你可以直接说想怎么继续。",
}

#: 成功话术标记（拒绝/弃权结局的渲染文本禁止出现；测试冻结扫描）。
SUCCESS_TALK_MARKERS: tuple[str, ...] = (
    "已完成",
    "已执行",
    "已保存",
    "已创建",
    "已修改",
    "已删除",
    "已更新",
    "已经完成",
    "搞定了",
    "executed successfully",
    "task completed",
)


@dataclass(frozen=True)
class SelectionRequest:
    """受限选择请求：白名单由调用方传入（候选/干预/ref/tool 全部封闭）。

    构造即 fail-loud：白名单必须 ⊆ 对应契约词表；ref 必须落在封闭 scheme 集
    （B05 I3 同源：scheme 不对 = 构造期拒绝，不进运行时）。
    """

    allowed_interventions: frozenset[str] = frozenset()
    allowed_execution_modes: frozenset[str] = frozenset({mode.value for mode in ExecutionMode})
    allowed_refs: frozenset[str] = frozenset()
    allowed_tools: frozenset[str] = frozenset()
    allowed_candidate_ids: frozenset[str] = frozenset()
    context_digest: str = ""

    def __post_init__(self) -> None:
        out_of_vocab = self.allowed_interventions - AURORA_INTERVENTION_TYPES
        if out_of_vocab:
            raise ValueError(f"allowed_interventions out of AURORA_INTERVENTION_TYPES: {sorted(out_of_vocab)}")
        known_modes = {mode.value for mode in ExecutionMode}
        bad_modes = self.allowed_execution_modes - known_modes
        if bad_modes:
            raise ValueError(f"allowed_execution_modes out of ExecutionMode: {sorted(bad_modes)}")
        bad_schemes = {ref.split("://", 1)[0] for ref in self.allowed_refs} - AURORA_DECISION_REF_SCHEMES
        if bad_schemes:
            raise ValueError(f"allowed_refs contain schemes outside AURORA_DECISION_REF_SCHEMES: {sorted(bad_schemes)}")

    def to_digest(self) -> str:
        payload = "|".join(
            (
                ",".join(sorted(self.allowed_interventions)),
                ",".join(sorted(self.allowed_execution_modes)),
                ",".join(sorted(self.allowed_refs)),
                ",".join(sorted(self.allowed_tools)),
                ",".join(sorted(self.allowed_candidate_ids)),
                self.context_digest,
            )
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ArmCost:
    """臂成本（I10 计量诚实口径）。

    - 零模型臂：calls=0、tokens=0、usage_source="measured"（0 是实测事实，
      I09 快路 0+0 记账同口径）；
    - 模型臂：tokens/usage_source 由臂如实上报；臂未上报用量 → None
      （unknown 不冒充，I10「未知键→None」口径），禁止填 0。
    """

    model_calls: int = 0
    prompt_tokens: int | None = 0
    completion_tokens: int | None = 0
    usage_source: str | None = "measured"
    sub_calls: tuple[dict[str, Any], ...] = ()

    def merged(self, other: ArmCost) -> ArmCost:
        """两次调用（首次+修复）的成本合并；None 传播不冒充。"""

        def _sum(a: int | None, b: int | None) -> int | None:
            if a is None or b is None:
                return None
            return a + b

        usage_source: str | None
        if self.usage_source is not None and other.usage_source == self.usage_source:
            usage_source = self.usage_source
        elif self.model_calls == 0:
            usage_source = other.usage_source
        elif other.model_calls == 0:
            usage_source = self.usage_source
        else:
            usage_source = None  # 两侧来源不一致 → unknown，不挑一个冒充
        return ArmCost(
            model_calls=self.model_calls + other.model_calls,
            prompt_tokens=_sum(self.prompt_tokens, other.prompt_tokens),
            completion_tokens=_sum(self.completion_tokens, other.completion_tokens),
            usage_source=usage_source,
            sub_calls=(*self.sub_calls, *other.sub_calls),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_calls": self.model_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "usage_source": self.usage_source,
            "sub_calls": list(self.sub_calls),
        }


#: 零模型臂成本（0 实测，无隐含模型 attempt）。
ZERO_MODEL_COST = ArmCost()


@dataclass(frozen=True)
class ProposerResponse:
    """语义臂 proposer 单次响应：提议（裸 dict）+ 如实成本上报。"""

    proposal: dict[str, Any]
    cost: ArmCost


class SemanticProposer(Protocol):
    """语义臂提议者协议（生产 = 受限提示词的模型调用；测试 = stub）。

    修复轮以 ``repair_feedback`` 携带违规清单与白名单提示；proposer 的任何
    内部失败应自行转为诚实响应或抛异常（异常由 run_selection 捕获为
    proposer_unavailable 可观测降级，不拼成功话术）。
    """

    async def propose(
        self,
        request: SelectionRequest,
        *,
        repair_feedback: tuple[str, ...] = (),
    ) -> ProposerResponse: ...


@dataclass(frozen=True)
class SelectionOutcome:
    """受限选择结局。

    结构保证（验收②）：verdict=REFUSED 时 selected_intervention_id /
    execution_mode / used_ref_ids / tool 恒空——拒绝结局结构上不携带任何
    可执行声明，「已完成/已执行」话术无处可拼；render_refusal 只出冻结
    澄清文案（含「先不执行」），SUCCESS_TALK_MARKERS 扫描由测试钉死。
    """

    verdict: SelectionVerdict
    cost: ArmCost = ZERO_MODEL_COST
    selected_intervention_id: str | None = None
    execution_mode: str | None = None
    used_ref_ids: tuple[str, ...] = ()
    tool: str | None = None
    blocking_factor_ids: tuple[str, ...] = ()
    missing_decision_variable: str | None = None
    question: str | None = None
    confidence_band: str = "unknown"
    abstain_reason: str | None = None
    refusal_code: RefusalCode | None = None
    violations: tuple[str, ...] = ()
    repairs_used: int = 0

    @property
    def failure_form(self) -> str:
        """失败形态（封闭词表；对照记录用）。selected → none。"""
        if self.verdict is SelectionVerdict.SELECTED:
            return "none"
        if self.verdict is SelectionVerdict.ABSTAINED:
            return "abstained"
        return self.refusal_code.value if self.refusal_code else "refused"

    def render_refusal(self) -> str:
        """拒绝/不可用结局的澄清话术（冻结文案表；selected 调用即 fail-loud）。"""
        if self.verdict is not SelectionVerdict.REFUSED:
            raise ValueError("render_refusal is only defined for REFUSED outcomes")
        assert self.refusal_code is not None
        return _REFUSAL_COPY.get(self.refusal_code, _REFUSAL_COPY[RefusalCode.SCHEMA_INVALID_AFTER_REPAIR])

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": SELECTION_SCHEMA_VERSION,
            "verdict": self.verdict.value,
            "failure_form": self.failure_form,
            "confidence_band": self.confidence_band,
            "violations": list(self.violations),
            "repairs_used": self.repairs_used,
            "cost": self.cost.to_dict(),
        }
        if self.verdict is SelectionVerdict.SELECTED:
            payload.update(
                {
                    "selected_intervention_id": self.selected_intervention_id,
                    "execution_mode": self.execution_mode,
                    "used_ref_ids": list(self.used_ref_ids),
                    "tool": self.tool,
                    "blocking_factor_ids": list(self.blocking_factor_ids),
                    "missing_decision_variable": self.missing_decision_variable,
                    "question": self.question,
                }
            )
        if self.verdict is SelectionVerdict.ABSTAINED:
            payload["abstain_reason"] = self.abstain_reason
        if self.refusal_code is not None:
            payload["refusal_code"] = self.refusal_code.value
            payload["refusal_copy"] = self.render_refusal()
        return payload


def _ref_scheme(ref: str) -> str:
    return ref.split("://", 1)[0] if "://" in ref else ""


@dataclass(frozen=True)
class _ProposalAudit:
    violations: tuple[str, ...]
    refusal: RefusalCode | None = None


def _validate_proposal(proposal: Any, request: SelectionRequest) -> _ProposalAudit:
    """schema 校验 + 白名单硬校验（纯函数）。

    违规分级：
    - schema 违规（结构/类型/未知键/长度）→ 可修复（最多一次）；
    - 白名单硬违规（未知 ref / 目录外 tool / 未知干预 / 非法模式）→ 修复
      不可能把未知 ref 变为已知，首拍即显式拒绝（fail-loud）。
    """
    if not isinstance(proposal, dict):
        return _ProposalAudit(violations=("proposal_not_an_object",), refusal=RefusalCode.SCHEMA_INVALID_AFTER_REPAIR)

    violations: list[str] = []
    hard_refusal: RefusalCode | None = None

    unknown_keys = sorted(set(proposal) - _SCHEMA_KEYS)
    if unknown_keys:
        violations.extend(f"unknown_key:{key}" for key in unknown_keys)

    # confidence_band 必填且封闭（审慎标签）。
    band = proposal.get("confidence_band")
    if band not in CONFIDENCE_BANDS:
        violations.append("confidence_band_invalid")

    abstain_reason = proposal.get("abstain_reason")
    abstaining = abstain_reason is not None
    if abstaining and abstain_reason not in AURORA_UNCERTAINTY_KINDS:
        violations.append("abstain_reason_out_of_vocabulary")

    # refs（used_ref_ids + blocking_factors[].evidence_refs）白名单硬校验。
    refs: list[Any] = list(proposal.get("used_ref_ids") or [])
    blocking = proposal.get("blocking_factors") or []
    if not isinstance(blocking, list):
        violations.append("blocking_factors_not_a_list")
        blocking = []
    for index, factor in enumerate(blocking):
        if not isinstance(factor, dict):
            violations.append(f"blocking_factor_{index}_not_an_object")
            continue
        candidate_id = factor.get("candidate_id")
        if request.allowed_candidate_ids and candidate_id not in request.allowed_candidate_ids:
            violations.append(f"blocking_factor_{index}_candidate_unknown")
        refs.extend(factor.get("evidence_refs") or [])
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            violations.append("ref_not_a_string")
            hard_refusal = hard_refusal or RefusalCode.UNKNOWN_REF
            continue
        if _ref_scheme(ref) not in AURORA_DECISION_REF_SCHEMES:
            violations.append(f"ref_scheme_out_of_closed_set:{ref}")
            hard_refusal = hard_refusal or RefusalCode.UNKNOWN_REF
        elif ref not in request.allowed_refs:
            violations.append(f"ref_not_in_allowed_set:{ref}")
            hard_refusal = hard_refusal or RefusalCode.UNKNOWN_REF

    # tool 目录校验（目录外 = 显式拒绝；非字符串/空串 = schema 违规可修复）。
    tool = proposal.get("tool")
    if tool is not None:
        if not isinstance(tool, str) or not tool.strip():
            violations.append("tool_invalid")
        elif tool not in request.allowed_tools:
            violations.append(f"tool_out_of_catalog:{tool}")
            hard_refusal = hard_refusal or RefusalCode.OUT_OF_CATALOG_TOOL

    if abstaining:
        return _ProposalAudit(violations=tuple(violations), refusal=hard_refusal)

    intervention = proposal.get("selected_intervention_id")
    if not isinstance(intervention, str) or not intervention.strip():
        violations.append("selected_intervention_missing")
    elif intervention not in AURORA_INTERVENTION_TYPES:
        violations.append(f"intervention_out_of_contract_vocabulary:{intervention}")
        hard_refusal = hard_refusal or RefusalCode.UNKNOWN_INTERVENTION
    elif intervention not in request.allowed_interventions:
        violations.append(f"intervention_not_in_allowed_set:{intervention}")
        hard_refusal = hard_refusal or RefusalCode.UNKNOWN_INTERVENTION

    mode = proposal.get("execution_mode")
    is_inert = isinstance(intervention, str) and intervention in _INERT_INTERVENTIONS
    if is_inert:
        if mode is not None:
            violations.append("inert_intervention_mode_must_be_null")
    else:
        if not isinstance(mode, str) or not mode.strip():
            violations.append("execution_mode_missing")
        elif mode not in request.allowed_execution_modes:
            violations.append(f"execution_mode_not_allowed:{mode}")
            hard_refusal = hard_refusal or RefusalCode.INVALID_EXECUTION_MODE

    missing_var = proposal.get("missing_decision_variable")
    if missing_var is not None:
        if not isinstance(missing_var, str) or not missing_var.strip():
            violations.append("missing_decision_variable_not_a_string")
        elif len(missing_var) > _MAX_MISSING_VAR_CHARS:
            violations.append("missing_decision_variable_too_long")
        elif not str(proposal.get("question") or "").strip():
            violations.append("missing_variable_requires_question")

    question = proposal.get("question")
    if question is not None and (not isinstance(question, str) or len(question) > _MAX_QUESTION_CHARS):
        violations.append("question_invalid")

    return _ProposalAudit(violations=tuple(violations), refusal=hard_refusal)


def _outcome_from(
    proposal: dict[str, Any], audit: _ProposalAudit, cost: ArmCost, repairs_used: int
) -> SelectionOutcome:
    if audit.refusal is not None:
        return SelectionOutcome(
            verdict=SelectionVerdict.REFUSED,
            cost=cost,
            refusal_code=audit.refusal,
            violations=audit.violations,
            repairs_used=repairs_used,
        )
    if audit.violations:
        return SelectionOutcome(
            verdict=SelectionVerdict.REFUSED,
            cost=cost,
            refusal_code=RefusalCode.SCHEMA_INVALID_AFTER_REPAIR,
            violations=audit.violations,
            repairs_used=repairs_used,
        )
    abstain_reason = proposal.get("abstain_reason")
    if abstain_reason is not None:
        return SelectionOutcome(
            verdict=SelectionVerdict.ABSTAINED,
            cost=cost,
            confidence_band=str(proposal.get("confidence_band") or "unknown"),
            abstain_reason=str(abstain_reason),
            question=str(question) if (question := proposal.get("question")) else None,
            repairs_used=repairs_used,
        )
    refs = tuple(ref for ref in (proposal.get("used_ref_ids") or []) if isinstance(ref, str))
    factor_ids = tuple(
        str(factor.get("candidate_id"))
        for factor in (proposal.get("blocking_factors") or [])
        if isinstance(factor, dict) and factor.get("candidate_id") is not None
    )
    tool = proposal.get("tool")
    return SelectionOutcome(
        verdict=SelectionVerdict.SELECTED,
        cost=cost,
        selected_intervention_id=str(proposal.get("selected_intervention_id")),
        execution_mode=proposal.get("execution_mode") if isinstance(proposal.get("execution_mode"), str) else None,
        used_ref_ids=refs,
        tool=tool if isinstance(tool, str) and tool.strip() else None,
        blocking_factor_ids=factor_ids,
        missing_decision_variable=proposal.get("missing_decision_variable"),
        question=proposal.get("question"),
        confidence_band=str(proposal.get("confidence_band") or "unknown"),
        repairs_used=repairs_used,
    )


async def run_selection(
    request: SelectionRequest,
    proposer: SemanticProposer | None,
) -> SelectionOutcome:
    """受限语义选择主入口：schema 校验 + 一次修复 + 白名单硬校验。

    - proposer None → PROPOSER_UNAVAILABLE 显式拒绝（可观测降级，零话术伪造）；
    - 首拍 schema 违规（无硬拒绝）→ 携带违规清单修复一次；仍违规 →
      SCHEMA_INVALID_AFTER_REPAIR 拒绝；
    - 白名单硬违规（未知 ref / 目录外 tool / 未知干预 / 非法模式）→ 首拍
      显式拒绝（不花修复调用）；
    - proposer 异常 → PROPOSER_UNAVAILABLE 拒绝 + WARN（不吞、不伪装成功）。
    """
    if proposer is None:
        outcome = SelectionOutcome(
            verdict=SelectionVerdict.REFUSED,
            cost=ZERO_MODEL_COST,
            refusal_code=RefusalCode.PROPOSER_UNAVAILABLE,
            violations=("proposer_unavailable",),
        )
        _inc_refusal(outcome.refusal_code)
        return outcome

    cost = ArmCost()
    repairs_used = 0
    try:
        response = await proposer.propose(request)
        cost = cost.merged(response.cost)
        audit = _validate_proposal(response.proposal, request)
        if audit.violations and audit.refusal is None and repairs_used < MAX_SCHEMA_REPAIRS:
            repairs_used += 1
            response = await proposer.propose(request, repair_feedback=audit.violations)
            cost = cost.merged(response.cost)
            audit = _validate_proposal(response.proposal, request)
        outcome = _outcome_from(response.proposal, audit, cost, repairs_used)
    except Exception as exc:  # noqa: BLE001 — proposer 失败 = 可观测降级，不冒充成功
        logger.warning("[SemanticSelector] proposer failed: {!r}", exc)
        # 用量诚实口径：中断调用的用量未知 → tokens/usage_source 置 None 不冒充
        # （已完成的响应成本保留；model_calls 只计已收到响应的调用）。
        cost = ArmCost(
            model_calls=cost.model_calls,
            prompt_tokens=None,
            completion_tokens=None,
            usage_source=None,
            sub_calls=cost.sub_calls,
        )
        outcome = SelectionOutcome(
            verdict=SelectionVerdict.REFUSED,
            cost=cost,
            refusal_code=RefusalCode.PROPOSER_UNAVAILABLE,
            violations=(f"proposer_exception:{type(exc).__name__}",),
            repairs_used=repairs_used,
        )
        _inc_refusal(outcome.refusal_code)
        return outcome
    _inc_refusal(outcome.refusal_code)
    return outcome


# ---------------------------------------------------------------------------
# 规则臂（I09 确定性形态）与双臂对照（验收③）
# ---------------------------------------------------------------------------


class RuleArmDecisionKind(StrEnum):
    """规则臂判定（封闭枚举；规则臂零模型，仅结构探针驱动）。"""

    NO_COMPLEX_EXPRESSION = "no_complex_expression"  # 无复杂表达（I09 词表外仍走既有慢路）
    CLARIFY_MISSING_MATERIAL = "clarify_missing_material"  # 材料不足 → 澄清缺失项
    DEFER_ACTION = "defer_action"  # 搁置表达 → 不安排执行
    RESCOPE_DEADLINE = "rescope_deadline"  # 临期 → 重定范围
    SEMANTIC_ESCALATE = "semantic_escalate"  # 多否定等极性敏感表达 → 交语义臂


#: 规则臂判定优先级（确定性；多形态并存时按此序取一，测试冻结）。
_RULE_ARM_PRIORITY: tuple[RuleArmDecisionKind, ...] = (
    RuleArmDecisionKind.CLARIFY_MISSING_MATERIAL,
    RuleArmDecisionKind.DEFER_ACTION,
    RuleArmDecisionKind.RESCOPE_DEADLINE,
    RuleArmDecisionKind.SEMANTIC_ESCALATE,
)

_FORM_TO_RULE_DECISION: dict[ComplexForm, RuleArmDecisionKind] = {
    ComplexForm.MATERIAL_INSUFFICIENCY: RuleArmDecisionKind.CLARIFY_MISSING_MATERIAL,
    ComplexForm.TIME_DEFERRAL: RuleArmDecisionKind.DEFER_ACTION,
    ComplexForm.DEADLINE_PRESSURE: RuleArmDecisionKind.RESCOPE_DEADLINE,
    ComplexForm.MULTI_NEGATION: RuleArmDecisionKind.SEMANTIC_ESCALATE,
}

#: 规则臂澄清问句（冻结文案表；句式不携带任何执行成功语义）。
_RULE_ARM_QUESTIONS: dict[RuleArmDecisionKind, str] = {
    RuleArmDecisionKind.CLARIFY_MISSING_MATERIAL: "你现在缺哪些材料？补充后我们再继续安排。",
    RuleArmDecisionKind.DEFER_ACTION: "那这部分先放着；想继续时直接说就行。",
    RuleArmDecisionKind.RESCOPE_DEADLINE: "时间比较紧，要不要先把范围收窄到最关键的部分？",
    RuleArmDecisionKind.SEMANTIC_ESCALATE: "",
    RuleArmDecisionKind.NO_COMPLEX_EXPRESSION: "",
}

#: 规则臂判定 ↔ 语义臂结局的一致性映射（封闭；不对应 → not_comparable）。
_RULE_DECISION_TO_INTERVENTIONS: dict[RuleArmDecisionKind, frozenset[str]] = {
    RuleArmDecisionKind.CLARIFY_MISSING_MATERIAL: frozenset({"clarify", "retrieve"}),
    RuleArmDecisionKind.DEFER_ACTION: frozenset({"pause", "remind", "no_action", "abstain"}),
    RuleArmDecisionKind.RESCOPE_DEADLINE: frozenset({"rescope", "split", "practice", "review"}),
    RuleArmDecisionKind.SEMANTIC_ESCALATE: frozenset({"explain", "reflect", "co_execute", "clarify"}),
    RuleArmDecisionKind.NO_COMPLEX_EXPRESSION: frozenset(),
}

# V4-I04 移交闭合（I03 O-2）：映射值全部落契约词表的 import 期不变式——
# 字面量漂移（改名/删词）在 import 时即失败，不再等影子 agreement 指标偏斜。
for _names in _RULE_DECISION_TO_INTERVENTIONS.values():
    assert (
        _names <= AURORA_INTERVENTION_TYPES
    ), f"_RULE_DECISION_TO_INTERVENTIONS out of AURORA_INTERVENTION_TYPES: {sorted(_names - AURORA_INTERVENTION_TYPES)}"

COMPARISON_AGREEMENTS: frozenset[str] = frozenset({"agree", "disagree", "not_comparable"})


@dataclass(frozen=True)
class RuleArmDecision:
    """规则臂判定（零模型；成本恒 ZERO_MODEL_COST）。"""

    kind: RuleArmDecisionKind
    profile: ComplexExpressionProfile
    question: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "arm": "rule",
            "decision": self.kind.value,
            "question": self.question or None,
            "cost": ZERO_MODEL_COST.to_dict(),
            "failure_form": "none",
            "profile": self.profile.to_dict(),
        }


def rule_arm_decide(profile: ComplexExpressionProfile) -> RuleArmDecision:
    """规则臂：结构探针 → 封闭判定（优先级确定性；零模型）。"""
    for kind in _RULE_ARM_PRIORITY:
        form = next((f for f, decision in _FORM_TO_RULE_DECISION.items() if decision is kind), None)
        if form is not None and profile.has_form(form):
            return RuleArmDecision(kind=kind, profile=profile, question=_RULE_ARM_QUESTIONS[kind])
    return RuleArmDecision(
        kind=RuleArmDecisionKind.NO_COMPLEX_EXPRESSION,
        profile=profile,
        question=_RULE_ARM_QUESTIONS[RuleArmDecisionKind.NO_COMPLEX_EXPRESSION],
    )


@dataclass(frozen=True)
class ArmComparisonRecord:
    """同输入双臂对照记录（可审计落账：判定/成本/失败形态全保留）。"""

    comparison_id: str
    input_text_sha256: str
    selector_version: str
    rule_arm: RuleArmDecision
    semantic_outcome: SelectionOutcome
    agreement: str  # COMPARISON_AGREEMENTS 成员

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "input_text_sha256": self.input_text_sha256,
            "selector_version": self.selector_version,
            "agreement": self.agreement,
            "rule_arm": self.rule_arm.to_dict(),
            "semantic_arm": {
                "arm": "semantic",
                "verdict": self.semantic_outcome.verdict.value,
                "failure_form": self.semantic_outcome.failure_form,
                "selected_intervention_id": self.semantic_outcome.selected_intervention_id,
                "execution_mode": self.semantic_outcome.execution_mode,
                "refusal_code": (
                    self.semantic_outcome.refusal_code.value if self.semantic_outcome.refusal_code else None
                ),
                "cost": self.semantic_outcome.cost.to_dict(),
                "repairs_used": self.semantic_outcome.repairs_used,
            },
        }

    def to_audit_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)


def compare_arms(rule: RuleArmDecision, semantic: SelectionOutcome) -> str:
    """双臂一致性（封闭三值）：agree / disagree / not_comparable。

    口径：语义臂 selected → 干预是否落在规则臂判定的预期干预族；语义臂
    abstained 且原因与规则臂澄清向一致（clarify ↔ insufficient_context）→
    agree；refused → not_comparable（语义臂没有产出可对照的判定）。
    """
    if semantic.verdict is SelectionVerdict.REFUSED:
        return "not_comparable"
    if semantic.verdict is SelectionVerdict.ABSTAINED:
        if rule.kind is RuleArmDecisionKind.CLARIFY_MISSING_MATERIAL:
            return "agree" if semantic.abstain_reason == "insufficient_context" else "disagree"
        return "not_comparable" if semantic.abstain_reason == "insufficient_context" else "disagree"
    expected = _RULE_DECISION_TO_INTERVENTIONS.get(rule.kind, frozenset())
    if not expected:
        return "not_comparable"
    return "agree" if semantic.selected_intervention_id in expected else "disagree"


async def run_arm_comparison(
    user_message: str,
    request: SelectionRequest,
    *,
    proposer: SemanticProposer | None = None,
) -> ArmComparisonRecord:
    """同输入跑规则臂与语义臂，对照保留判定/成本/失败形态（验收③）。

    - 规则臂：结构探针 + 封闭映射，零模型（成本 0 实测）；
    - 语义臂：``run_selection``（proposer None 时如实记 proposer_unavailable）；
    - 对照记录带确定性 comparison_id（版本+输入+白名单摘要哈希），可审计。
    """
    text = str(user_message or "")
    profile = probe_complex_expression(text)
    rule = rule_arm_decide(profile)
    semantic = await run_selection(request, proposer)
    agreement = compare_arms(rule, semantic)
    text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    record = ArmComparisonRecord(
        comparison_id=f"sscmp_{hashlib.sha256(f'{SEMANTIC_SELECTOR_VERSION}|{text_sha}|{request.to_digest()}'.encode()).hexdigest()[:32]}",
        input_text_sha256=text_sha,
        selector_version=SEMANTIC_SELECTOR_VERSION,
        rule_arm=rule,
        semantic_outcome=semantic,
        agreement=agreement,
    )
    _record_comparison_metrics(record)
    logger.info(
        "[SemanticSelector] comparison id={} agreement={} rule={} semantic={} failure={}",
        record.comparison_id,
        agreement,
        rule.kind.value,
        semantic.verdict.value,
        semantic.failure_form,
    )
    return record


async def run_semantic_selector_shadow(
    user_message: str,
    context_data: dict[str, Any] | None,
    *,
    proposer: SemanticProposer | None = None,
) -> ArmComparisonRecord | None:
    """聊天流影子入口（router_node 接线；off = 零行为）。

    - mode=off → None（零调用、零写入）；
    - mode=shadow/live → 跑对照并把记录写 ``context_data["semantic_selector"]``
      （shadow/live 均不改变路由——live 的裁决语义归下游消费卡 V4-I04/I07）；
    - mode 未知值 → 按 off 处理 + WARN（fail-closed，不猜）。
    """
    from app.config import settings

    mode = str(getattr(settings, "SEMANTIC_SELECTOR_MODE", "off") or "off").strip().lower()
    if mode not in ("off", "shadow", "live"):
        logger.warning("[SemanticSelector] unknown SEMANTIC_SELECTOR_MODE={!r}; treating as off", mode)
        return None
    if mode == "off":
        return None
    record = await run_arm_comparison(user_message, _default_request_from_context(context_data), proposer=proposer)
    if isinstance(context_data, dict):
        context_data["semantic_selector"] = record.to_dict()
        context_data["semantic_selector_mode"] = mode
    return record


def _default_request_from_context(context_data: dict[str, Any] | None) -> SelectionRequest:
    """影子对照的默认白名单（保守最小集，全部来自契约词表子集）。

    生产接线方（I04/I07）将替换为目标域真实白名单；本卡影子对照只要求
    词表封闭与对照可审计，不声明生产白名单。
    """
    del context_data  # 影子面暂不消费上下文派生白名单（如实留空）
    return SelectionRequest(
        allowed_interventions=frozenset({"clarify", "explain", "retrieve", "rescope", "pause", "no_action"}),
        allowed_execution_modes=frozenset({mode.value for mode in ExecutionMode}),
    )


def _inc_refusal(code: RefusalCode | None) -> None:
    if code is None:
        return
    try:
        SEMANTIC_SELECTOR_REFUSAL_TOTAL.labels(refusal_code=code.value).inc()
    except Exception:  # pragma: no cover - 遥测失败不影响主链路
        logger.opt(exception=True).warning("semantic selector refusal metric failed")


def _record_comparison_metrics(record: ArmComparisonRecord) -> None:
    try:
        SEMANTIC_SELECTOR_COMPARISON_TOTAL.labels(
            agreement=record.agreement,
            rule_decision=record.rule_arm.kind.value,
            semantic_verdict=record.semantic_outcome.verdict.value,
        ).inc()
    except Exception:  # pragma: no cover - 遥测失败不影响主链路
        logger.opt(exception=True).warning("semantic selector comparison metric failed")


__all__ = [
    "ArmComparisonRecord",
    "ArmCost",
    "COMPARISON_AGREEMENTS",
    "ComplexExpressionProfile",
    "ComplexForm",
    "CONFIDENCE_BANDS",
    "MAX_SCHEMA_REPAIRS",
    "ProposerResponse",
    "ProbeEvidence",
    "RefusalCode",
    "RuleArmDecision",
    "RuleArmDecisionKind",
    "SELECTION_SCHEMA_VERSION",
    "SEMANTIC_SELECTOR_VERSION",
    "SUCCESS_TALK_MARKERS",
    "SelectionOutcome",
    "SelectionRequest",
    "SelectionVerdict",
    "SemanticProposer",
    "ZERO_MODEL_COST",
    "compare_arms",
    "probe_complex_expression",
    "rule_arm_decide",
    "run_arm_comparison",
    "run_selection",
    "run_semantic_selector_shadow",
]
