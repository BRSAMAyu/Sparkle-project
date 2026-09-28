"""洞察呈现契约层（V4-D05，``insight.presentation.v1``）——把 D07 事实卡接成
用户可读观察/下一步建议时的**表述纪律全函数**。

本模块是真源之上的呈现层判定（零 IO、零 LLM、零第二真源），只消费既有权威：

- **样本身份** = D02 ``derive_attribution_sample_id``（``attr_<sha256[:32]>``，
  重放恒同 id）。D02-R1 C-3 消费方义务：**呈现侧公开样本量/比率前必须按
  sample_id 先行去重**——重放投递只如实计入 raw 计数，永不放大去重后样本量。
  命名空间说明：干预生命周期的锚点是 ``decision_id``（``aurora_<32hex>``，
  intervention occurrence 级），四域词表在此仅作派生种子命名空间消费——
  ``decision_id`` 与 D02 归因的 canonical UUID 锚点分属不同 id 空间，不会产生
  跨面身份碰撞；domain 固定取 ``OCCURRENCE``（intervention occurrence 锚）。
- **因果断言扫描** = M-06 ``scan_output_for_causal_assertions``（单一权威，零
  重实现）。本模块在其上补**数值面**：部分关联子集上的百分比 + 因果/成效措辞
  组合（「三例只有两例关联」写「因果提升 67%」类）在结构上拒绝。
- **claim 禁词** = D-05 ``FORBIDDEN_CLAIM_TERMS``（封闭词表 import，不复制）。
- **观察窗/删失语义** = D-05 ``resolve_observation_status``（唯一权威；本模块
  的回访判定只消费其结论，不重算窗口）。

验收红线（卡 V4-D05，全部可失败）：
1. 三例只有两例关联不能写因果提升 67%（分母/样本量随行）；
2. 无数据不出「充分理解」；已删来源不复用；
3. 一条观察 ≤ 一个主建议，用户可拒绝且不扣奖励。

任何词表/字段集改动需 bump ``PRESENTATION_SCHEMA_VERSION`` 并过 reviewer。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence

from app.core.attribution import (
    ATTRIBUTION_SCHEMA_VERSION,
    AttributionDomain,
    derive_attribution_sample_id,
)
from app.core.experience_memory import scan_output_for_causal_assertions
from app.core.intervention_lifecycle import (
    FORBIDDEN_CLAIM_TERMS,
    ObservationStatus,
)

PRESENTATION_SCHEMA_VERSION = "insight.presentation.v1"

# ---------------------------------------------------------------------------
# ① 样本去重（D02-R1 C-3 消费方义务：重放不进样本量）
# ---------------------------------------------------------------------------


def presentation_sample_id(*, decision_id: str, outcome_id: str) -> str:
    """干预呈现面的归因样本身份（D02 权威派生，重放恒同）。

    (``decision_id``, ``outcome_id``) 内容寻址——同一 outcome 对同一 decision 的
    重放投递（at-least-once 关联重写、扫描 beat 重跑）恒产同 id；时间字段不进
    派生。domain 取 ``OCCURRENCE``：decision_id 是 intervention occurrence 级锚，
    与 D02 四域归因的 UUID 锚点不同 id 空间，命名空间不碰撞。
    """
    return derive_attribution_sample_id(
        domain=AttributionDomain.OCCURRENCE,
        anchor_id=str(decision_id),
        outcome_id=str(outcome_id),
    )


@dataclass(frozen=True)
class SampleDedup:
    """呈现侧样本去重结果（raw 如实、unique 才是样本量；差值审计可见）。"""

    n_raw: int
    n_unique: int
    unique_sample_ids: tuple[str, ...]
    duplicates_dropped: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ATTRIBUTION_SCHEMA_VERSION,
            "n_raw": self.n_raw,
            "n_unique": self.n_unique,
            "duplicates_dropped": self.duplicates_dropped,
            "unique_sample_ids": list(self.unique_sample_ids),
        }


def dedupe_outcome_samples(*, decision_id: str, outcome_ids: Sequence[str]) -> SampleDedup:
    """(decision, outcome) 投递序列 → 按样本身份先行去重。

    顺序保持（首见位）；空 outcome_id 不构成样本身份，跳过（不计 raw 也不计
    unique——空引用不是投递证据）。
    """
    seen: set[str] = set()
    unique_ids: list[str] = []
    raw = 0
    for outcome_id in outcome_ids:
        ref = str(outcome_id or "")
        if not ref:
            continue
        raw += 1
        sample_id = presentation_sample_id(decision_id=decision_id, outcome_id=ref)
        if sample_id in seen:
            continue
        seen.add(sample_id)
        unique_ids.append(sample_id)
    return SampleDedup(
        n_raw=raw,
        n_unique=len(unique_ids),
        unique_sample_ids=tuple(unique_ids),
        duplicates_dropped=max(0, raw - len(unique_ids)),
    )


# ---------------------------------------------------------------------------
# ② 夸大表述门（验收①：三例只有两例关联不能写因果提升 67%）
# ---------------------------------------------------------------------------

GATE_ALLOWED = "allowed"
GATE_REJECTED = "rejected"

#: 因果断言由 M-06 扫描器检出的理由码。
REASON_CAUSAL_ASSERTION = "causal_assertion_detected"
#: 因果/成效措辞与百分比数字同现（「提升 67%」族）——本面只有相关性证据。
REASON_CAUSAL_PERCENTAGE = "causal_percentage_claim"
#: 百分比建立在部分关联子集上（n_linked < n_denominator；分母未随行）。
REASON_PARTIAL_LINKAGE_PERCENT = "percentage_over_partial_linkage"

#: 因果/成效措辞族（呈现层补充词表，封闭；与 D-05 ``FORBIDDEN_CLAIM_TERMS``
#: 互补——「导致/caused/成功率」族已在 D-05 冻结词表，本表只收「提升/有效」族。
#: 两表并集参与文本扫描，本表不改动 D-05 冻结词表）。
CAUSAL_EFFECT_TERMS: tuple[str, ...] = (
    "提升",
    "提高了",
    "提高",
    "改善",
    "增长",
    "见效",
    "起效",
    "有效",
    "improve",
    "increase",
    "boost",
    "effective",
    "works",
)

#: 百分比数字形态（「67%」「67 %」「3.5%」）。
_PERCENT_RE = re.compile(r"\d+(?:\.\d+)?\s*%")

#: 数值面文本扫描只覆盖**系统组写的 claim 面**（封闭键集）；用户自述内容
#: （如 goal 标题）不是系统宣称，不进本门——避免把用户自己的话判成系统夸大。
SYSTEM_CLAIM_KEYS: frozenset[str] = frozenset(
    {"claim", "note", "direction", "role", "band", "action_key", "qualifiers"}
)


@dataclass(frozen=True)
class PresentationGateVerdict:
    """表述门判定（封闭二值 + 封闭理由词表；allowed 恒 reasons=()）。"""

    allowed: bool
    reasons: tuple[str, ...] = ()

    @property
    def status(self) -> str:
        return GATE_ALLOWED if self.allowed else GATE_REJECTED

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PRESENTATION_SCHEMA_VERSION,
            "status": self.status,
            "reasons": list(self.reasons),
        }


def _claim_violations(text: str, *, n_linked: int, n_denominator: int) -> tuple[str, ...]:
    """单条 claim 文本的数值面扫描（因果措辞 × 百分比 × 部分关联）。"""
    violations: list[str] = []
    has_percent = _PERCENT_RE.search(text) is not None
    has_causal_effect = any(term in text for term in CAUSAL_EFFECT_TERMS)
    has_d05_forbidden = any(term in text for term in FORBIDDEN_CLAIM_TERMS)
    if has_d05_forbidden:
        violations.append(REASON_CAUSAL_ASSERTION)
    if has_percent and has_causal_effect:
        # 因果/成效措辞 + 百分比：本面证据只有相关性，无论分母是否齐全都拒绝。
        violations.append(REASON_CAUSAL_PERCENTAGE)
    elif has_percent and (n_denominator <= 0 or n_linked < n_denominator):
        # 纯百分比但分母是部分关联子集（三例两例 → 任何 % 都缺分母正当性）；
        # 分母为零宣称百分比本身就是假精确。
        violations.append(REASON_PARTIAL_LINKAGE_PERCENT)
    if has_causal_effect and not has_percent:
        # 无百分比的因果措辞：M-06/D-05 禁词已覆盖「导致/使得」族；「提升/有效」
        # 族不带数字时同样不得出现（相关面不写成效）。
        violations.append(REASON_CAUSAL_ASSERTION)
    return tuple(violations)


def exaggeration_gate(
    payload: Any,
    *,
    n_linked: int,
    n_denominator: int,
    claim_texts: Sequence[str] = (),
) -> PresentationGateVerdict:
    """夸大表述门（验收①的机制化；可失败——违例即 rejected + 封闭理由）。

    三层检查（任一命中即拒绝，理由并集）：
    1. M-06 ``scan_output_for_causal_assertions(payload)``：字段名/``causal_claim``
       值/``claim`` 文本的因果断言（单一权威，零重实现）；
    2. 显式 ``claim_texts`` 数值面：因果/成效措辞 × 百分比同现 →
       ``causal_percentage_claim``（「关联提升 67%」族结构性禁止）；
    3. 百分比建立在部分关联子集（``n_linked < n_denominator``）→
       ``percentage_over_partial_linkage``（分母必须随行）。

    ``n_denominator <= 0`` 且出现百分比：分母为零宣称百分比本身就是假精确，
    按 partial-linkage 拒绝。文本面只扫系统组写字段（:data:`SYSTEM_CLAIM_KEYS`
    键下的值）与显式 ``claim_texts``——用户自述内容（goal 标题等）不是系统
    宣称，不进本门。
    """
    reasons: list[str] = []
    m06_violations = scan_output_for_causal_assertions(payload)
    if m06_violations:
        reasons.append(REASON_CAUSAL_ASSERTION)
    for text in claim_texts:
        reasons.extend(_claim_violations(str(text), n_linked=n_linked, n_denominator=n_denominator))
    # 系统组写 claim 面的数值面扫描（防御纵深；用户内容键不扫）。
    for text in _system_claim_strings(payload):
        reasons.extend(_claim_violations(text, n_linked=n_linked, n_denominator=n_denominator))
    deduped = tuple(dict.fromkeys(reasons))
    return PresentationGateVerdict(allowed=not deduped, reasons=deduped)


def _system_claim_strings(node: Any, *, key: str | None = None) -> Iterable[str]:
    if isinstance(node, Mapping):
        for child_key, value in node.items():
            child_key_str = str(child_key)
            yield from _system_claim_strings(value, key=child_key_str)
    elif isinstance(node, (list, tuple, set, frozenset)):
        for item in node:
            yield from _system_claim_strings(item, key=key)
    elif isinstance(node, str) and key in SYSTEM_CLAIM_KEYS:
        yield node


# ---------------------------------------------------------------------------
# ③ 理解宣称门（验收②前半：无数据不出「充分理解」）
# ---------------------------------------------------------------------------

#: 「充分理解」族宣称词（封闭；呈现面在门未放行时出现即违例）。
UNDERSTANDING_OVERCLAIM_TERMS: tuple[str, ...] = (
    "充分理解",
    "完全理解",
    "彻底理解",
    "很懂你",
    "fully understood",
    "completely understood",
    "complete understanding",
)

#: 理由码（封闭）。
REASON_NO_DATA_NO_CLAIM = "no_data_no_claim"
REASON_INCOMPLETE_EVIDENCE = "incomplete_evidence_missing_or_censored"


def understanding_claim_gate(*, samples: int, missing: int = 0, censored: int = 0) -> PresentationGateVerdict:
    """理解宣称门：只有**完整**观察（samples>0 且 missing=censored=0）才放行。

    - ``samples <= 0`` → ``no_data_no_claim``（无数据连宣称的资格都没有）；
    - 有样本但存在 missing/censored → ``incomplete_evidence_missing_or_censored``
      （缺失/删失显式在册时，「充分理解」在语义上不可成立）；
    - 完整数据 → 放行（放行 ≠ 面上会写：本服务任何档位都不产理解宣称，
      放行只表示**不被本门禁止**；censored 是显式不结论，不是失败）。
    """
    if int(samples) <= 0:
        return PresentationGateVerdict(allowed=False, reasons=(REASON_NO_DATA_NO_CLAIM,))
    if int(missing) > 0 or int(censored) > 0:
        return PresentationGateVerdict(allowed=False, reasons=(REASON_INCOMPLETE_EVIDENCE,))
    return PresentationGateVerdict(allowed=True)


def find_understanding_overclaims(payload: Any) -> list[str]:
    """扫描 payload 中全部字符串的「充分理解」族违例（路径列表；空=干净）。"""
    hits: list[str] = []

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                child = f"{path}.{key}" if path else str(key)
                _walk(key, child)
                _walk(value, child)
        elif isinstance(node, (list, tuple)):
            for index, item in enumerate(node):
                _walk(item, f"{path}[{index}]")
        elif isinstance(node, str):
            lowered = node.lower()
            if any(term in node or term in lowered for term in UNDERSTANDING_OVERCLAIM_TERMS):
                hits.append(path)

    _walk(payload, "")
    return hits


# ---------------------------------------------------------------------------
# ④ 单主建议信封（验收③：一条观察 ≤ 一个主建议；可拒绝且零惩罚）
# ---------------------------------------------------------------------------

#: 拒绝惩罚的冻结常量：拒绝一个建议对奖励的影响 = 无。
REJECT_PENALTY_NONE = "none"
#: 拒绝 affordance 恒存在（结构冻结，不是每卡可变字段）。
USER_CAN_REJECT = True


@dataclass(frozen=True)
class SuggestionEnvelope:
    """一条观察的主建议信封（≤1 主建议；拒绝路径一等公民、零惩罚）。

    ``primary=None`` 表示该观察不带建议（观察可以只有事实——不硬凑行动项）。
    """

    observation_id: str
    primary: Mapping[str, Any] | None
    user_can_reject: bool = USER_CAN_REJECT
    reject_penalty: str = REJECT_PENALTY_NONE

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PRESENTATION_SCHEMA_VERSION,
            "observation_id": self.observation_id,
            "primary": dict(self.primary) if self.primary is not None else None,
            "user_can_reject": self.user_can_reject,
            "reject_penalty": self.reject_penalty,
        }


def build_suggestion_envelope(*, observation_id: str, candidates: Sequence[Mapping[str, Any]]) -> SuggestionEnvelope:
    """候选建议序列 → 信封。多于一个主建议即 ValueError（fail-loud，不静默取首个）。"""
    if len(candidates) > 1:
        raise ValueError(
            f"observation {observation_id!r} produced {len(candidates)} primary suggestions; "
            "at most one is allowed (V4-D05: 一条观察≤一个主建议)"
        )
    primary = candidates[0] if candidates else None
    return SuggestionEnvelope(observation_id=observation_id, primary=primary)


# ---------------------------------------------------------------------------
# ⑤ 已删来源不复用（验收②后半：撤回/删除源从呈现面排除，unaffected 保留）
# ---------------------------------------------------------------------------

REASON_CARD_WITHOUT_VALID_EVIDENCE = "card_without_valid_evidence"


@dataclass(frozen=True)
class FilteredRefs:
    """来源引用过滤结果（excluded 显式在册；unaffected 一等保留——I05 同律）。"""

    kept: tuple[str, ...]
    excluded: tuple[str, ...]

    @property
    def has_valid_evidence(self) -> bool:
        return bool(self.kept)

    def to_dict(self) -> dict[str, Any]:
        return {"kept": list(self.kept), "excluded": list(self.excluded)}


def exclude_withdrawn_refs(refs: Sequence[str], withdrawn: Sequence[str]) -> FilteredRefs:
    """从呈现引用中排除已删除/已撤回来源（精确身份匹配；unaffected 保留）。

    身份 = ``<type>:<id>`` 字符串的**整串相等**（I05 ``SourcePointer`` 同款纪律：
    值相同、类型不同不构成同源，绝不连坐）。
    """
    withdrawn_set = {str(ref) for ref in withdrawn}
    kept = tuple(ref for ref in refs if str(ref) not in withdrawn_set)
    excluded = tuple(ref for ref in refs if str(ref) in withdrawn_set)
    return FilteredRefs(kept=kept, excluded=excluded)


# ---------------------------------------------------------------------------
# ⑥ 回访记录（objective：回访能证明上次建议是否相关，而非套模板）
# ---------------------------------------------------------------------------

#: 回访相关性封闭词表（每值可追溯到真实事件或显式不结论）。
RELEVANCE_NO_PRIOR = "no_prior_suggestion"
RELEVANCE_REJECTED_BY_USER = "rejected_by_user"
RELEVANCE_RELATED_OUTCOME = "related_outcome_observed"
RELEVANCE_ACTED_AWAITING_OUTCOME = "acted_awaiting_outcome"
RELEVANCE_AWAITING_USER = "awaiting_user"
RELEVANCE_CENSORED_WINDOW_CLOSED = "censored_window_closed"
RELEVANCE_CENSORED_USER_CHURNED = "censored_user_churned"

REVISIT_RELEVANCES: frozenset[str] = frozenset(
    {
        RELEVANCE_NO_PRIOR,
        RELEVANCE_REJECTED_BY_USER,
        RELEVANCE_RELATED_OUTCOME,
        RELEVANCE_ACTED_AWAITING_OUTCOME,
        RELEVANCE_AWAITING_USER,
        RELEVANCE_CENSORED_WINDOW_CLOSED,
        RELEVANCE_CENSORED_USER_CHURNED,
    }
)

#: 用户显式拒绝族（拒绝 = 用户的一等决定：不再证明「相关」，且零惩罚）。
_REJECTED_RESPONSES: frozenset[str] = frozenset({"rejected"})
#: 已行动族（accepted/edited/started：接受了建议但结果未回）。
_ACTED_RESPONSES: frozenset[str] = frozenset({"accepted", "edited", "started"})


@dataclass(frozen=True)
class RevisitRecord:
    """上次建议的回访记录（全部字段可追溯到真实事件 id / 计数；零模板编造）。

    ``proves_relevance`` 只有 ``related_outcome_observed`` 才可为 True，且必须
    携带 ≥1 个去重后样本身份（:func:`revisit_evidence_integrity` 钉死）——
    「相关」不能由文案模板自封。
    """

    decision_id: str
    intervention_type: str
    friction_tag: str
    shown_at: str | None
    response: str | None
    relevance: str
    n_outcome_samples_raw: int
    n_outcome_samples_unique: int
    sample_ids: tuple[str, ...] = ()
    window_status: str | None = None
    proves_relevance: bool = False
    reward_consequence: str = REJECT_PENALTY_NONE

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PRESENTATION_SCHEMA_VERSION,
            "decision_id": self.decision_id,
            "intervention_type": self.intervention_type,
            "friction_tag": self.friction_tag,
            "shown_at": self.shown_at,
            "response": self.response,
            "relevance": self.relevance,
            "n_outcome_samples_raw": self.n_outcome_samples_raw,
            "n_outcome_samples_unique": self.n_outcome_samples_unique,
            "sample_ids": list(self.sample_ids),
            "window_status": self.window_status,
            "proves_relevance": self.proves_relevance,
            "reward_consequence": self.reward_consequence,
        }


def build_revisit_record(
    *,
    decision_id: str,
    intervention_type: str,
    friction_tag: str,
    shown_at: datetime | None,
    response: str | None,
    outcome_ids: Sequence[str],
    observation_status: ObservationStatus | str | None,
) -> RevisitRecord:
    """真实事件面 → 回访记录（判定顺序确定性短路；窗口/删失语义消费 D-05 权威）。

    ``observation_status`` 必须来自 D-05 ``resolve_observation_status``（唯一
    权威）或 None（无 exposure）。判定顺序：

    1. 无 decision_id/exposure → ``no_prior_suggestion``（不编造回访）；
    2. 用户显式拒绝 → ``rejected_by_user``（用户的「不相关」判定最高；此时
       即便有链接 outcome 也不改写用户决定，计数仍如实随行）；
    3. 去重后样本身份 ≥1 → ``related_outcome_observed``（相关性由真实链接证明）；
    4. D-05 观察窗未收口：已行动 → ``acted_awaiting_outcome``；未行动 →
       ``awaiting_user``；
    5. 窗口收口无结果 → censored 两态（显式不结论，绝不是失败）。
    """
    has_prior = bool(str(decision_id or "")) and observation_status is not None
    dedup = dedupe_outcome_samples(decision_id=decision_id or "", outcome_ids=outcome_ids)

    if not has_prior:
        return RevisitRecord(
            decision_id=str(decision_id or ""),
            intervention_type=str(intervention_type or ""),
            friction_tag=str(friction_tag or ""),
            shown_at=shown_at.isoformat() if shown_at else None,
            response=None,
            relevance=RELEVANCE_NO_PRIOR,
            n_outcome_samples_raw=0,
            n_outcome_samples_unique=0,
            sample_ids=(),
        )

    response_value = str(response) if response else None
    if response_value in _REJECTED_RESPONSES:
        return RevisitRecord(
            decision_id=str(decision_id),
            intervention_type=str(intervention_type),
            friction_tag=str(friction_tag),
            shown_at=shown_at.isoformat() if shown_at else None,
            response=response_value,
            relevance=RELEVANCE_REJECTED_BY_USER,
            n_outcome_samples_raw=dedup.n_raw,
            n_outcome_samples_unique=dedup.n_unique,
            sample_ids=dedup.unique_sample_ids,
            reward_consequence=REJECT_PENALTY_NONE,
        )

    if dedup.n_unique > 0:
        return RevisitRecord(
            decision_id=str(decision_id),
            intervention_type=str(intervention_type),
            friction_tag=str(friction_tag),
            shown_at=shown_at.isoformat() if shown_at else None,
            response=response_value,
            relevance=RELEVANCE_RELATED_OUTCOME,
            n_outcome_samples_raw=dedup.n_raw,
            n_outcome_samples_unique=dedup.n_unique,
            sample_ids=dedup.unique_sample_ids,
            window_status=_status_value(observation_status),
            proves_relevance=True,
        )

    status_value = _status_value(observation_status)
    if status_value in ("censored_window_closed", "censored_user_churned"):
        relevance = (
            RELEVANCE_CENSORED_WINDOW_CLOSED
            if status_value == "censored_window_closed"
            else RELEVANCE_CENSORED_USER_CHURNED
        )
        return RevisitRecord(
            decision_id=str(decision_id),
            intervention_type=str(intervention_type),
            friction_tag=str(friction_tag),
            shown_at=shown_at.isoformat() if shown_at else None,
            response=response_value,
            relevance=relevance,
            n_outcome_samples_raw=dedup.n_raw,
            n_outcome_samples_unique=0,
            window_status=status_value,
        )
    # 窗口未收口（censored_not_yet_due / observed-without-linked-outcome 等）：
    # 按用户是否已行动二分。
    if response_value in _ACTED_RESPONSES:
        relevance = RELEVANCE_ACTED_AWAITING_OUTCOME
    else:
        relevance = RELEVANCE_AWAITING_USER
    return RevisitRecord(
        decision_id=str(decision_id),
        intervention_type=str(intervention_type),
        friction_tag=str(friction_tag),
        shown_at=shown_at.isoformat() if shown_at else None,
        response=response_value,
        relevance=relevance,
        n_outcome_samples_raw=dedup.n_raw,
        n_outcome_samples_unique=0,
        window_status=status_value,
    )


def _status_value(observation_status: ObservationStatus | str | None) -> str | None:
    if observation_status is None:
        return None
    return str(getattr(observation_status, "value", observation_status))


def revisit_evidence_integrity(record: RevisitRecord) -> bool:
    """回访记录的证据完整性（「非套模板」的结构钉）。

    - ``related_outcome_observed`` 必须携带 decision_id + ≥1 个去重样本 id；
    - ``no_prior_suggestion`` 不得携带任何样本身份/响应（无事件就没有回访）；
    - 其余状态不得宣称 ``proves_relevance``。
    """
    if record.relevance not in REVISIT_RELEVANCES:
        return False
    if record.relevance == RELEVANCE_RELATED_OUTCOME:
        return bool(record.decision_id) and record.n_outcome_samples_unique >= 1
    if record.relevance == RELEVANCE_NO_PRIOR:
        return not record.sample_ids and record.response is None
    return not record.proves_relevance


__all__ = [
    "PRESENTATION_SCHEMA_VERSION",
    "GATE_ALLOWED",
    "GATE_REJECTED",
    "REASON_CAUSAL_ASSERTION",
    "REASON_CAUSAL_PERCENTAGE",
    "REASON_PARTIAL_LINKAGE_PERCENT",
    "REASON_NO_DATA_NO_CLAIM",
    "REASON_INCOMPLETE_EVIDENCE",
    "REASON_CARD_WITHOUT_VALID_EVIDENCE",
    "CAUSAL_EFFECT_TERMS",
    "UNDERSTANDING_OVERCLAIM_TERMS",
    "REJECT_PENALTY_NONE",
    "USER_CAN_REJECT",
    "SampleDedup",
    "PresentationGateVerdict",
    "SuggestionEnvelope",
    "FilteredRefs",
    "RevisitRecord",
    "REVISIT_RELEVANCES",
    "RELEVANCE_NO_PRIOR",
    "RELEVANCE_REJECTED_BY_USER",
    "RELEVANCE_RELATED_OUTCOME",
    "RELEVANCE_ACTED_AWAITING_OUTCOME",
    "RELEVANCE_AWAITING_USER",
    "RELEVANCE_CENSORED_WINDOW_CLOSED",
    "RELEVANCE_CENSORED_USER_CHURNED",
    "presentation_sample_id",
    "dedupe_outcome_samples",
    "exaggeration_gate",
    "understanding_claim_gate",
    "find_understanding_overclaims",
    "build_suggestion_envelope",
    "exclude_withdrawn_refs",
    "build_revisit_record",
    "revisit_evidence_integrity",
]
