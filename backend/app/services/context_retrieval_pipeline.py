"""C-03 · Context 硬过滤 → 语义检索 pipeline（L0 candidate-pool 前置层）。

CONTEXT_COMPILER_V3 §6 的观测链（候选数→硬筛数→rerank数→注入数）与卡面
「invalid candidate 绝不送给 model」的最小实现：**任何 embedding / rerank /
LLM 调用之前**，memory 与 knowledge 两个通道的候选先过确定性硬筛，只有合法
候选进入语义阶段。

与既有地基的关系（不重建权威真源）：

- **M-03（``memory_retrieval_prefilter``）**：memory 通道的真权威。本模块的
  memory 通道**委托** ``prefilter_candidates``（同语义、同 version、同
  metric payload），绝不重写筛选规则；``Rejection`` 数据类直接复用（rejections
  形状单一事实源）。M-03 已有的三个接线点（context_pack.build /
  context_manager / stage34）不动——本卡在其上加**边界守卫测试**（变异「去掉
  过滤」必红），并把 knowledge 权限面补齐到同一层。
- **knowledge 权限面（本卡新增）**：Redis RAG 索引（``idx:knowledge@{ver}``）
  是跨用户共享索引——vector/BM25 命中天然含他人 personal chunk。现状两处
  消费面：
  - ``galaxy/retrieval_service._execute_hybrid_search``：RRF 融合后**直接把
    全部候选（含他人 personal chunk 正文）送远程 rerank 模型**，权限检查
    不存在（本卡修复，见 W-K1）；
  - ``graph_rag._redis_hybrid_search``：有内联布尔检查
    ``_redis_doc_matches_user``，但 fail-open（user_id 缺失放行、无检索用户
    放行、无归因、无指标），且是私有静态方法不可复用（本卡收敛为同层前置
    滤芯，见 W-K2）。
  - ``document_vector_search`` / ``document_lexical_search``（pgvector/词法
    文档检索）：SQL 谓词（``DocumentChunk.user_id == user_id`` OR 可访问群组）
    已是 pool 前过滤，不经本层（避免双写规则）。
  - ``_pgvector_fallback`` / ``semantic_search_nodes``：候选是 KnowledgeNode
    共享图节点（等价 node_description 语义，权限中性），不接滤芯。
- **C-02（``orchestration/context_sources``）**：报告/计量形状纪律同源——
  封闭 key 集冻结 + 序列化唯一权威函数（``build_pipeline_report`` 对应
  ``assemble_manifest``）。

**fail-closed 纪律（对齐 M-03）**：

- 身份不可判定的 document chunk（无 user_id 且无 group_id）→ 砍
  （``knowledge:unattributed``）。写方（rag_indexing_service）保证 personal
  chunk 恒带 user_id、group chunk 恒带 group_id——两者皆缺即数据完整性异常，
  fail-open 恰是本层要防的故障类。
- 检索上下文无用户（``user_id=None``）→ document chunk 一律砍
  （``knowledge:no_user_context``）——没有可校验的主体就没有放行依据。
  node_description（共享知识图 chunk）不受影响。
- source_type 词表外（非 ``node_description`` / ``document_chunk``）→ 砍
  （``knowledge:unknown_source_type``）。索引 schema 只有两类写方；E-05 版本化
  索引前缀保证老格式 key 不在新索引内。
- lifecycle 仅在候选**携带**该字段时可判（BM25 面）；缺失 → 放行并在本
  docstring 登记：删除即时可见性由 E-05 的 key 失效 + knowledge_version 语义
  缓存失效拥有（不在本层重建）。

**维度求值顺序**（首个失败维度独占拒绝归因，指标确定性；与 M-03 的
user→status 同构）：identity → lifecycle。顺序被
``test_filter_dimensions_order_is_pinned`` 钉死；reorder 必须 bump
``KNOWLEDGE_PERMISSION_FILTER_VERSION``。

**封闭 code 词表（冻结）**——新增 reason code 必须同步冻结测试
（``test_reason_codes_frozen``）与版本号：

    identity:  knowledge:unknown_source_type
               knowledge:no_user_context
               knowledge:group_inaccessible
               knowledge:wrong_user
               knowledge:unattributed
    lifecycle: knowledge:lifecycle_inactive

**reasons / 计量形状**：``KnowledgeFilterResult`` 与 M-03 ``PrefilterResult``
字段集逐字对齐（``test_result_shape_parity_with_m03`` 钉死），metric payload
同 key 集（version/input_count/allowed_count/dimension_counts/reason_counts）；
pipeline 报告顶层 key 集（``PIPELINE_REPORT_KEYS``）、通道 key 集
（``CHANNEL_REPORT_KEYS``）与 rerank 节 key 集（``RERANK_REPORT_KEYS``）冻结，
序列化唯一权威是 ``build_pipeline_report``。

真实 LLM / embedding 零依赖：滤芯与管道核心均为纯函数；rerank 通过 ``rerank_fn``
注入（galaxy 接线注入 rerank_service 闭包；测试注入合成向量排序）。
"""

