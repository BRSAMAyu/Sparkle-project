"""C-08 · Context Observability —— 漏斗观测 + source_ref 追溯 + bloat/inert 定位。

回答「为什么这次模型看了这些」并验证「少而对」：把散落在
``context_funnel_memory``（context_builder stage34 装配）、
``document_context_retrieval`` / ``document_context_budget``（检索节点）、
``context_budget``（C-06 预算装配）与 ``citation_outcome``（C-04 结果记录）
的观测面收敛成**单一结构化漏斗记录**。

三层职责，全部纯函数、零 I/O（hermetic，可独立单测；不 import 任何
app.* 模块——token 估算经注入的 estimator，缺省用保守的长度近似）：

1. **漏斗观测** —— 每条注入面（episodic 记忆 / experience 经验 / RAG 文档）
   的 ``candidates → filtered → ranked → injected`` 四段计数 + token 计量 +
   决策 reasons（结构化、有界词表）。漏斗单调性
   （injected ≤ ranked ≤ filtered ≤ candidates）是可机检不变量。
2. **source_ref 追溯** —— 每条注入材料带可追溯 ref
   （``doc:<file_id>:<chunk_id>`` / ``mem:<memory_id>`` / ``exp:<record_id>``），
   与 C-04 ``[S#]`` 引用标记按注入顺序对齐；错误 Context 可据此定位到源。
3. **bloat / harmful 定位** —— 分区 token 占比超阈标记（bloat）；
   「注入了但零引用零支撑」的材料标记（inert，harmful 候选）。

红线（acceptance「不记录敏感正文到日志」）：本模块产出的记录**永不携带
正文**——只有 id / 类型 / 计数 / token 估算 / 长度 / 12 位短哈希。
``find_content_leak`` 是测试面探针：给定正文样本，扫描记录序列化结果
是否泄漏（单测钉死）。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable

#: 记录 schema 版本（变更需同步单测与评测门禁）。
FUNNEL_VERSION = "c08-context-funnel.v1"

#: 漏斗阶段（冻结顺序：上游 → 下游）。
STAGE_CANDIDATES = "candidates"
STAGE_FILTERED = "filtered"
STAGE_RANKED = "ranked"
STAGE_INJECTED = "injected"
STAGE_NAMES: tuple[str, ...] = (STAGE_CANDIDATES, STAGE_FILTERED, STAGE_RANKED, STAGE_INJECTED)

#: 注入面（有界 label 词表；Prometheus label 只接受这三个 + "other"）。
SURFACE_EPISODIC = "memory_episodic"
SURFACE_EXPERIENCE = "memory_experience"
SURFACE_DOCUMENTS = "documents"
SURFACES: tuple[str, ...] = (SURFACE_EPISODIC, SURFACE_EXPERIENCE, SURFACE_DOCUMENTS)

#: 决策 reason 有界词表（clamp 后才进 Prometheus label；开放词表只留在
#: 结构化 payload 里）。前六项对齐 M-03 prefilter 的 FilterDimension。
REASON_PREFILTER_USER = "prefilter_user"
REASON_PREFILTER_STATUS = "prefilter_status"
REASON_PREFILTER_TTL = "prefilter_ttl"
REASON_PREFILTER_SCOPE = "prefilter_scope"
REASON_PREFILTER_PURPOSE = "prefilter_purpose"
REASON_PREFILTER_SENSITIVITY = "prefilter_sensitivity"
REASON_RANK_CUTOFF = "rank_cutoff"
REASON_SELFCHECK_INTERNAL = "selfcheck_internal"
REASON_BUDGET_TRUNCATED = "budget_truncated"
REASON_EMPTY_CONTENT = "empty_content"
REASON_OTHER = "other"
BOUNDED_DROP_REASONS: frozenset[str] = frozenset(
    {
        REASON_PREFILTER_USER,
        REASON_PREFILTER_STATUS,
        REASON_PREFILTER_TTL,
        REASON_PREFILTER_SCOPE,
        REASON_PREFILTER_PURPOSE,
        REASON_PREFILTER_SENSITIVITY,
        REASON_RANK_CUTOFF,
        REASON_SELFCHECK_INTERNAL,
        REASON_BUDGET_TRUNCATED,
        REASON_EMPTY_CONTENT,
        REASON_OTHER,
    }
)

#: bloat 判定：单一分区 token 占总注入 token 的比例超过该值即标记。
DEFAULT_BLOAT_SHARE_THRESHOLD = 0.45

#: source_ref 类型（有界）。
REF_KIND_DOCUMENT = "document"
REF_KIND_EPISODIC = "episodic"
REF_KIND_EXPERIENCE = "experience"
REF_KINDS: tuple[str, ...] = (REF_KIND_DOCUMENT, REF_KIND_EPISODIC, REF_KIND_EXPERIENCE)

_FALLBACK_TOKEN_ESTIMATOR: Callable[[str], int] = lambda text: max(1, len(text) // 4) if text else 0

#: C-08 N6：``make_source_ref`` 标量 extra 的字符串长度上限——extra 是
#: metadata 通道（page_number / chunk_index / relevance 等短标量），超长
#: 字符串截断，防止未来调用方把正文/敏感文本借道标量 extra 整段入册。
_MAX_EXTRA_STR_LEN = 64


def clamp_drop_reason(reason: str) -> str:
    """开放 reason 词表 → 有界 label 词表（Prometheus 基数守卫）。

    M-03 prefilter 的 reason 是 ``<dimension>:<detail>`` 形态
    （``status:superseded`` / ``ttl:expired`` / ``scope:mismatch`` …），
    按维度前缀收敛到 ``prefilter_<dimension>``；本模块自有 reason 原样
    通过；未知值一律 ``other``。
    """
    text = str(reason or "").strip()
    if not text:
        return REASON_OTHER
    if text in BOUNDED_DROP_REASONS:
        return text
    dimension = text.split(":", 1)[0]
    if f"prefilter_{dimension}" in BOUNDED_DROP_REASONS:
        return f"prefilter_{dimension}"
    for prefix in ("user", "status", "ttl", "scope", "purpose", "sensitivity"):
        if prefix in text:
            return f"prefilter_{prefix}"
    return REASON_OTHER


def clamp_surface(surface: str) -> str:
    """漏斗面有界化（未知面 → ``other``，防 label 基数膨胀）。"""
    return surface if surface in SURFACES else "other"


def content_fingerprint(text: str) -> tuple[int, str]:
    """正文 → (长度, 12 位短哈希)。身份可比对、正文不可还原（隐私红线）。"""
    payload = str(text or "")
    return len(payload), hashlib.sha256(payload.encode("utf-8", "ignore")).hexdigest()[:12]


@dataclass
class StageObservation:
    """单阶段观测：计数 + token + 决策 reasons（无正文）。"""

    stage: str
    items: int = 0
    tokens: int = 0
    #: 聚合 reasons（reason → 淘汰数；开放词表，仅入结构化 payload）。
    reasons: dict[str, int] = field(default_factory=dict)
    #: 逐条淘汰明细 [(ref, reason)]——ref 是 source_ref，不是正文。
    dropped_refs: list[tuple[str, str]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "items": int(self.items),
            "tokens": int(self.tokens),
            "reasons": {str(k): int(v) for k, v in sorted(self.reasons.items())},
            "dropped_refs": [[str(ref), str(reason)] for ref, reason in self.dropped_refs],
        }


@dataclass
class SurfaceFunnel:
    """单注入面漏斗：四段 StageObservation + 单调性校验。"""

    surface: str
    stages: dict[str, StageObservation] = field(default_factory=dict)

    def observe(
        self,
        stage: str,
        *,
        items: int,
        tokens: int = 0,
        reasons: dict[str, int] | None = None,
        dropped_refs: list[tuple[str, str]] | None = None,
    ) -> StageObservation:
        observation = StageObservation(stage=stage, items=max(0, int(items)), tokens=max(0, int(tokens)))
        if reasons:
            observation.reasons = dict(reasons)
        if dropped_refs:
            observation.dropped_refs = list(dropped_refs)
        self.stages[stage] = observation
        return observation

    def stage(self, stage: str) -> StageObservation:
        return self.stages.setdefault(stage, StageObservation(stage=stage))

    def validate(self) -> list[str]:
        """漏斗单调性：下游计数不得大于上游（违例返回人读错误列表）。"""
        errors: list[str] = []
        ordered = [name for name in STAGE_NAMES if name in self.stages]
        for upstream, downstream in zip(ordered, ordered[1:]):
            up = self.stages[upstream].items
            down = self.stages[downstream].items
            if down > up:
                errors.append(f"{self.surface}: {downstream}({down}) > {upstream}({up})")
        return errors

    def to_payload(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "stages": {
                name: self.stages[name].to_payload() for name in STAGE_NAMES if name in self.stages
            },
            "consistent": not self.validate(),
        }


def make_source_ref(
    *,
    kind: str,
    ref_id: str,
    content: str = "",
    tokens: int | None = None,
    marker: str | None = None,
    token_estimator: Callable[[str], int] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构造一条 source_ref（metadata-only：id/类型/长度/短哈希/token）。

    ``extra`` 只接受标量元数据（page_number / chunk_index / relevance 等），
    值若为非标量会被丢弃——防止正文借道混入；字符串标量截断到
    ``_MAX_EXTRA_STR_LEN``（C-08 N6：未来调用方误把长文本放标量 extra 时
    也不至于整段入册）。
    """
    content_len, content_hash = content_fingerprint(content)
    if tokens is None:
        estimator = token_estimator or _FALLBACK_TOKEN_ESTIMATOR
        tokens = int(estimator(content))
    entry: dict[str, Any] = {
        "ref": str(ref_id),
        "kind": str(kind),
        "tokens": max(0, int(tokens)),
        "content_len": content_len,
        "content_hash": content_hash,
    }
    if marker:
        entry["marker"] = str(marker)
    if extra:
        scalars = {
            key: (value[:_MAX_EXTRA_STR_LEN] if isinstance(value, str) else value)
            for key, value in extra.items()
            if isinstance(value, (str, int, float, bool)) or value is None
        }
        if scalars:
            entry["extra"] = scalars
    return entry


