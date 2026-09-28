"""V4-I02 · optional-history utility gate（阶段二效用门，合法历史的效用筛选）。

定位（v4/04_tasks/cards/V4-I02.md + v4/03_intelligence/MEMORY_UTILITY_AND_CONFLICT.md）：
在原 Context Compiler 的 M-03 硬预筛（``memory_retrieval_prefilter``，阶段一：
owner/status/TTL/scope/purpose/sensitivity 合法性）**之后**，对剩余合法 optional
history（episodic 排序面）做阶段二效用打分与筛选。mandatory context（当前目标/
显式约束/授权）不经本门——本门只作用于 optional history。

病根与靶（B03 冻结负基线）：A-08 修后 full 0.45 反被 no_memory 0.55 反超，坏经验
污染（历史失败错迁移，FIX52：异类型失败拉向 skill/difficulty）是主病根之一。本门
抑制该污染：**旧失败只在同类型/有效时间影响候选**——异类型失败经验被硬拒
（negative_transfer_hard），过期失败被 stale 惩罚压到阈下。

打分公式（可解释规则，不是概率、不是价值网络）：
``score = relevance + outcome + confirmed_bonus + decision_relevance
        − conflict_penalty − stale_penalty − token_cost``

outcome 权重逐项 = B03 冻结 ``frozen_utility.json`` 的 ``utility_frozen.weights``
（与 A-08 aurora_ablation_metrics.v1 一致；``FROZEN_OUTCOME_WEIGHTS`` 有冻结锚
单测）。V4 规则权重为本模块常量（开发集冻结点），改动必须过证据。

censored ≠ negative（智能文档 §线上与离线分工）：无 outcome 信号的普通记忆
（无 due_at 的非承诺行）outcome 记 0，不因"没有成功标记"被当失败。

反 gaming（验收②）：required-memory 场景（query 显式要求召回历史）全拒 = recall
miss，``passed=False``；空选择 precision 按分母策略输出 N/A（``None``，不是 0%
更不是 100%）。接线侧（context_pack.build）遇 ``passed=False`` 回退 V3 预筛后
路径保召回并如实登记 miss——筛选器不能靠"全拒用"刷干净。

合法性边界（验收③）：本门**不拥有**合法性判断——已删/越权/过期/错 scope 由
M-03 预筛排除，本门只消费预筛 allowed 列表，无任何复活路径（选择集 ⊆ 输入集）。

开关：``settings.ENABLE_MEMORY_UTILITY_GATE``（默认 False，灰度可开）。关 = 零
行为变化（不调用、无 metadata），V3 路径与数据不受影响。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger

from app.core.business_metrics import MEMORY_UTILITY_GATE_DECISIONS_TOTAL
from app.core.time_utils import ensure_naive_utc

MEMORY_UTILITY_GATE_VERSION = "memory-v4.i02.v1"

# ---------------------------------------------------------------------------
# 1. 冻结权重
# ---------------------------------------------------------------------------

#: B03 冻结 ``v4/evidence/V4-B03/frozen_utility.json`` → utility_frozen.weights
#: （逐项 = A-08 aurora_ablation_metrics.v1；冻结锚单测对表，禁止静默改值）。
FROZEN_OUTCOME_WEIGHTS: dict[str, float] = {
    "resolved_episode": 1.0,
    "unresolved_episode": -1.0,
    "wrong_followed_decision": -0.4,
    "question": -0.15,
    "control_intrusion": -0.6,
}

#: V4 可解释规则权重（本模块 = 开发集冻结点；初值待 D 臂基线测量，非普适最优）。
WEIGHT_RELEVANCE: float = 1.0
WEIGHT_DECISION_RELEVANCE: float = 0.3
WEIGHT_CONFIRMED_BONUS: float = 0.3
PENALTY_CONFLICT_PER_CORRECTION: float = 0.5
MAX_CONFLICT_PENALTY: float = 1.0
STALE_PENALTY_FREE_DAYS: float = 30.0
STALE_PENALTY_FULL_AT_DAYS: float = 90.0
TOKEN_COST_DIVISOR: float = 400.0

#: 推断提取行不算用户确认（与 context_builder._serialize_stage34_episodic_memory
#: 的 ``user_confirmed`` 判定同口径）。
INFERRED_EXTRACTION_LANE = "inferred_extraction"

#: 负迁移 marker tag 词汇（closed；与冻结权重键同名）。现有写入方不带这些
#: tag 时对应权重不生效——不发明隐藏推断。
TAG_WRONG_FOLLOWED_DECISION = "wrong_followed_decision"
TAG_QUESTION = "question"
TAG_CONTROL_INTRUSION = "control_intrusion"

#: 候选类型锚 tag 约定：``task_type:<value>`` / ``domain:<value>``。
TAG_TASK_TYPE_PREFIX = "task_type:"
TAG_DOMAIN_PREFIX = "domain:"

#: 阈下拒绝 + TopK 预算（智能文档：初值可选历史 ≤6 条，待基线测量）。
DEFAULT_MIN_SCORE: float = 0.0
DEFAULT_TOP_K: int = 6

#: required-memory 场景 marker（query 显式要求召回历史；closed 子串词表）。
REQUIRED_MEMORY_MARKERS: tuple[str, ...] = (
    "上次",
    "之前",
    "以前",
    "昨天",
    "上周",
    "记得",
    "我说过",
    "历史",
    "回顾",
)

_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


# ---------------------------------------------------------------------------
# 2. 候选特征（从既有列派生；不要求新写入面）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UtilityFeatures:
    """一条 optional-history 候选的效用门输入特征（全部从既有列/markers 派生）。"""

    item_id: str
    content: str
    resolved: bool = False
    failed: bool = False
    wrong_followed: bool = False
    question: bool = False
    control_intrusion: bool = False
    user_confirmed: bool = False
    correction_count: int = 0
    age_days: float = 0.0
    type_anchors: frozenset[str] = field(default_factory=frozenset)

    @property
    def token_estimate(self) -> int:
        """确定性 token 估计（len//4，context_pack.estimate_tokens 同级近似）。"""
        return max(1, len(self.content) // 4)


def _lexical_terms(text: str) -> frozenset[str]:
    """确定性词法项：latin/digit 词（≥2 字符）+ CJK 单字。零依赖、可解释。"""
    lowered = text.lower()
    terms: set[str] = set(_TOKEN_RE.findall(lowered))
    terms.update(ch for ch in lowered if _CJK_RE.match(ch))
    return frozenset(terms)


def _relevance(query_terms: frozenset[str], candidate_terms: frozenset[str]) -> float:
    """query 项被候选覆盖率 ∈ [0,1]；无 query 项 → 0（纯效用序，不掺伪相关）。"""
    if not query_terms:
        return 0.0
    return min(1.0, len(query_terms & candidate_terms) / len(query_terms))


def _type_anchors_from_tags(tags: frozenset[str]) -> frozenset[str]:
    anchors: set[str] = set()
    for tag in tags:
        for prefix in (TAG_TASK_TYPE_PREFIX, TAG_DOMAIN_PREFIX):
            if tag.startswith(prefix):
                value = tag[len(prefix) :].strip().lower()
                if value:
                    anchors.add(value)
    return frozenset(anchors)


def extract_utility_features(item: Any, *, now: datetime | None = None) -> UtilityFeatures:
    """从既有 episodic 形（ORM 或鸭子类型）派生 ``UtilityFeatures``。

    派生口径：
    - ``resolved``：``resolved_at`` 非空（承诺型 episode 已解决 → +1.0）；
    - ``failed``：承诺已到期未解决（``due_at`` 已过且无 ``resolved_at``）——
      censored（未到期/无承诺）不算失败；
    - marker tags：``wrong_followed_decision`` / ``question`` / ``control_intrusion``；
    - ``user_confirmed``：``source_lane != inferred_extraction``；
    - 类型锚：tags 的 ``task_type:*`` / ``domain:*``。
    """
    tags_raw = getattr(item, "tags", None) or []
    tags = frozenset(str(tag or "").strip().lower() for tag in tags_raw if str(tag or "").strip())
    resolved_at = getattr(item, "resolved_at", None)
    due_at = getattr(item, "due_at", None)
    resolved = resolved_at is not None
    failed = False
    if due_at is not None and not resolved:
        due_naive = ensure_naive_utc(due_at)
        now_naive = ensure_naive_utc(now) or ensure_naive_utc(datetime.now())
        if due_naive is not None and now_naive is not None and due_naive < now_naive:
            failed = True
    occurred = getattr(item, "occurred_at", None) or getattr(item, "created_at", None)
    age_days = 0.0
    occurred_naive = ensure_naive_utc(occurred) if occurred is not None else None
    now_naive = ensure_naive_utc(now) or ensure_naive_utc(datetime.now())
    if occurred_naive is not None and now_naive is not None:
        age_days = max(0.0, (now_naive - occurred_naive).total_seconds() / 86400.0)
    content = str(getattr(item, "summary", "") or "")
    return UtilityFeatures(
        item_id=str(getattr(item, "id", "") or ""),
        content=content,
        resolved=resolved,
        failed=failed,
        wrong_followed=TAG_WRONG_FOLLOWED_DECISION in tags,
        question=TAG_QUESTION in tags,
        control_intrusion=TAG_CONTROL_INTRUSION in tags,
        user_confirmed=str(getattr(item, "source_lane", "") or "").strip() != INFERRED_EXTRACTION_LANE,
        correction_count=int(getattr(item, "correction_count", 0) or 0),
        age_days=age_days,
        type_anchors=_type_anchors_from_tags(tags),
    )


# ---------------------------------------------------------------------------
# 3. 打分与判定（纯核心）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UtilityGateDecision:
    """单条候选的选/拒用决定（含原因；metadata-only，零正文）。"""

    item_id: str
    selected: bool
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class UtilityGateResult:
    """效用门结果：决定列表 + required-memory 召回判定 + 反 gaming 口径。"""

    decisions: tuple[UtilityGateDecision, ...]
    selected_ids: frozenset[str]
    candidate_count: int
    required_memory_detected: bool
    #: None = 非 required-memory 场景（不判定）；False = 需要召回但全拒（miss）。
    required_memory_recall: bool | None

    @property
    def selected_count(self) -> int:
        return len(self.selected_ids)

    @property
    def passed(self) -> bool:
        """全部拒用不能过门：required-memory 场景空选择 = recall miss → False。"""
        if self.required_memory_detected and self.selected_count == 0:
            return False
        return True

    @property
    def precision(self) -> float | None:
        """分母策略（B03 denominator_policy）：空选择 precision = N/A（None）。

        本门无 ground truth，不给伪 precision 数——离线评测（B03 四臂协议）拥有
        precision 数值；这里只保证「空选择不得表述为 0% 或 100%」。
        """
        if not self.decisions or self.selected_count == 0:
            return None
        return round(self.selected_count / self.candidate_count, 6)

    def to_metric_payload(self) -> dict[str, Any]:
        verdict = "no_candidates"
        if self.candidate_count:
            verdict = "selected"
            if self.selected_count == 0:
                verdict = "required_memory_recall_miss" if self.required_memory_detected else "all_rejected"
        return {
            "version": MEMORY_UTILITY_GATE_VERSION,
            "candidate_count": self.candidate_count,
            "selected_count": self.selected_count,
            "decisions": [
                {
                    "item_id": decision.item_id,
                    "selected": decision.selected,
                    "score": round(decision.score, 6),
                    "reasons": list(decision.reasons),
                }
                for decision in self.decisions
            ],
            "required_memory_detected": self.required_memory_detected,
            "required_memory_recall": self.required_memory_recall,
            "passed": self.passed,
            "precision": self.precision,
            "verdict": verdict,
        }


def required_memory_query(query_text: str | None) -> bool:
    """query 是否显式要求召回历史（closed 子串词表，确定性）。"""
    text = str(query_text or "").strip().lower()
    if not text:
        return False
    return any(marker in text for marker in REQUIRED_MEMORY_MARKERS)


def score_candidate(
    features: UtilityFeatures,
    *,
    query_terms: frozenset[str],
) -> tuple[float, tuple[str, ...]]:
    """效用打分（可解释；返回 (score, factor reasons)。不做硬拒判定）。"""
    reasons: list[str] = []
    relevance = _relevance(query_terms, _lexical_terms(features.content))
    if query_terms:
        reasons.append(f"relevance:{round(relevance, 3)}")

    # outcome：冻结权重逐项；censored（无信号）记 0。
    outcome = 0.0
    if features.resolved:
        outcome += FROZEN_OUTCOME_WEIGHTS["resolved_episode"]
        reasons.append("outcome:resolved_episode")
        # decision_relevance：已解决经验携带可复用决策信息。
        outcome += WEIGHT_DECISION_RELEVANCE
    if features.failed:
        outcome += FROZEN_OUTCOME_WEIGHTS["unresolved_episode"]
        reasons.append("outcome:unresolved_episode")
    if features.wrong_followed:
        outcome += FROZEN_OUTCOME_WEIGHTS["wrong_followed_decision"]
        reasons.append("outcome:wrong_followed_decision")
    if features.question:
        outcome += FROZEN_OUTCOME_WEIGHTS["question"]
        reasons.append("outcome:question")
    if features.control_intrusion:
        outcome += FROZEN_OUTCOME_WEIGHTS["control_intrusion"]
        reasons.append("outcome:control_intrusion")

    if features.user_confirmed:
        outcome += WEIGHT_CONFIRMED_BONUS
        reasons.append("confirmed_bonus")

    conflict = min(MAX_CONFLICT_PENALTY, PENALTY_CONFLICT_PER_CORRECTION * features.correction_count)
    if conflict:
        reasons.append(f"conflict_penalty:{round(conflict, 3)}")
    stale = 0.0
    if features.age_days > STALE_PENALTY_FREE_DAYS:
        span = max(1.0, STALE_PENALTY_FULL_AT_DAYS - STALE_PENALTY_FREE_DAYS)
        stale = min(1.0, (features.age_days - STALE_PENALTY_FREE_DAYS) / span)
        reasons.append(f"stale_penalty:{round(stale, 3)}")
    token_cost = features.token_estimate / TOKEN_COST_DIVISOR
    reasons.append(f"token_cost:{round(token_cost, 3)}")

    score = WEIGHT_RELEVANCE * relevance + outcome - conflict - stale - token_cost
    return score, tuple(reasons)


def evaluate_history_utility(
    features_list: list[UtilityFeatures],
    *,
    query_text: str | None = None,
    current_type_anchors: frozenset[str] = frozenset(),
    min_score: float = DEFAULT_MIN_SCORE,
    top_k: int = DEFAULT_TOP_K,
) -> UtilityGateResult:
    """效用门纯核心：异类型失败硬拒（FIX52）→ 阈下拒 → TopK。

    选择集 ⊆ 输入集（无复活路径）；输入应为 M-03 预筛 allowed（合法性由
    阶段一拥有，本门不重复也不推翻）。时间特征（age_days）已折入
    ``UtilityFeatures``（由 ``extract_utility_features`` 派生）。
    """
    query_terms = _lexical_terms(str(query_text or ""))
    is_required = required_memory_query(query_text)

    scored: list[tuple[UtilityFeatures, float, tuple[str, ...]]] = []
    decisions: list[UtilityGateDecision] = []
    for features in features_list:
        score, reasons = score_candidate(features, query_terms=query_terms)
        # FIX52 硬门：异类型失败不拉向 skill/difficulty——候选声明了类型锚、
        # 当次也声明了类型锚且零交集的失败/错跟随经验，直接拒用（旧失败只在
        # 同类型/有效时间影响候选）。
        negative = features.failed or features.wrong_followed
        cross_type = (
            negative
            and bool(features.type_anchors)
            and bool(current_type_anchors)
            and not (features.type_anchors & current_type_anchors)
        )
        if cross_type:
            decisions.append(
                UtilityGateDecision(
                    item_id=features.item_id,
                    selected=False,
                    score=score,
                    reasons=(*reasons, "negative_transfer_cross_type"),
                )
            )
            _inc_gate("rejected", "negative_transfer_cross_type")
            continue
        if score <= min_score:
            # 严格正值才入选：零信号（无相关性/无结果/无确认）= 纯 token 成本，
            # 宁可省掉不确定历史（智能文档 §两阶段选择）。
            decisions.append(
                UtilityGateDecision(
                    item_id=features.item_id,
                    selected=False,
                    score=score,
                    reasons=(*reasons, "utility_low_score"),
                )
            )
            _inc_gate("rejected", "utility_low_score")
            continue
        scored.append((features, score, reasons))

    scored.sort(key=lambda entry: (-entry[1], entry[0].item_id))
    selected: list[tuple[UtilityFeatures, float, tuple[str, ...]]] = scored[: max(0, int(top_k))]
    for index, (features, score, reasons) in enumerate(scored):
        if index < len(selected):
            decisions.append(UtilityGateDecision(item_id=features.item_id, selected=True, score=score, reasons=reasons))
            _inc_gate("selected", "score_ok")
        else:
            decisions.append(
                UtilityGateDecision(
                    item_id=features.item_id, selected=False, score=score, reasons=(*reasons, "top_k_cap")
                )
            )
            _inc_gate("rejected", "top_k_cap")

    # 决定按输入序输出（确定性；调用方按 item_id 对表）。
    order = {features.item_id: index for index, features in enumerate(features_list)}
    decisions.sort(key=lambda decision: order.get(decision.item_id, len(order)))

    selected_ids = frozenset(features.item_id for features, _, _ in selected)
    recall: bool | None = None
    if is_required:
        recall = bool(selected_ids)
    return UtilityGateResult(
        decisions=tuple(decisions),
        selected_ids=selected_ids,
        candidate_count=len(features_list),
        required_memory_detected=is_required,
        required_memory_recall=recall,
    )


# ---------------------------------------------------------------------------
# 4. context_pack 接线适配（RankedItem 面；保序输出）
# ---------------------------------------------------------------------------


def apply_history_utility_gate(
    ranked_items: list[Any],
    *,
    query_text: str | None = None,
    now: datetime | None = None,
    current_type_anchors: frozenset[str] = frozenset(),
    min_score: float = DEFAULT_MIN_SCORE,
    top_k: int = DEFAULT_TOP_K,
) -> tuple[list[Any], dict[str, Any]]:
    """对 ranked optional-history（``entry.item`` / ``entry.score`` 鸭子类型）
    执行效用门，返回 ``(kept_items, metadata)``。

    metadata 为 metadata-only 观测面（id/reason/score，零正文回灌——metadata
    经 ``to_prompt_context`` 可进 prompt）。调用方契约：输入必须是 M-03 预筛
    后的 allowed 列表；``passed=False`` 时调用方回退全量输入并登记 bypass。
    """
    now_naive = ensure_naive_utc(now) or ensure_naive_utc(datetime.now())
    features_list = [extract_utility_features(entry.item, now=now_naive) for entry in ranked_items]
    result = evaluate_history_utility(
        features_list,
        query_text=query_text,
        current_type_anchors=current_type_anchors,
        min_score=min_score,
        top_k=top_k,
    )
    kept = [entry for entry in ranked_items if str(getattr(entry.item, "id", "")) in result.selected_ids]
    metadata = result.to_metric_payload()
    metadata["applied"] = True
    if result.candidate_count and result.selected_count < result.candidate_count:
        logger.info(
            "V4-I02 utility gate: candidates={} selected={} verdict={} required_memory={}",
            result.candidate_count,
            result.selected_count,
            metadata["verdict"],
            result.required_memory_recall,
        )
    return kept, metadata


def _inc_gate(outcome: str, reason: str) -> None:
    """计数（metrics 永不破坏检索——M-03 同款容错）。"""
    try:
        MEMORY_UTILITY_GATE_DECISIONS_TOTAL.labels(outcome=outcome, reason=reason).inc()
    except Exception:  # pragma: no cover - metrics must never break retrieval
        pass


__all__ = [
    "DEFAULT_MIN_SCORE",
    "DEFAULT_TOP_K",
    "FROZEN_OUTCOME_WEIGHTS",
    "INFERRED_EXTRACTION_LANE",
    "MEMORY_UTILITY_GATE_VERSION",
    "REQUIRED_MEMORY_MARKERS",
    "TAG_CONTROL_INTRUSION",
    "TAG_DOMAIN_PREFIX",
    "TAG_QUESTION",
    "TAG_TASK_TYPE_PREFIX",
    "TAG_WRONG_FOLLOWED_DECISION",
    "UtilityFeatures",
    "UtilityGateDecision",
    "UtilityGateResult",
    "apply_history_utility_gate",
    "evaluate_history_utility",
    "extract_utility_features",
    "required_memory_query",
    "score_candidate",
]