from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Coroutine
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Iterable, Mapping, Sequence

from loguru import logger

from app.core.business_metrics import KNOWLEDGE_PREFILTER_REJECTIONS_TOTAL
from app.services.memory_retrieval_prefilter import (
    MEMORY_PREFILTER_VERSION,
    Rejection,
    RetrievalContext,
    prefilter_candidates,
)
from app.services.rag_indexing_service import SOURCE_DOCUMENT_CHUNK, SOURCE_NODE_DESCRIPTION

KNOWLEDGE_PERMISSION_FILTER_VERSION = "context-v3.c03.knowledge.v1"
PIPELINE_SCHEMA_VERSION = "context_retrieval_pipeline.v1"

# ---------------------------------------------------------------------------
# 1. Knowledge 权限预筛 —— 封闭词表（单一事实源）
# ---------------------------------------------------------------------------


class KnowledgeFilterDimension(StrEnum):
    """粗粒度筛选维度（metrics label）。与 M-03 FilterDimension 同型：
    身份（identity）对应 user，lifecycle 对应 status。"""

    IDENTITY = "identity"
    LIFECYCLE = "lifecycle"


#: 固定求值顺序：首个失败维度独占拒绝归因（确定性指标归因）。
KNOWLEDGE_FILTER_DIMENSIONS: tuple[KnowledgeFilterDimension, ...] = (
    KnowledgeFilterDimension.IDENTITY,
    KnowledgeFilterDimension.LIFECYCLE,
)

#: Redis RAG 索引 chunk 的封闭 source_type 词表（写方：rag_indexing_service；
#: 词表 parity 由 test_source_type_vocabulary_pinned 守卫——写方加类型必红）。
KNOWLEDGE_SOURCE_TYPES: frozenset[str] = frozenset({SOURCE_NODE_DESCRIPTION, SOURCE_DOCUMENT_CHUNK})

#: 共享知识图 chunk（权限中性：KnowledgeNode 是全局去重共享图，用户态在
#: UserNodeStatus / KnowledgeNodeDocument，chunk 本体无身份归属）。
SHARED_SOURCE_TYPES: frozenset[str] = frozenset({SOURCE_NODE_DESCRIPTION})

#: lifecycle 判定的合法活跃值（与 StoredFile.lifecycle_status / rag_indexing
#: 写入的 ACTIVE 值对齐；缺失字段 = 该传输面不可判 → 放行，见模块 docstring）。
ACTIVE_LIFECYCLE_STATUS = "active"

#: 冻结 reason code 全集（新增必须 bump KNOWLEDGE_PERMISSION_FILTER_VERSION
#: 并同步 test_reason_codes_frozen）。
KNOWLEDGE_REJECTION_REASONS: frozenset[str] = frozenset(
    {
        "knowledge:unknown_source_type",
        "knowledge:no_user_context",
        "knowledge:group_inaccessible",
        "knowledge:wrong_user",
        "knowledge:unattributed",
        "knowledge:lifecycle_inactive",
    }
)