def document_ref(file_id: Any, chunk_id: Any) -> str:
    """RAG 文档切片 ref：``doc:<file_id>:<chunk_id>``（缺失段填 ``-``）。"""
    return f"doc:{_ref_part(file_id)}:{_ref_part(chunk_id)}"


def episodic_ref(memory_id: Any) -> str:
    return f"mem:{_ref_part(memory_id)}"


def experience_ref(record_id: Any) -> str:
    return f"exp:{_ref_part(record_id)}"


def _ref_part(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else "-"


def align_markers_to_refs(
    refs: list[dict[str, Any]],
    markers: list[str] | None,
) -> tuple[list[dict[str, Any]], str]:
    """把 C-04 ``[S#]`` 标记按注入顺序对齐到 source_ref。

    材料块行首 ``[N]`` 序号按 chunks 列表顺序生成（graph_rag.format_filtered_
    study_materials_context），annotate 后映射为 ``S<出现序>``，因此第 k 个
    标记对应第 k 条 ref。数量不一致（multi-hop 预构建块、JIT 裁剪、budget
    截断）时**诚实降级** ``alignment="unverified"``，绝不强行错位对齐。
    """
    aligned = [dict(entry) for entry in refs]
    if not markers:
        return aligned, "no_markers"
    if len(markers) != len(aligned):
        return aligned, "unverified"
    for entry, marker in zip(aligned, markers):
        entry["marker"] = str(marker)
    return aligned, "aligned"


# ---------------------------------------------------------------------------
# bloat / inert（harmful 候选）定位
# ---------------------------------------------------------------------------


def detect_context_bloat(
    section_tokens: dict[str, int],
    *,
    total_tokens: int | None = None,
    share_threshold: float = DEFAULT_BLOAT_SHARE_THRESHOLD,
) -> list[dict[str, Any]]:
    """分区 token 占比 → bloat 标记。

    ``section_tokens`` 是「实际注入」的分区 token 计量（如 context_pack 的
    token_usage：conversation/documents/galaxy/task_error/cognitive + 记忆面
    ``memory``）。占比 = 分区 / 总注入（total 缺省用分区和）。返回超阈分区
    列表 ``[{section, tokens, share}]``（按占比降序）；无超阈返回空表。
    """
    usage = {str(k): max(0, int(v)) for k, v in (section_tokens or {}).items()}
    total = int(total_tokens) if total_tokens else sum(usage.values())
    if total <= 0:
        return []
    flags: list[dict[str, Any]] = []
    for section, tokens in usage.items():
        if tokens <= 0:
            continue
        share = tokens / total
        if share >= share_threshold:
            flags.append({"section": section, "tokens": tokens, "share": round(share, 4)})
    flags.sort(key=lambda item: item["share"], reverse=True)
    return flags


def flag_inert_refs(
    source_refs: list[dict[str, Any]],
    *,
    cited_markers: list[str] | None,
    supported_markers: list[str] | None,
    used_refs: set[str] | None = None,
) -> list[dict[str, Any]]:
    """「注入了但零引用零支撑」的材料 → inert（harmful 候选）标记。

    - 文档 ref：其 marker 既不在 cited 也不在 answer_supported → inert
      （占预算、稀释注意力，本轮未产生任何效用）；
    - 记忆 ref：不在 ``used_refs``（调用方由答案重叠/引用判定给出）→ inert。
    无 marker 的文档 ref（bullet 格式 / multi-hop）无法判定引用，**不误标**。
    """
    cited = {str(marker) for marker in (cited_markers or [])}
    supported = {str(marker) for marker in (supported_markers or [])}
    used = {str(ref) for ref in (used_refs or set())}
    inert: list[dict[str, Any]] = []
    for entry in source_refs or []:
        ref = str(entry.get("ref") or "")
        kind = str(entry.get("kind") or "")
        marker = entry.get("marker")
        if kind == REF_KIND_DOCUMENT:
            if not marker:
                continue
            if str(marker) not in cited and str(marker) not in supported:
                inert.append({"ref": ref, "marker": str(marker), "tokens": int(entry.get("tokens") or 0)})
        else:
            if ref and ref not in used:
                inert.append({"ref": ref, "tokens": int(entry.get("tokens") or 0)})
    return inert


# ---------------------------------------------------------------------------
# 产出侧：从各面已有观测拼装单一记录
# ---------------------------------------------------------------------------


def build_episodic_funnel(
    *,
    candidate_rows: list[Any],
    prefilter_allowed_count: int,
    prefilter_reasons: dict[str, int],
    prefilter_dropped_refs: list[tuple[str, str]],
    ranked_rows: list[Any],
    injected_rows: list[Any],
    rank_cut_reason: str = REASON_RANK_CUTOFF,
    selfcheck_dropped_refs: list[tuple[str, str]] | None = None,
    summary_field: str = "summary",
    token_estimator: Callable[[str], int] | None = None,
) -> SurfaceFunnel:
    """episodic 记忆漏斗（stage34 装配面）。

    candidates=预筛前全集；filtered=M-03 预筛通过；ranked=纠偏/重要性排序
    （重排不淘汰，计数不变）；injected=最终进 payload 的条目。rank 截断与
    M-05 selfcheck 降档都记在 injected 段的 reasons 里。
    """
    estimator = token_estimator or _FALLBACK_TOKEN_ESTIMATOR
    funnel = SurfaceFunnel(surface=SURFACE_EPISODIC)
    funnel.observe(
        STAGE_CANDIDATES,
        items=len(candidate_rows),
        tokens=sum(int(estimator(str(getattr(row, summary_field, "") or ""))) for row in candidate_rows),
    )
    funnel.observe(
        STAGE_FILTERED,
        items=max(0, int(prefilter_allowed_count)),
        tokens=sum(int(estimator(str(getattr(row, summary_field, "") or ""))) for row in ranked_rows),
        reasons=dict(prefilter_reasons or {}),
        dropped_refs=[(ref, clamp_drop_reason(reason)) for ref, reason in (prefilter_dropped_refs or [])],
    )
    funnel.observe(
        STAGE_RANKED,
        items=len(ranked_rows),
        tokens=sum(int(estimator(str(getattr(row, summary_field, "") or ""))) for row in ranked_rows),
    )
    injected = funnel.observe(
        STAGE_INJECTED,
        items=len(injected_rows),
        tokens=sum(int(estimator(str(entry.get("summary") or ""))) for entry in injected_rows if isinstance(entry, dict)),
    )
    if len(ranked_rows) > len(injected_rows):
        injected.reasons[REASON_RANK_CUTOFF] = injected.reasons.get(REASON_RANK_CUTOFF, 0) + (
            len(ranked_rows) - len(injected_rows)
        )
    for ref, reason in selfcheck_dropped_refs or []:
        injected.dropped_refs.append((ref, REASON_SELFCHECK_INTERNAL))
        injected.reasons[REASON_SELFCHECK_INTERNAL] = injected.reasons.get(REASON_SELFCHECK_INTERNAL, 0) + 1
    return funnel


def build_experience_funnel(
    meta: dict[str, Any],
    *,
    injected_rows: list[Any] | None = None,
    token_estimator: Callable[[str], int] | None = None,
) -> SurfaceFunnel:
    """experience 经验漏斗——从既有 ``experience_memory_meta``（M-06/M-05 计数）
    升级为四段漏斗（C-08 前：只有 total_candidates/surfaced 两个数）。"""
    estimator = token_estimator or _FALLBACK_TOKEN_ESTIMATOR
    funnel = SurfaceFunnel(surface=SURFACE_EXPERIENCE)
    total_candidates = max(0, int((meta or {}).get("total_candidates") or 0))
    internal_only = max(0, int((meta or {}).get("internal_only") or 0))
    surfaced = int((meta or {}).get("surfaced") or 0)
    if injected_rows is None:
        surfaced_tokens = int((meta or {}).get("tokens") or 0)
    else:
        surfaced_tokens = sum(int(estimator(str(entry.get("claim") or ""))) for entry in injected_rows if isinstance(entry, dict))
    funnel.observe(STAGE_CANDIDATES, items=total_candidates)
    funnel.observe(
        STAGE_FILTERED,
        items=max(0, total_candidates - internal_only),
        reasons={REASON_SELFCHECK_INTERNAL: internal_only} if internal_only else {},
    )
    funnel.observe(STAGE_RANKED, items=max(0, total_candidates - internal_only))
    funnel.observe(STAGE_INJECTED, items=max(surfaced, 0), tokens=surfaced_tokens)
    return funnel


def build_document_funnel(
    retrieval: dict[str, Any],
    *,
    injected_tokens: int = 0,
    injected_chunks: int | None = None,
    budget: dict[str, Any] | None = None,
) -> SurfaceFunnel:
    """RAG 文档漏斗——从既有 ``document_context_retrieval`` +
    ``document_context_budget``（C-06 裁剪面）拼装。

    candidates=retrieved；filtered=passed（阈值过滤）；ranked=预算内展示
    （budget.shown_results 有值时）；injected=最终 document_block（shadow 模式
    只存候选不注入 → injected=0，诚实记录）。
    """
    funnel = SurfaceFunnel(surface=SURFACE_DOCUMENTS)
    candidates = max(0, int((retrieval or {}).get("total_retrieved") or 0))
    passed = max(0, int((retrieval or {}).get("total_passed") or 0))
    funnel.observe(STAGE_CANDIDATES, items=candidates)
    filtered = funnel.observe(
        STAGE_FILTERED,
        items=passed,
        reasons={REASON_OTHER: candidates - passed} if candidates > passed else {},
    )
    if candidates > passed:
        filtered.dropped_refs.append(("-", "relevance_threshold"))
    shown = None
    if budget:
        raw_shown = (budget or {}).get("shown_results")
        if isinstance(raw_shown, int):
            shown = max(0, raw_shown)
    if shown is None:
        shown = passed
    ranked = funnel.observe(
        STAGE_RANKED,
        items=shown,
        reasons={REASON_BUDGET_TRUNCATED: passed - shown} if passed > shown else {},
    )
    if passed > shown:
        ranked.dropped_refs.append(("-", REASON_BUDGET_TRUNCATED))
    injected_items = candidates if injected_chunks is None else max(0, int(injected_chunks))
    funnel.observe(STAGE_INJECTED, items=injected_items, tokens=max(0, int(injected_tokens)))
    return funnel


def build_context_funnel_record(
    *,
    request_id: str | None = None,
    trace_id: str | None = None,
    memory_funnel: dict[str, Any] | None = None,
    experience_meta: dict[str, Any] | None = None,
    retrieval: dict[str, Any] | None = None,
    document_budget: dict[str, Any] | None = None,
    context_budget: dict[str, Any] | None = None,
    citation_outcome: dict[str, Any] | None = None,
    source_refs: list[dict[str, Any]] | None = None,
    citation_markers: list[str] | None = None,
    document_injected: bool = False,
    document_block_tokens: int = 0,
    memory_refs: list[dict[str, Any]] | None = None,
    used_memory_refs: set[str] | None = None,
    token_estimator: Callable[[str], int] | None = None,
) -> dict[str, Any]:
    """拼装单一 context funnel 记录（metadata-only，JSON-safe）。

    输入全部是各装配点**已有**的观测 dict——本函数零业务推理、只做收敛、
    对齐与判定；任何输入缺失都降级为空观测，绝不抛错阻断主链。
    """
    estimator = token_estimator or _FALLBACK_TOKEN_ESTIMATOR
    funnels: dict[str, SurfaceFunnel] = {}

    memory_payload = memory_funnel if isinstance(memory_funnel, dict) else {}
    if memory_payload:
        funnels[SURFACE_EPISODIC] = _funnel_from_payload(SURFACE_EPISODIC, memory_payload)
    if isinstance(experience_meta, dict) and experience_meta:
        funnels[SURFACE_EXPERIENCE] = build_experience_funnel(
            experience_meta,
            token_estimator=estimator,
        )

    retrieval_payload = retrieval if isinstance(retrieval, dict) else {}
    if retrieval_payload or document_injected:
        document_tokens = int(document_block_tokens)
        if not document_tokens and isinstance(document_budget, dict):
            document_tokens = int(document_budget.get("token_usage") or 0)
        funnels[SURFACE_DOCUMENTS] = build_document_funnel(
            retrieval_payload,
            injected_tokens=document_tokens,
            injected_chunks=1 if document_injected else 0,
            budget=document_budget if isinstance(document_budget, dict) else None,
        )

    refs, alignment = align_markers_to_refs(list(source_refs or []), list(citation_markers or []))
    if memory_refs:
        refs = refs + [dict(entry) for entry in memory_refs]

    # bloat：分区 token（context_budget 的 token_usage + 记忆面注入 token）。
    section_tokens: dict[str, int] = {}
    budget_payload = context_budget if isinstance(context_budget, dict) else {}
    raw_usage = budget_payload.get("token_usage")
    if isinstance(raw_usage, dict):
        section_tokens.update({str(k): int(v) for k, v in raw_usage.items() if isinstance(v, (int, float))})
    memory_tokens = sum(funnel.stage(STAGE_INJECTED).tokens for funnel in funnels.values() if funnel.surface != SURFACE_DOCUMENTS)
    if memory_tokens:
        section_tokens["memory"] = memory_tokens
    total_tokens = budget_payload.get("metadata", {}).get("total_tokens") if isinstance(budget_payload.get("metadata"), dict) else None
    bloat = detect_context_bloat(section_tokens, total_tokens=int(total_tokens) if total_tokens else None)

    outcome = citation_outcome if isinstance(citation_outcome, dict) else {}
    inert = flag_inert_refs(
        refs,
        cited_markers=outcome.get("cited"),
        supported_markers=outcome.get("answer_supported"),
        used_refs=used_memory_refs,
    )

    consistency: list[str] = []
    for funnel in funnels.values():
        consistency.extend(funnel.validate())

    return {
        "version": FUNNEL_VERSION,
        "request_id": str(request_id) if request_id else None,
        # O-02 trace spine：漏斗记录挂到全链 trace_id（context 关联可查）。
        "trace_id": str(trace_id) if trace_id else None,
        "funnels": {surface: funnel.to_payload() for surface, funnel in sorted(funnels.items())},
        "source_refs": refs,
        "marker_alignment": alignment,
        "section_tokens": section_tokens,
        "total_tokens": int(total_tokens) if total_tokens else sum(section_tokens.values()),
        "bloat": bloat,
        "inert_refs": inert,
        "citation": {
            "retrieved": outcome.get("retrieved"),
            "cited": outcome.get("cited"),
            "unknown_cited": outcome.get("unknown_cited"),
            "answer_supported": outcome.get("answer_supported"),
            "faithfulness_ok": outcome.get("faithfulness_ok"),
        },
        "consistent": not consistency,
        "invariants": consistency,
    }


def _funnel_from_payload(surface: str, payload: dict[str, Any]) -> SurfaceFunnel:
    """把 context_builder 侧产出的漏斗 payload 还原为 SurfaceFunnel。"""
    funnel = SurfaceFunnel(surface=surface)
    raw_stages = payload.get("stages")
    if isinstance(raw_stages, dict):
        for stage, observation in raw_stages.items():
            if stage not in STAGE_NAMES or not isinstance(observation, dict):
                continue
            entry = funnel.observe(
                stage,
                items=int(observation.get("items") or 0),
                tokens=int(observation.get("tokens") or 0),
            )
            raw_reasons = observation.get("reasons")
            if isinstance(raw_reasons, dict):
                entry.reasons = {str(k): int(v) for k, v in raw_reasons.items()}
            raw_dropped = observation.get("dropped_refs")
            if isinstance(raw_dropped, list):
                entry.dropped_refs = [
                    (str(pair[0]), str(pair[1])) for pair in raw_dropped if isinstance(pair, (list, tuple)) and len(pair) == 2
                ]
    return funnel


# ---------------------------------------------------------------------------
# 隐私探针（测试面）：正文泄漏扫描
# ---------------------------------------------------------------------------


def find_content_leak(record: dict[str, Any], samples: list[str], *, min_len: int = 8) -> list[str]:
    """扫描记录序列化结果是否泄漏正文样本（单测钉「无正文红线」用）。

    返回泄漏样本列表（空 = 干净）。样本短于 ``min_len`` 忽略（子串误报）。
    """
    blob = json.dumps(record, ensure_ascii=False, default=str)
    leaked: list[str] = []
    for sample in samples or []:
        text = str(sample or "")
        if len(text) < min_len:
            continue
        if text in blob:
            leaked.append(text)
    return leaked


# ---------------------------------------------------------------------------
# Prometheus 出口（有界 label；失败绝不阻断主链）
# ---------------------------------------------------------------------------


def record_funnel_metrics(record: dict[str, Any]) -> None:
    """漏斗记录 → 有界 label Prometheus 计数（best-effort）。

    label 基数守卫：stage ∈ STAGE_NAMES、surface ∈ SURFACES+other、
    outcome ∈ {kept, dropped}、reason 经 clamp；任何异常吞掉（观测永不
    影响业务主链）。
    """
    try:
        from app.core.business_metrics import (
            CONTEXT_FUNNEL_BLOAT_SECTION_TOTAL,
            CONTEXT_FUNNEL_INERT_REFS_TOTAL,
            CONTEXT_FUNNEL_STAGE_ITEMS_TOTAL,
        )

        for surface, funnel in (record.get("funnels") or {}).items():
            clamped_surface = clamp_surface(str(surface))
            for stage, observation in (funnel.get("stages") or {}).items():
                if stage not in STAGE_NAMES:
                    continue
                items = int(observation.get("items") or 0)
                CONTEXT_FUNNEL_STAGE_ITEMS_TOTAL.labels(
                    stage=str(stage), surface=clamped_surface, outcome="kept"
                ).inc(items)
                dropped = 0
                for reason, count in (observation.get("reasons") or {}).items():
                    CONTEXT_FUNNEL_STAGE_ITEMS_TOTAL.labels(
                        stage=str(stage),
                        surface=clamped_surface,
                        outcome="dropped",
                    ).inc(int(count))
                    dropped += int(count)
                if dropped and items == 0:
                    # 全淘汰阶段：kept 不再重复计数（items=0 已隐含）。
                    pass
        for entry in record.get("inert_refs") or []:
            ref = str(entry.get("ref") or "")
            surface = "other"
            if ref.startswith("doc:"):
                surface = SURFACE_DOCUMENTS
            elif ref.startswith("mem:"):
                surface = SURFACE_EPISODIC
            elif ref.startswith("exp:"):
                surface = SURFACE_EXPERIENCE
            CONTEXT_FUNNEL_INERT_REFS_TOTAL.labels(surface=surface).inc()
        for flag in record.get("bloat") or []:
            CONTEXT_FUNNEL_BLOAT_SECTION_TOTAL.labels(section=str(flag.get("section") or "other")).inc()
    except Exception:  # pragma: no cover - metrics must never break the chain
        pass


def funnel_log_line(record: dict[str, Any]) -> str:
    """记录 → 一行 metadata-only 摘要（日志面；无正文）。"""
    parts: list[str] = []
    for surface, funnel in (record.get("funnels") or {}).items():
        stages = funnel.get("stages") or {}
        chain = "/".join(
            f"{stages[name].get('items', 0)}" for name in STAGE_NAMES if name in stages
        )
        tokens = (stages.get(STAGE_INJECTED) or {}).get("tokens", 0)
        parts.append(f"{surface}={chain}i/{tokens}t")
    refs = record.get("source_refs") or []
    bloat = [flag.get("section") for flag in record.get("bloat") or []]
    inert = len(record.get("inert_refs") or [])
    citation = record.get("citation") or {}
    return (
        "C-08 context funnel"
        + (f" {record.get('request_id')}" if record.get('request_id') else "")
        + (f" trace={record.get('trace_id')}" if record.get('trace_id') else "")
        + (" " + " ".join(parts) if parts else "")
        + f" refs={len(refs)} alignment={record.get('marker_alignment')}"
        + f" bloat={','.join(bloat) if bloat else '-'} inert={inert}"
        + f" cited={citation.get('cited_count') if citation.get('cited_count') is not None else '-'}"
        + f" faithful={citation.get('faithfulness_ok')}"
        + f" consistent={record.get('consistent')}"
    )
