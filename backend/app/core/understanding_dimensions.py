"""D-03 · Understanding 五维内部度量契约 —— 可诊断、缺数据=unknown（冻结）。

单一权威（backend/app/core，无 I/O、无 LLM、确定性纯函数）定义 DATA_FLYWHEEL §2
的五个内部理解维度。本模块只定义**公式与缺失语义**；从真实表取数由
``app/services/understanding_dimensions_service.py`` 执行；与外部可观察行为的
对齐验证（离线校准 + 漂移检测）由
``app/services/understanding_calibration_service.py`` 执行。

## 与既有真源的关系（不重建，只引用）

- **coverage** ← ``aurora_judgment_records``（Stage20 确定性 sufficiency judge，
  ``SufficiencyJudgeService``——规则分桶，非 LLM 自评）。它逐决策度量
  「当前 decision 所需维度知道多少」，正是 DATA_FLYWHEEL 对 Coverage 的定义。
  D-01 词表 ``user_state.updated`` 的读投影家族。
- **correctness / scope_precision / freshness** ← ``memory_corrections`` 动作词表
  （写方词表归 MemoryService / MemoryProvenanceService / M-08 scope 治理，
  M-01 认识论契约的兄弟面）+ ``unresolved_conflicts``。本模块**不发明新动作名**，
  只做封闭分区（partition）：哪些既有动作算哪个维度的信号。
- **utility** ← ``memory_corrections`` 的 ``memory_reference_*`` 面（
  ``MemoryService.record_memory_reference_outcome``，数据飞轮 §4 Immediate loop）。
  D-02 outcome 联动的升级路径（个性化 vs 基线 outcome 对比）需 D-05
  intervention→outcome 关联在真实数据上跑通后接入——v1 诚实标注边界，
  不把「接受率」冒充「因果改善」（§5 禁止假象：把相关性写成因果）。

## 五维公式（冻结；改动需 bump UNDERSTANDING_DIMENSIONS_SCHEMA_VERSION 并过 reviewer）

| 维度 | 公式 | 数据源 | 缺失语义 |
|---|---|---|---|
| coverage | mean(context_sufficiency_score)，窗口内 judgment 数 n | aurora_judgment_records | n < MIN_COVERAGE_SAMPLE → unknown |
| correctness | 1 − min(1, ((neg+conflict)/max(usage,1)) / CORRECTNESS_TOLERANCE) | memory_corrections(否定动作) + unresolved_conflicts ÷ context_pack_runs(注入≥1) | usage = 0 → unknown |
| scope_precision | 1 − min(1, (scope_neg / max(scope_feedback,1)) / SCOPE_TOLERANCE) | memory_corrections(scope 面) | scope_feedback = 0 → unknown（反馈通道无数据） |
| freshness | 1 − min(1, mean_lag_days / FRESHNESS_LAG_TOLERANCE_DAYS) | 状态变更型 corrections 与被改记录 created_at 之差 | lag 样本 = 0 → unknown |
| utility | accepted / max(decisive,1) | memory_corrections(memory_reference_{accepted,corrected,denied}) | decisive < MIN_UTILITY_SAMPLE → unknown |

设计纪律（勿漂移）：
- **缺数据 = unknown，永不默认 0/1**。dev 实测（2026-09-20 只读）：229 judgments /
  243 pack runs live，memory_reference_* 与 scope_* 面 0 行 —— unknown 是常态而非
  边角，任何「无数据给满分」的实现都是假指标。
- **纠正/错误使用必须降低相关维度**（验收②）：negatives 与 scope_negatives 分别
  单调压低 correctness / scope_precision（单测钉死单调性）。
- 维度间**不合成单一百分比**（卡面：替代神秘 understanding_depth 百分比）；
  UI 只消费 ``summarize`` 产出的可解释档位。
- 校准（calibration service）可以给出 coverage 的仿射重标定 map，但 map 只作用于
  展示/对齐面，原始维度值保持可重放。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Sequence

UNDERSTANDING_DIMENSIONS_SCHEMA_VERSION = "understanding.dimensions.v1"

# ---------------------------------------------------------------------------
# 维度与状态词表（封闭）
# ---------------------------------------------------------------------------


class DimensionName(StrEnum):
    """DATA_FLYWHEEL §2 五维（封闭词表）。"""

    COVERAGE = "coverage"
    CORRECTNESS = "correctness"
    SCOPE_PRECISION = "scope_precision"
    FRESHNESS = "freshness"
    UTILITY = "utility"


#: 全维度（有序，展示与 JSON 键序冻结用）。
ALL_DIMENSIONS: tuple[DimensionName, ...] = (
    DimensionName.COVERAGE,
    DimensionName.CORRECTNESS,
    DimensionName.SCOPE_PRECISION,
    DimensionName.FRESHNESS,
    DimensionName.UTILITY,
)


class DimensionStatus(StrEnum):
    """单维度取值状态（缺失语义的一等公民，不是 None 糊弄）。"""

    OK = "ok"  # 有值（样本量达标）
    UNKNOWN = "unknown"  # 缺数据：样本量不达标，value 必为 None


# ---------------------------------------------------------------------------
# memory_corrections 动作分区（封闭；动作名归写方服务，本模块只分区）
# ---------------------------------------------------------------------------

#: 内容错误信号：用户明确表示模型内容错了（撤回级 + 置信级）。
#: - delete/reject/no_longer_applicable/retract：撤回级（M-01 EPOCH_BUMP 家族 +
#:   MemoryProvenanceService 治理动作）。
#: - lower_confidence：置信级（用户说「没那么肯定」= 模型过度自信）。
CORRECTNESS_NEGATIVE_ACTIONS: frozenset[str] = frozenset(
    {
        "delete",
        "reject",
        "no_longer_applicable",
        "retract",
        "lower_confidence",
    }
)

#: scope 面：与「用在哪/该不该用于此上下文」相关的反馈与治理动作。
#: - scope_pause / scope_update：M-08 用户 scope 治理（用户改挂载范围 = 用错范围）。
#: - memory_reference_corrected / denied：用户纠正/否认本上下文注入的记忆
#:   （记忆本身可能没错，是**用错地方**）。
#: - memory_reference_accepted：正面样本（用对了）。ignored 不参与（非决定性）。
#: scope_resume 是恢复而非误用信号，不纳入。
SCOPE_FEEDBACK_ACTIONS: frozenset[str] = frozenset(
    {
        "scope_pause",
        "scope_update",
        "memory_reference_accepted",
        "memory_reference_corrected",
        "memory_reference_denied",
    }
)
SCOPE_NEGATIVE_ACTIONS: frozenset[str] = frozenset(
    {
        "scope_pause",
        "scope_update",
        "memory_reference_corrected",
        "memory_reference_denied",
    }
)

#: 状态变更型纠正（freshness lag 样本）：被改记录的旧状态在替换前存活了多久。
#: = 撤回级否定动作（错误状态存活期）+ 用户主动编辑/更新（user_edit /
#: user_edit_supersede / user_update——记录被刷新，旧值存活期）。
#: confirm 不改状态（确认不是更新）；epoch_bump 是管线内部动作，均不纳入。
FRESHNESS_STATE_CHANGE_ACTIONS: frozenset[str] = CORRECTNESS_NEGATIVE_ACTIONS | frozenset(
    {"user_edit", "user_edit_supersede", "user_update"}
)

#: utility 决定性反馈（accepted=个性化有效；corrected/denied=无效）。
#: ignored 非决定性，不进分母。
UTILITY_DECISIVE_ACTIONS: frozenset[str] = frozenset(
    {
        "memory_reference_accepted",
        "memory_reference_corrected",
        "memory_reference_denied",
    }
)
UTILITY_POSITIVE_ACTIONS: frozenset[str] = frozenset({"memory_reference_accepted"})

# ---------------------------------------------------------------------------
# 冻结常数（改这里要同步 golden 与单测）
# ---------------------------------------------------------------------------

MIN_COVERAGE_SAMPLE = 3
"""coverage 最小 judgment 样本数（不足 → unknown）。"""

CORRECTNESS_TOLERANCE = 0.5
"""纠正+冲突率达到 0.5 次/使用机会时 correctness 归零（沿用既有
CORRECTION_TOLERANCE 量纲，D-03 冻结值）。"""

SCOPE_TOLERANCE = 0.25
"""scope 否定率达到 0.25（四分之一反馈为误用）时 scope_precision 归零。"""

FRESHNESS_LAG_TOLERANCE_DAYS = 30.0
"""旧状态平均存活 30 天未更新时 freshness 归零。"""

MIN_UTILITY_SAMPLE = 3
"""utility 最小决定性反馈数（不足 → unknown）。"""

MAX_LAG_DAYS = 365.0
"""lag 截断上限：极老的记录被删不计入超长尾（防单样本均值被拉穿）。"""


# ---------------------------------------------------------------------------
# 值载体
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DimensionValue:
    """一个维度的计算结果：值或 unknown，永不「缺数据假装有值」。

    ``provenance`` 记录数据源表与样本量（可解释/可审计）；``detail`` 携带
    维度特有的解释字段（如 coverage 的 missing-dimension 频次、freshness 的
    lag 分布），键名由各维度单测冻结。
    """

    dimension: DimensionName
    status: DimensionStatus
    value: float | None
    samples: int = 0
    provenance: tuple[str, ...] = ()
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "status": self.status.value,
            "value": None if self.status is not DimensionStatus.OK else round(float(self.value or 0.0), 4),
            "samples": self.samples,
            "provenance": list(self.provenance),
            "detail": dict(self.detail),
        }


def _ok(
    dim: DimensionName, value: float, samples: int, provenance: tuple[str, ...], detail: dict[str, Any] | None = None
) -> DimensionValue:
    bounded = min(1.0, max(0.0, float(value)))
    return DimensionValue(
        dimension=dim,
        status=DimensionStatus.OK,
        value=round(bounded, 4),
        samples=samples,
        provenance=provenance,
        detail=detail or {},
    )


def _unknown(
    dim: DimensionName, samples: int, provenance: tuple[str, ...], reason: str, detail: dict[str, Any] | None = None
) -> DimensionValue:
    merged = dict(detail or {})
    merged["unknown_reason"] = reason
    return DimensionValue(
        dimension=dim,
        status=DimensionStatus.UNKNOWN,
        value=None,
        samples=samples,
        provenance=provenance,
        detail=merged,
    )


# ---------------------------------------------------------------------------
# 维度公式（纯函数，golden 冻结面）
# ---------------------------------------------------------------------------


def compute_coverage(
    *,
    context_scores: Sequence[float],
    task_scores: Sequence[float],
    missing_dimensions: Sequence[str],
) -> DimensionValue:
    """coverage = 窗口内确定性 sufficiency judge 的 context 充分度均值。

    ``missing_dimensions``：窗口内 judgment 报告的缺失维度全量（频次进 detail，
    top-3 进 ``top_missing``——可解释性：知道缺什么，而不只是知道缺）。
    task_scores 只进 detail（决策意图面，与用户模型 coverage 互补，不混算）。
    """
    provenance = ("aurora_judgment_records",)
    n = len(context_scores)
    if n < MIN_COVERAGE_SAMPLE:
        return _unknown(
            DimensionName.COVERAGE,
            n,
            provenance,
            f"judgment samples {n} < {MIN_COVERAGE_SAMPLE}",
        )
    mean_ctx = sum(float(s) for s in context_scores) / n
    freq: dict[str, int] = {}
    for dim in missing_dimensions:
        key = str(dim)
        freq[key] = freq.get(key, 0) + 1
    top_missing = tuple(sorted(freq, key=lambda k: (-freq[k], k))[:3])
    detail = {
        "context_score_mean": round(mean_ctx, 4),
        "task_score_mean": round(sum(float(s) for s in task_scores) / len(task_scores), 4) if task_scores else None,
        "missing_dimension_freq": freq,
        "top_missing": list(top_missing),
    }
    return _ok(DimensionName.COVERAGE, mean_ctx, n, provenance, detail)


def compute_correctness(
    *,
    usage_opportunities: int,
    negative_corrections: int,
    unresolved_conflicts: int,
) -> DimensionValue:
    """correctness = 1 − min(1, 纠正+冲突强度 / CORRECTNESS_TOLERANCE)。

    分母 usage_opportunities = 窗口内注入了 ≥1 条记忆的 context pack run 数
    （模型被实际使用的次数——纠正是「用错」的证据，分母必须是使用面而非聊天量，
    §5 反模式：用更多聊天量当理解增长）。
    usage = 0 → unknown（模型没被用过，谈不上对错）。
    """
    provenance = ("memory_corrections", "unresolved_conflicts", "context_pack_runs")
    usage = int(usage_opportunities)
    if usage <= 0:
        return _unknown(DimensionName.CORRECTNESS, 0, provenance, "no memory usage opportunities in window")
    negatives = int(negative_corrections)
    conflicts = int(unresolved_conflicts)
    rate = (negatives + conflicts) / usage
    value = 1.0 - min(1.0, rate / CORRECTNESS_TOLERANCE)
    detail = {
        "negative_corrections": negatives,
        "unresolved_conflicts": conflicts,
        "usage_opportunities": usage,
        "correction_conflict_rate": round(rate, 4),
    }
    return _ok(DimensionName.CORRECTNESS, value, usage, provenance, detail)


def compute_scope_precision(
    *,
    scope_feedback_total: int,
    scope_negative: int,
) -> DimensionValue:
    """scope_precision = 1 − min(1, 误用率 / SCOPE_TOLERANCE)。

    反馈通道无数据（total = 0）→ unknown：没有用户反馈时声称「范围用得准」
    是无证据断言（dev 实测该面 live 0 行，unknown 是诚实态）。
    """
    provenance = ("memory_corrections",)
    total = int(scope_feedback_total)
    if total <= 0:
        return _unknown(DimensionName.SCOPE_PRECISION, 0, provenance, "scope feedback channel dark in window")
    negatives = int(scope_negative)
    rate = negatives / total
    value = 1.0 - min(1.0, rate / SCOPE_TOLERANCE)
    detail = {
        "scope_feedback_total": total,
        "scope_negative": negatives,
        "scope_misuse_rate": round(rate, 4),
    }
    return _ok(DimensionName.SCOPE_PRECISION, value, total, provenance, detail)


def compute_freshness(
    *,
    lag_days_samples: Sequence[float],
) -> DimensionValue:
    """freshness = 1 − min(1, 平均 lag 天 / FRESHNESS_LAG_TOLERANCE_DAYS)。

    lag = 状态变更型纠正时刻 − 被改记录 created_at（截断 [0, MAX_LAG_DAYS]）：
    旧状态被替换前存活越久，freshness 越低。无样本 → unknown（无更替发生时
    无法区分「稳定」与「陈旧」——不假装知道）。
    """
    provenance = ("memory_corrections",)
    if not lag_days_samples:
        return _unknown(DimensionName.FRESHNESS, 0, provenance, "no state-changing corrections in window")
    clamped = [min(MAX_LAG_DAYS, max(0.0, float(x))) for x in lag_days_samples]
    mean_lag = sum(clamped) / len(clamped)
    value = 1.0 - min(1.0, mean_lag / FRESHNESS_LAG_TOLERANCE_DAYS)
    detail = {
        "lag_sample_count": len(clamped),
        "mean_lag_days": round(mean_lag, 2),
        "max_lag_days": round(max(clamped), 2),
    }
    return _ok(DimensionName.FRESHNESS, value, len(clamped), provenance, detail)


def compute_utility(
    *,
    accepted: int,
    corrected: int,
    denied: int,
) -> DimensionValue:
    """utility（v1，Immediate loop 面）= accepted / decisive。

    decisive = accepted + corrected + denied（用户对注入记忆的**决定性**反馈；
    ignored 不进分母）。v1 边界（诚实标注，勿漂移）：这是个性化注入的即时
    接受率，**不是**因果性的 action/outcome 改善度量——outcome 联动
    （个性化 vs 非个性化基线的 D-02 truth-class 对比）需 D-05
    intervention→outcome 关联在真实数据上跑通后接入，届时 bump 版本。
    """
    provenance = ("memory_corrections",)
    decisive = int(accepted) + int(corrected) + int(denied)
    if decisive < MIN_UTILITY_SAMPLE:
        return _unknown(
            DimensionName.UTILITY,
            decisive,
            provenance,
            f"decisive feedback {decisive} < {MIN_UTILITY_SAMPLE}",
        )
    value = int(accepted) / decisive
    detail = {
        "accepted": int(accepted),
        "corrected": int(corrected),
        "denied": int(denied),
        "decisive_total": decisive,
        "boundary": "immediate-loop acceptance; outcome-linked utility reserved (D-05/D-02)",
    }
    return _ok(DimensionName.UTILITY, value, decisive, provenance, detail)


# ---------------------------------------------------------------------------
# 可解释 summary（UI 唯一消费面；不给单一百分比）
# ---------------------------------------------------------------------------


#: summary 档位（冻结）：只给定性档位 + 证据计数，不给未校准百分数。
#: ok 值分三档：>=0.66 sufficient / >=0.33 partial / <0.33 insufficient。
def band_of(value: float) -> str:
    if value >= 0.66:
        return "sufficient"
    if value >= 0.33:
        return "partial"
    return "insufficient"


def summarize(values: dict[str, DimensionValue]) -> dict[str, Any]:
    """把五维结果折叠成 UI 可消费的可解释 summary。

    - 每维输出 {status, band?, value?, samples, top_missing?, note}；
      value 只在 status=ok 时给出（未校准百分数不出现在 UI 面）。
    - overall 只做证据面陈述：几维 ok / 几维 unknown，无合成分。
    """
    per_dimension: dict[str, Any] = {}
    ok_count = 0
    for dim in ALL_DIMENSIONS:
        entry = values.get(dim.value)
        if entry is None:
            per_dimension[dim.value] = {"status": DimensionStatus.UNKNOWN.value, "value": None, "note": "not computed"}
            continue
        item: dict[str, Any] = {
            "status": entry.status.value,
            "samples": entry.samples,
        }
        if entry.status is DimensionStatus.OK and entry.value is not None:
            ok_count += 1
            item["value"] = entry.value
            item["band"] = band_of(entry.value)
        else:
            item["value"] = None
            item["note"] = entry.detail.get("unknown_reason", "insufficient evidence")
        if dim is DimensionName.COVERAGE and entry.detail.get("top_missing"):
            item["top_missing"] = entry.detail["top_missing"]
        per_dimension[dim.value] = item
    return {
        "schema_version": UNDERSTANDING_DIMENSIONS_SCHEMA_VERSION,
        "dimensions": per_dimension,
        "overall": {
            "ok_dimensions": ok_count,
            "unknown_dimensions": len(ALL_DIMENSIONS) - ok_count,
            # 证据充足性门槛：过半维度有值才给「可诊断」结论，否则如实说证据不足。
            "evidence": "diagnosable" if ok_count * 2 > len(ALL_DIMENSIONS) else "insufficient_evidence",
        },
    }


__all__ = [
    "UNDERSTANDING_DIMENSIONS_SCHEMA_VERSION",
    "DimensionName",
    "DimensionStatus",
    "DimensionValue",
    "ALL_DIMENSIONS",
    "CORRECTNESS_NEGATIVE_ACTIONS",
    "SCOPE_FEEDBACK_ACTIONS",
    "SCOPE_NEGATIVE_ACTIONS",
    "FRESHNESS_STATE_CHANGE_ACTIONS",
    "UTILITY_DECISIVE_ACTIONS",
    "UTILITY_POSITIVE_ACTIONS",
    "MIN_COVERAGE_SAMPLE",
    "CORRECTNESS_TOLERANCE",
    "SCOPE_TOLERANCE",
    "FRESHNESS_LAG_TOLERANCE_DAYS",
    "MIN_UTILITY_SAMPLE",
    "MAX_LAG_DAYS",
    "compute_coverage",
    "compute_correctness",
    "compute_scope_precision",
    "compute_freshness",
    "compute_utility",
    "band_of",
    "summarize",
]