@dataclass(frozen=True)
class KnowledgeAccessContext:
    """一次 knowledge 检索消费行为的权限上下文（纯数据；I/O 由调用方完成——
    M-03 ``build_retrieval_context`` 的分层同型）。

    ``user_id`` 允许 None（显式「无检索主体」→ document chunk fail-closed）；
    ``allowed_group_ids`` 是已解析的可访问群组 id 集（str 归一化）。
    """

    user_id: str | None = None
    allowed_group_ids: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_group_ids", frozenset(str(g) for g in self.allowed_group_ids))
        if self.user_id is not None:
            object.__setattr__(self, "user_id", str(self.user_id).strip() or None)


# ---------------------------------------------------------------------------
# 2. 结果类型（形状与 M-03 PrefilterResult 逐字对齐）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeFilterResult:
    """与 M-03 ``PrefilterResult`` 同字段集：allowed / rejections / input_count /
    dimension_counts / reason_counts；metric payload 同 key 集（version 不同）。
    parity 由 test_result_shape_parity_with_m03 钉死。"""

    allowed: list[Any]
    rejections: list[Rejection]
    input_count: int
    dimension_counts: dict[str, int]
    reason_counts: dict[str, int]

    @property
    def allowed_count(self) -> int:
        return len(self.allowed)

    def to_metric_payload(self) -> dict[str, Any]:
        """结构化 filter-reason 输出（D-06/O-02 可观测消费面；M-03 同型）。"""
        return {
            "version": KNOWLEDGE_PERMISSION_FILTER_VERSION,
            "input_count": self.input_count,
            "allowed_count": self.allowed_count,
            "dimension_counts": dict(self.dimension_counts),
            "reason_counts": dict(self.reason_counts),
        }


def _doc_field(doc: Any, key: str, default: Any = None) -> Any:
    """Redis Document（属性访问）或 dict（键访问）统一取字段。"""
    if isinstance(doc, Mapping):
        return doc.get(key, default)
    return getattr(doc, key, default)


def _doc_id(doc: Any) -> str:
    for key in ("id", "chunk_id", "node_id", "parent_id"):
        value = _doc_field(doc, key)
        if value:
            return str(value)
    return "<unknown>"


def _reject(doc: Any, dimension: KnowledgeFilterDimension, reason: str, detail: str) -> Rejection:
    return Rejection(record_id=_doc_id(doc), dimension=dimension.value, reason=reason, detail=detail)


def _reject_identity(doc: Any, ctx: KnowledgeAccessContext) -> Rejection | None:
    source_type = str(_doc_field(doc, "source_type", "") or "").strip()
    if source_type not in KNOWLEDGE_SOURCE_TYPES:
        return _reject(
            doc,
            KnowledgeFilterDimension.IDENTITY,
            "knowledge:unknown_source_type",
            f"source_type={source_type!r} vocabulary={sorted(KNOWLEDGE_SOURCE_TYPES)}",
        )
    if source_type in SHARED_SOURCE_TYPES:
        # 共享知识图 chunk：无身份归属，权限中性（见 SHARED_SOURCE_TYPES 注释）。
        return None
    # document_chunk：身份判定（固定子顺序：无主体 → 群组 → 个人 → 无归属）。
    if ctx.user_id is None:
        return _reject(
            doc,
            KnowledgeFilterDimension.IDENTITY,
            "knowledge:no_user_context",
            "retrieval context carries no user; document chunks are unverifiable",
        )
    group_id = str(_doc_field(doc, "group_id", "") or "").strip()
    if group_id:
        if group_id not in ctx.allowed_group_ids:
            return _reject(
                doc,
                KnowledgeFilterDimension.IDENTITY,
                "knowledge:group_inaccessible",
                f"group_id={group_id} not in allowed groups (n={len(ctx.allowed_group_ids)})",
            )
        return None
    doc_user_id = str(_doc_field(doc, "user_id", "") or "").strip()
    if doc_user_id:
        if doc_user_id != ctx.user_id:
            return _reject(
                doc,
                KnowledgeFilterDimension.IDENTITY,
                "knowledge:wrong_user",
                f"doc_user={doc_user_id!r} context_user={ctx.user_id!r}",
            )
        return None
    return _reject(
        doc,
        KnowledgeFilterDimension.IDENTITY,
        "knowledge:unattributed",
        "document chunk carries neither user_id nor group_id (writer invariant violated)",
    )


def _reject_lifecycle(doc: Any) -> Rejection | None:
    raw = _doc_field(doc, "lifecycle_status", None)
    if raw is None or not str(raw).strip():
        # 该传输面不携带 lifecycle（如 dense 面 return_fields 无此列）：
        # 删除即时可见性由 E-05 key 失效拥有，本层不凭缺失砍合法候选。
        return None
    status = str(raw).strip()
    if status != ACTIVE_LIFECYCLE_STATUS:
        return _reject(
            doc,
            KnowledgeFilterDimension.LIFECYCLE,
            "knowledge:lifecycle_inactive",
            f"lifecycle_status={status!r}",
        )
    return None


def prefilter_knowledge_candidates(candidates: Iterable[Any], ctx: KnowledgeAccessContext) -> KnowledgeFilterResult:
    """确定性砍除权限非法的 knowledge 候选（rerank/embedding 之前的 L0 层）。

    纯函数（无 I/O）；候选可为 Redis Document、dict 或等价 namespace。返回
    合法子集 + 逐候选拒绝归因 + 逐维度/逐原因计数（同步落 Prometheus 与日志，
    M-03 同型）。"""
    allowed: list[Any] = []
    rejections: list[Rejection] = []
    dimension_counts: dict[str, int] = {dimension.value: 0 for dimension in KNOWLEDGE_FILTER_DIMENSIONS}
    reason_counts: dict[str, int] = {}
    input_count = 0

    for doc in candidates:
        input_count += 1
        rejection = _reject_identity(doc, ctx) or _reject_lifecycle(doc)
        if rejection is None:
            allowed.append(doc)
            continue
        rejections.append(rejection)
        dimension_counts[rejection.dimension] = dimension_counts.get(rejection.dimension, 0) + 1
        reason_counts[rejection.reason] = reason_counts.get(rejection.reason, 0) + 1
        try:
            KNOWLEDGE_PREFILTER_REJECTIONS_TOTAL.labels(dimension=rejection.dimension, reason=rejection.reason).inc()
        except Exception:  # pragma: no cover - metrics must never break retrieval
            pass

    result = KnowledgeFilterResult(
        allowed=allowed,
        rejections=rejections,
        input_count=input_count,
        dimension_counts=dimension_counts,
        reason_counts=reason_counts,
    )
    if rejections:
        logger.info(
            "C-03 knowledge prefilter: input={} allowed={} rejected_dims={} rejected_reasons={}",
            input_count,
            result.allowed_count,
            {k: v for k, v in dimension_counts.items() if v},
            reason_counts,
        )
    return result


def knowledge_candidate_permitted(doc: Any, ctx: KnowledgeAccessContext) -> bool:
    """布尔便捷面（W-K2 兼容层）。新代码一律用 ``prefilter_knowledge_candidates``
    （批量 + 归因 + 指标）。"""
    return not _reject_identity(doc, ctx) and not _reject_lifecycle(doc)


# ---------------------------------------------------------------------------
# 3. 硬过滤 → rerank pipeline（合法候选才进语义阶段）
# ---------------------------------------------------------------------------

#: 通道封闭词表（pipeline 报告 channels 的 key 全集；扩展需 bump
#: PIPELINE_SCHEMA_VERSION 并同步冻结测试）。
CHANNEL_MEMORY = "memory"
CHANNEL_KNOWLEDGE = "knowledge"
PIPELINE_CHANNELS: tuple[str, ...] = (CHANNEL_MEMORY, CHANNEL_KNOWLEDGE)

#: 通道报告 key 集（冻结；序列化唯一权威 build_pipeline_report）。
CHANNEL_REPORT_KEYS: tuple[str, ...] = (
    "channel",
    "version",  # M-03 MEMORY_PREFILTER_VERSION / KNOWLEDGE_PERMISSION_FILTER_VERSION
    "input_count",
    "allowed_count",
    "rejected_count",
    "dimension_counts",
    "reason_counts",
    "latency_ms",
    "tokens_before",
    "tokens_after",
)

#: rerank 分节 key 集（冻结）。
RERANK_REPORT_KEYS: tuple[str, ...] = ("input_count", "output_count", "latency_ms", "skipped")

#: pipeline 报告顶层 key 集（冻结；与 C-02 MANIFEST_TOP_LEVEL_KEYS 同纪律）。
PIPELINE_REPORT_KEYS: tuple[str, ...] = (
    "schema_version",
    "channels",
    "rerank",
    "total_latency_ms",
    "tokens_before",
    "tokens_after",
    "tokens_saved",
)


def _default_estimate_tokens(text: str) -> int:
    """与 app.core.context_pack.estimate_tokens 同型降级（无 tiktoken 时 len//4）。"""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _candidate_text(candidate: Any) -> str:
    """token 估算用的候选正文（knowledge chunk：content；memory 记录：summary /
    pref_value / title。仅用于「过滤前后 token 可观测」，非注入正文）。"""
    parts: list[str] = []
    for attr in ("content", "summary", "description", "pref_value", "title", "name"):
        value = _doc_field(candidate, attr)
        if isinstance(value, str) and value:
            parts.append(value)
        elif value is not None and not isinstance(value, (Mapping, list, tuple, bool, int, float)):
            parts.append(str(value))
    return " ".join(parts)


def _estimate_candidates(candidates: Iterable[Any], estimate_tokens_fn: Callable[[str], int]) -> int:
    return sum(estimate_tokens_fn(_candidate_text(candidate)) for candidate in candidates)


@dataclass(frozen=True)
class ChannelOutcome:
    """单通道硬筛结果（合法子集 + M-03/知识滤芯 metric payload 原样 + 计量）。"""

    channel: str
    allowed: list[Any]
    metric_payload: Mapping[str, Any]
    latency_ms: float
    tokens_before: int
    tokens_after: int

    def to_report(self) -> dict[str, Any]:
        payload = dict(self.metric_payload)
        input_count = int(payload.get("input_count", 0) or 0)
        allowed_count = int(payload.get("allowed_count", 0) or 0)
        return {
            "channel": self.channel,
            "version": payload.get("version"),
            "input_count": input_count,
            "allowed_count": allowed_count,
            "rejected_count": input_count - allowed_count,
            "dimension_counts": dict(payload.get("dimension_counts") or {}),
            "reason_counts": dict(payload.get("reason_counts") or {}),
            "latency_ms": round(self.latency_ms, 3),
            "tokens_before": int(self.tokens_before),
            "tokens_after": int(self.tokens_after),
        }


@dataclass(frozen=True)
class PipelineResult:
    """硬过滤→rerank 的管道输出：合法且已重排的候选 + 逐通道结果 + 冻结形状报告。"""

    ranked: list[Any]
    channels: Mapping[str, ChannelOutcome]
    rerank_input: list[Any]
    rerank_latency_ms: float | None
    rerank_skipped: bool
    report: Mapping[str, Any]

    @property
    def allowed(self) -> list[Any]:
        """跨通道合法候选（rerank 输入，memory→knowledge 确定性顺序）。"""
        return list(self.rerank_input)


def build_pipeline_report(
    *,
    channel_outcomes: Sequence[ChannelOutcome],
    rerank_input_count: int,
    rerank_output_count: int,
    rerank_latency_ms: float | None,
    rerank_skipped: bool,
    total_latency_ms: float,
) -> dict[str, Any]:
    """pipeline 报告序列化的**唯一权威**：恒定产出恰好 PIPELINE_REPORT_KEYS 的
    key 集、每通道恰好 CHANNEL_REPORT_KEYS、rerank 节恰好 RERANK_REPORT_KEYS
    （形状契约由 test_pipeline_report_keys_frozen 钉死，任何变更需双 reviewer）。"""
    channels = {outcome.channel: outcome.to_report() for outcome in channel_outcomes}
    tokens_before = sum(outcome.tokens_before for outcome in channel_outcomes)
    tokens_after = sum(outcome.tokens_after for outcome in channel_outcomes)
    rerank: dict[str, Any] = {
        "input_count": int(rerank_input_count),
        "output_count": int(rerank_output_count),
        "latency_ms": round(rerank_latency_ms, 3) if rerank_latency_ms is not None else None,
        "skipped": bool(rerank_skipped),
    }
    return {
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "channels": channels,
        "rerank": rerank,
        "total_latency_ms": round(total_latency_ms, 3),
        "tokens_before": int(tokens_before),
        "tokens_after": int(tokens_after),
        "tokens_saved": int(tokens_before - tokens_after),
    }


# ---------------------------------------------------------------------------
# 3a. 管道核心（同步/异步面共用；滤芯纯函数，只有 rerank 可能是 async）
# ---------------------------------------------------------------------------


def _validate_channel_contexts(
    memory_candidates: Sequence[Any],
    retrieval_ctx: RetrievalContext | None,
    knowledge_candidates: Sequence[Any],
    knowledge_ctx: KnowledgeAccessContext | None,
) -> None:
    """fail-loud 上下文校验（同步/异步面共用）：给了候选就必须给该通道上下文——
    缺上下文是调用方错误，ValueError 可见（绝不「没上下文就当全合法」）。
    M-03 RetrievalContext 的 purpose 词表校验同型。"""
    if memory_candidates and retrieval_ctx is None:
        raise ValueError(
            "memory_candidates given without retrieval_ctx (M-03 context required; refusing to pass unfiltered)"
        )
    if knowledge_candidates and knowledge_ctx is None:
        raise ValueError(
            "knowledge_candidates given without knowledge_ctx (permission context required; refusing to pass unfiltered)"
        )


def _run_channel_filters(
    *,
    memory_candidates: Sequence[Any],
    retrieval_ctx: RetrievalContext | None,
    knowledge_candidates: Sequence[Any],
    knowledge_ctx: KnowledgeAccessContext | None,
    estimate: Callable[[str], int],
) -> list[ChannelOutcome]:
    """逐通道硬筛（同步/异步面共用核心）：memory 委托 M-03、knowledge 走权限
    滤芯。滤芯本身是纯函数（无 I/O），两个面的语义因此逐字节一致。"""
    outcomes: list[ChannelOutcome] = []

    if memory_candidates:
        channel_start = time.perf_counter()
        tokens_before = _estimate_candidates(memory_candidates, estimate)
        prefilter_result = prefilter_candidates(memory_candidates, retrieval_ctx)
        channel_latency_ms = (time.perf_counter() - channel_start) * 1000.0
        outcomes.append(
            ChannelOutcome(
                channel=CHANNEL_MEMORY,
                allowed=list(prefilter_result.allowed),
                metric_payload=prefilter_result.to_metric_payload(),
                latency_ms=channel_latency_ms,
                tokens_before=tokens_before,
                tokens_after=_estimate_candidates(prefilter_result.allowed, estimate),
            )
        )
        logger.info(
            "C-03 pipeline memory channel (M-03 {}): input={} allowed={} latency_ms={:.3f}",
            MEMORY_PREFILTER_VERSION,
            prefilter_result.input_count,
            prefilter_result.allowed_count,
            channel_latency_ms,
        )

    if knowledge_candidates:
        channel_start = time.perf_counter()
        tokens_before = _estimate_candidates(knowledge_candidates, estimate)
        knowledge_result = prefilter_knowledge_candidates(knowledge_candidates, knowledge_ctx)
        channel_latency_ms = (time.perf_counter() - channel_start) * 1000.0
        outcomes.append(
            ChannelOutcome(
                channel=CHANNEL_KNOWLEDGE,
                allowed=list(knowledge_result.allowed),
                metric_payload=knowledge_result.to_metric_payload(),
                latency_ms=channel_latency_ms,
                tokens_before=tokens_before,
                tokens_after=_estimate_candidates(knowledge_result.allowed, estimate),
            )
        )

    return outcomes


def _channel_outcome(outcomes: Sequence[ChannelOutcome], channel: str) -> ChannelOutcome | None:
    for outcome in outcomes:
        if outcome.channel == channel:
            return outcome
    return None


def _legal_candidates(outcomes: Sequence[ChannelOutcome]) -> list[Any]:
    """跨通道合法列表（顺序确定性：恒 PIPELINE_CHANNELS 序 = memory→knowledge，
    与 outcomes 的构造顺序无关）。"""
    legal: list[Any] = []
    for channel in PIPELINE_CHANNELS:
        outcome = _channel_outcome(outcomes, channel)
        if outcome is not None:
            legal.extend(outcome.allowed)
    return legal


def _log_pipeline_summary(outcomes: Sequence[ChannelOutcome], report: Mapping[str, Any]) -> None:
    logger.info(
        "C-03 hard-filter pipeline: channels={} rerank_in={} rerank_out={} rerank_skipped={} "
        "tokens {}->{} (saved {}) total_latency_ms={:.3f}",
        {outcome.channel: outcome.metric_payload.get("input_count") for outcome in outcomes},
        report["rerank"]["input_count"],
        report["rerank"]["output_count"],
        report["rerank"]["skipped"],
        report["tokens_before"],
        report["tokens_after"],
        report["tokens_saved"],
        report["total_latency_ms"],
    )


def _resolve_ranked_sync(raw: Any) -> Any:
    """同步面 rerank 结果解析：awaitable 只允许在无运行 loop 时消费（纯同步
    调用方给 coroutine 的边角）；运行中 loop 内给 async rerank_fn 是接线错误，
    显式报错引导到 async 面。"""
    if not inspect.isawaitable(raw):
        return raw
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(raw)
    # 关闭未消费的 coroutine，避免 "never awaited" RuntimeWarning（close 对
    # 未启动的 coroutine 是安全的空操作路径）。Awaitable 家族中仅 coroutine
    # 有 close，用 isinstance 收窄。
    if isinstance(raw, Coroutine):
        raw.close()
    raise RuntimeError(
        "run_hard_filter_pipeline called inside a running event loop with an async "
        "rerank_fn; use run_hard_filter_pipeline_async instead"
    )


def run_hard_filter_pipeline(
    *,
    memory_candidates: Sequence[Any] = (),
    retrieval_ctx: RetrievalContext | None = None,
    knowledge_candidates: Sequence[Any] = (),
    knowledge_ctx: KnowledgeAccessContext | None = None,
    rerank_fn: Callable[[list[Any]], Any] | None = None,
    estimate_tokens_fn: Callable[[str], int] | None = None,
) -> PipelineResult:
    """候选池 → 硬筛（memory: M-03 / knowledge: 权限滤芯）→ 仅合法候选 rerank。

    分层契约（CONTEXT_COMPILER_V3 §6「候选数→硬筛数→rerank数」）：

    - **fail-loud，不静默透传**：见 ``_validate_channel_contexts``；
    - **rerank_fn 只见合法候选**（卡面验收「invalid candidate 绝不送给
      model」）；``rerank_fn=None`` 表示该接线点无语义阶段（rerank 节报
      skipped）。同步面要求 rerank_fn 同步（或无运行 loop 时可消费 awaitable）；
      async rerank_fn（远程模型）用 ``run_hard_filter_pipeline_async``；
    - 顺序确定性：跨通道合法列表恒 memory→knowledge；报告 key 集冻结；
    - 逐通道计量（候选数/砍除归因/延迟/token 前后）随返回值携带 + 结构化日志，
      供 manifest / telemetry 消费（与 C-02 sources 计量同纪律）。
    """
    _validate_channel_contexts(memory_candidates, retrieval_ctx, knowledge_candidates, knowledge_ctx)
    estimate = estimate_tokens_fn or _default_estimate_tokens
    wall_start = time.perf_counter()
    outcomes = _run_channel_filters(
        memory_candidates=memory_candidates,
        retrieval_ctx=retrieval_ctx,
        knowledge_candidates=knowledge_candidates,
        knowledge_ctx=knowledge_ctx,
        estimate=estimate,
    )
    legal = _legal_candidates(outcomes)

    rerank_latency_ms: float | None = None
    rerank_skipped = rerank_fn is None
    ranked: list[Any] = legal
    if rerank_fn is not None:
        rerank_start = time.perf_counter()
        ranked = list(_resolve_ranked_sync(rerank_fn(legal)))
        rerank_latency_ms = (time.perf_counter() - rerank_start) * 1000.0

    report = build_pipeline_report(
        channel_outcomes=outcomes,
        rerank_input_count=len(legal),
        rerank_output_count=len(ranked),
        rerank_latency_ms=rerank_latency_ms,
        rerank_skipped=rerank_skipped,
        total_latency_ms=(time.perf_counter() - wall_start) * 1000.0,
    )
    _log_pipeline_summary(outcomes, report)
    return PipelineResult(
        ranked=ranked,
        channels={outcome.channel: outcome for outcome in outcomes},
        rerank_input=legal,
        rerank_latency_ms=rerank_latency_ms,
        rerank_skipped=rerank_skipped,
        report=report,
    )


async def run_hard_filter_pipeline_async(
    *,
    memory_candidates: Sequence[Any] = (),
    retrieval_ctx: RetrievalContext | None = None,
    knowledge_candidates: Sequence[Any] = (),
    knowledge_ctx: KnowledgeAccessContext | None = None,
    rerank_fn: Callable[[list[Any]], Any] | None = None,
    estimate_tokens_fn: Callable[[str], int] | None = None,
) -> PipelineResult:
    """async 接线面（galaxy hybrid 路径）：async rerank_fn（远程模型）在当前
    loop 内 await；过滤语义与同步面完全一致（共用 _run_channel_filters）。"""
    _validate_channel_contexts(memory_candidates, retrieval_ctx, knowledge_candidates, knowledge_ctx)
    estimate = estimate_tokens_fn or _default_estimate_tokens
    wall_start = time.perf_counter()
    outcomes = _run_channel_filters(
        memory_candidates=memory_candidates,
        retrieval_ctx=retrieval_ctx,
        knowledge_candidates=knowledge_candidates,
        knowledge_ctx=knowledge_ctx,
        estimate=estimate,
    )
    legal = _legal_candidates(outcomes)

    rerank_latency_ms: float | None = None
    rerank_skipped = rerank_fn is None
    ranked: list[Any] = legal
    if rerank_fn is not None:
        rerank_start = time.perf_counter()
        raw_ranked = rerank_fn(legal)
        if inspect.isawaitable(raw_ranked):
            raw_ranked = await raw_ranked
        ranked = list(raw_ranked)
        rerank_latency_ms = (time.perf_counter() - rerank_start) * 1000.0

    report = build_pipeline_report(
        channel_outcomes=outcomes,
        rerank_input_count=len(legal),
        rerank_output_count=len(ranked),
        rerank_latency_ms=rerank_latency_ms,
        rerank_skipped=rerank_skipped,
        total_latency_ms=(time.perf_counter() - wall_start) * 1000.0,
    )
    _log_pipeline_summary(outcomes, report)
    return PipelineResult(
        ranked=ranked,
        channels={outcome.channel: outcome for outcome in outcomes},
        rerank_input=legal,
        rerank_latency_ms=rerank_latency_ms,
        rerank_skipped=rerank_skipped,
        report=report,
    )


__all__ = [
    "ACTIVE_LIFECYCLE_STATUS",
    "CHANNEL_KNOWLEDGE",
    "CHANNEL_MEMORY",
    "CHANNEL_REPORT_KEYS",
    "KNOWLEDGE_FILTER_DIMENSIONS",
    "KNOWLEDGE_PERMISSION_FILTER_VERSION",
    "KNOWLEDGE_REJECTION_REASONS",
    "KNOWLEDGE_SOURCE_TYPES",
    "PIPELINE_CHANNELS",
    "PIPELINE_REPORT_KEYS",
    "PIPELINE_SCHEMA_VERSION",
    "RERANK_REPORT_KEYS",
    "SHARED_SOURCE_TYPES",
    "ChannelOutcome",
    "KnowledgeAccessContext",
    "KnowledgeFilterDimension",
    "KnowledgeFilterResult",
    "PipelineResult",
    "build_pipeline_report",
    "knowledge_candidate_permitted",
    "prefilter_knowledge_candidates",
    "run_hard_filter_pipeline",
    "run_hard_filter_pipeline_async",
]
