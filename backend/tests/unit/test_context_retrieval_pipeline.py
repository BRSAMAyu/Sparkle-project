"""C-03 · knowledge 权限预筛 + 硬过滤→rerank 管道单元测试。

守卫对象（对齐 M-03 test_memory_retrieval_prefilter 的纪律）：

1. **封闭词表冻结**：source_type 与 rag_indexing_service 写方 parity、reason
   code 全集逐字冻结、维度求值顺序钉死（reorder 必红且必须 bump 版本）；
2. **fail-closed 矩阵**：无归属 document chunk、无检索用户、词表外
   source_type 一律砍除——变异回 fail-open 必红；
3. **形状 parity**：``KnowledgeFilterResult`` 与 M-03 ``PrefilterResult``
   字段集/metric payload key 集逐字对齐；pipeline 报告 key 集冻结
   （C-02 MANIFEST_* 同纪律）；
4. **管道语义**：memory 通道委托 M-03（同 allowed/同 payload）、rerank_fn
   只见合法候选、缺上下文 fail-loud、跨通道顺序确定性、同步/异步面一致。
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.time_utils import utcnow
from app.services import context_retrieval_pipeline as crp
from app.services.context_retrieval_pipeline import (
    CHANNEL_KNOWLEDGE,
    CHANNEL_MEMORY,
    CHANNEL_REPORT_KEYS,
    KNOWLEDGE_FILTER_DIMENSIONS,
    KNOWLEDGE_PERMISSION_FILTER_VERSION,
    KNOWLEDGE_REJECTION_REASONS,
    KNOWLEDGE_SOURCE_TYPES,
    PIPELINE_CHANNELS,
    PIPELINE_REPORT_KEYS,
    RERANK_REPORT_KEYS,
    KnowledgeAccessContext,
    KnowledgeFilterResult,
    build_pipeline_report,
    prefilter_knowledge_candidates,
    run_hard_filter_pipeline,
    run_hard_filter_pipeline_async,
)
from app.services.memory_retrieval_prefilter import (
    PURPOSE_LLM_CONTEXT,
    PrefilterResult,
    Rejection,
    RetrievalContext,
    prefilter_candidates,
)
from app.services.rag_indexing_service import SOURCE_DOCUMENT_CHUNK, SOURCE_NODE_DESCRIPTION

USER = "user-1"
OTHER = "user-2"


def _ctx(user_id: str | None = USER, groups: frozenset[str] = frozenset()) -> KnowledgeAccessContext:
    return KnowledgeAccessContext(user_id=user_id, allowed_group_ids=groups)


def _doc(**kwargs) -> SimpleNamespace:
    defaults = {"id": "c-1", "content": "lorem ipsum", "source_type": SOURCE_DOCUMENT_CHUNK}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# 1. 封闭词表冻结
# ---------------------------------------------------------------------------


def test_source_type_vocabulary_pinned():
    """写方 parity：rag_indexing_service 加第三个 source_type 写方时必红。"""
    assert frozenset({SOURCE_NODE_DESCRIPTION, SOURCE_DOCUMENT_CHUNK}) == KNOWLEDGE_SOURCE_TYPES
    assert frozenset({SOURCE_NODE_DESCRIPTION}) == crp.SHARED_SOURCE_TYPES


def test_reason_codes_frozen():
    """reason code 全集逐字冻结：新增/删除 code 必须 bump
    KNOWLEDGE_PERMISSION_FILTER_VERSION 并同步本测试 + 双 reviewer。"""
    assert (
        frozenset(
            {
                "knowledge:unknown_source_type",
                "knowledge:no_user_context",
                "knowledge:group_inaccessible",
                "knowledge:wrong_user",
                "knowledge:unattributed",
                "knowledge:lifecycle_inactive",
            }
        )
        == KNOWLEDGE_REJECTION_REASONS
    )


def test_filter_dimensions_order_is_pinned():
    """维度求值顺序冻结：identity → lifecycle（首个失败维度独占归因）。
    reorder 必红且必须 bump KNOWLEDGE_PERMISSION_FILTER_VERSION。"""
    assert tuple(dimension.value for dimension in KNOWLEDGE_FILTER_DIMENSIONS) == ("identity", "lifecycle")


def test_pipeline_channels_frozen():
    assert PIPELINE_CHANNELS == (CHANNEL_MEMORY, CHANNEL_KNOWLEDGE)


def test_report_key_sets_frozen():
    assert set(PIPELINE_REPORT_KEYS) == {
        "schema_version",
        "channels",
        "rerank",
        "total_latency_ms",
        "tokens_before",
        "tokens_after",
        "tokens_saved",
    }
    assert set(CHANNEL_REPORT_KEYS) == {
        "channel",
        "version",
        "input_count",
        "allowed_count",
        "rejected_count",
        "dimension_counts",
        "reason_counts",
        "latency_ms",
        "tokens_before",
        "tokens_after",
    }
    assert set(RERANK_REPORT_KEYS) == {"input_count", "output_count", "latency_ms", "skipped"}


# ---------------------------------------------------------------------------
# 2. 形状 parity（与 M-03 PrefilterResult 逐字对齐）
# ---------------------------------------------------------------------------


def test_result_shape_parity_with_m03():
    """KnowledgeFilterResult 与 M-03 PrefilterResult 字段集逐字相等；
    metric payload key 集逐字相等（version 值不同是唯一允许差异）。"""
    m03_names = [f.name for f in dataclass_fields(PrefilterResult)]
    c03_names = [f.name for f in dataclass_fields(KnowledgeFilterResult)]
    assert c03_names == m03_names

    result = prefilter_knowledge_candidates([_doc(user_id=USER)], _ctx())
    m03_payload_keys = set(
        PrefilterResult(
            allowed=[], rejections=[], input_count=0, dimension_counts={}, reason_counts={}
        ).to_metric_payload()
    )
    payload = result.to_metric_payload()
    assert set(payload) == m03_payload_keys
    assert payload["version"] == KNOWLEDGE_PERMISSION_FILTER_VERSION


def test_rejection_shape_reuses_m03_dataclass():
    """rejections 元素必须是 M-03 的 Rejection（单一形状事实源，消费方
    D-06/O-02 不需要第二套解析）。"""
    result = prefilter_knowledge_candidates([_doc(user_id=OTHER)], _ctx())
    assert result.rejections
    assert all(isinstance(rejection, Rejection) for rejection in result.rejections)
    rejection = result.rejections[0]
    assert rejection.dimension == "identity"
    assert rejection.reason == "knowledge:wrong_user"
    assert rejection.record_id == "c-1"
    assert rejection.detail  # detail carries attribution evidence


# ---------------------------------------------------------------------------
# 3. fail-closed 矩阵（每个 reason code 的行为钉死）
# ---------------------------------------------------------------------------


def _one_reason(docs, ctx) -> tuple[list[str], set[str], dict[str, int]]:
    result = prefilter_knowledge_candidates(docs, ctx)
    return (
        [d.id for d in result.allowed],
        {r.reason for r in result.rejections},
        dict(result.reason_counts),
    )


def test_shared_node_description_always_permitted():
    allowed, rejections, _ = _one_reason([_doc(source_type=SOURCE_NODE_DESCRIPTION)], _ctx())
    assert allowed == ["c-1"] and not rejections


def test_personal_chunk_requires_user_match():
    _, reasons, counts = _one_reason([_doc(user_id=OTHER)], _ctx())
    assert reasons == {"knowledge:wrong_user"}
    assert counts == {"knowledge:wrong_user": 1}


def test_own_personal_chunk_permitted():
    allowed, reasons, _ = _one_reason([_doc(user_id=USER)], _ctx())
    assert allowed == ["c-1"] and not reasons


def test_group_chunk_group_scoping():
    groups = frozenset({"g-1"})
    allowed, _, _ = _one_reason([_doc(group_id="g-1", user_id="owner-9")], _ctx(groups=groups))
    assert allowed == ["c-1"]
    _, reasons, _ = _one_reason([_doc(group_id="g-2", user_id="owner-9")], _ctx(groups=groups))
    assert reasons == {"knowledge:group_inaccessible"}


def test_no_user_context_fail_closed_for_document_chunks():
    """fail-closed：无检索用户时 document chunk 一律砍（旧内联检查是放行——
    本测试钉住收紧后的语义）。node_description 不受影响。"""
    _, reasons, _ = _one_reason([_doc(user_id=USER)], _ctx(user_id=None))
    assert reasons == {"knowledge:no_user_context"}
    allowed, reasons, _ = _one_reason([_doc(source_type=SOURCE_NODE_DESCRIPTION)], _ctx(user_id=None))
    assert allowed == ["c-1"] and not reasons


def test_unattributed_document_chunk_fail_closed():
    """fail-closed：无 user_id 且无 group_id 的 document chunk 砍除
    （旧内联检查 ``not doc_user_id → True`` 是放行——本测试钉住收紧）。"""
    _, reasons, _ = _one_reason([_doc()], _ctx())
    assert reasons == {"knowledge:unattributed"}


def test_unknown_source_type_fail_closed():
    _, reasons, _ = _one_reason([_doc(source_type="legacy_thing")], _ctx())
    assert reasons == {"knowledge:unknown_source_type"}
    _, reasons, _ = _one_reason([_doc(source_type="")], _ctx())
    assert reasons == {"knowledge:unknown_source_type"}


def test_lifecycle_inactive_rejected_only_when_carried():
    _, reasons, _ = _one_reason([_doc(user_id=USER, lifecycle_status="archived")], _ctx())
    assert reasons == {"knowledge:lifecycle_inactive"}
    # 字段缺失（dense 面传输限制）→ 放行（删除可见性归 E-05 key 失效）
    allowed, _, _ = _one_reason([_doc(user_id=USER)], _ctx())
    assert allowed == ["c-1"]


def test_identity_owns_attribution_when_both_dimensions_fail():
    """归因确定性：identity 与 lifecycle 同时失败 → identity 独占（顺序钉死）。"""
    _, reasons, counts = _one_reason([_doc(user_id=OTHER, lifecycle_status="archived")], _ctx())
    assert reasons == {"knowledge:wrong_user"}
    assert counts == {"knowledge:wrong_user": 1}


def test_group_scope_beats_user_match():
    """群组归属优先于 user_id 匹配（与旧内联检查的判定序一致：先 group 后
    personal——group 共享不在本人可访问集即砍，即使 user_id 恰好是本人）。"""
    _, reasons, _ = _one_reason([_doc(group_id="g-9", user_id=USER)], _ctx())
    assert reasons == {"knowledge:group_inaccessible"}


def test_dict_candidates_supported():
    doc = {"id": "c-dict", "content": "x", "source_type": "document_chunk", "user_id": OTHER}
    _, reasons, _ = _one_reason([doc], _ctx())
    assert reasons == {"knowledge:wrong_user"}


def test_counts_and_input_count():
    docs = [
        _doc(id="a", user_id=USER),
        _doc(id="b", user_id=OTHER),
        _doc(id="c", source_type=SOURCE_NODE_DESCRIPTION),
        _doc(id="d", group_id="g-2"),
    ]
    result = prefilter_knowledge_candidates(docs, _ctx())
    assert result.input_count == 4
    assert result.allowed_count == 2
    assert result.dimension_counts == {"identity": 2, "lifecycle": 0}
    assert result.reason_counts == {"knowledge:wrong_user": 1, "knowledge:group_inaccessible": 1}


def test_boolean_compatibility_face():
    assert crp.knowledge_candidate_permitted(_doc(user_id=USER), _ctx()) is True
    assert crp.knowledge_candidate_permitted(_doc(user_id=OTHER), _ctx()) is False


def test_context_normalization():
    """group ids str 归一化 + user_id strip；空串 user_id 显式归一为 None。"""
    ctx = KnowledgeAccessContext(user_id=" user-1 ", allowed_group_ids=frozenset({uuid4()}))
    assert ctx.user_id == "user-1"
    assert all(isinstance(g, str) for g in ctx.allowed_group_ids)
    assert KnowledgeAccessContext(user_id="   ").user_id is None


# ---------------------------------------------------------------------------
# 4. 管道：memory 委托 M-03 / rerank 只见合法 / fail-loud / 形状
# ---------------------------------------------------------------------------


def _memory_record(**kwargs):
    from app.models.memory import EpisodicMemory

    defaults = {
        "user_id": uuid4(),
        "summary": "pipeline memory",
        "source_type": "chat_turn",
        "source_lane": "direct_capture",
        "subject_type": "self",
        "occurred_at": utcnow() - timedelta(hours=1),
        "importance_score": 0.5,
        "evidence_refs": [{"type": "user_state", "id": "t"}],
    }
    defaults.update(kwargs)
    return EpisodicMemory(**defaults)


def _retrieval_ctx(user_id) -> RetrievalContext:
    return RetrievalContext(user_id=str(user_id), purpose=PURPOSE_LLM_CONTEXT, now=utcnow())


def test_pipeline_memory_channel_delegates_to_m03():
    """memory 通道语义 == M-03 直调（同 allowed、同 metric payload 除
    latency/tokens 外逐字一致）。"""
    user_id = uuid4()
    legal = _memory_record(user_id=user_id, summary="LEGAL")
    wrong_user = _memory_record(user_id=uuid4(), summary="WRONG")
    ctx = _retrieval_ctx(user_id)

    direct = prefilter_candidates([legal, wrong_user], ctx)
    result = run_hard_filter_pipeline(memory_candidates=[legal, wrong_user], retrieval_ctx=ctx)

    assert result.channels[CHANNEL_MEMORY].allowed == direct.allowed
    payload = result.channels[CHANNEL_MEMORY].metric_payload
    assert payload["input_count"] == direct.input_count
    assert payload["allowed_count"] == direct.allowed_count
    assert payload["reason_counts"] == dict(direct.reason_counts)
    assert payload["version"] == direct.to_metric_payload()["version"]  # M-03 version 原样


def test_pipeline_rerank_receives_only_legal_candidates():
    user_id = uuid4()
    memory = [_memory_record(user_id=user_id, summary="M-LEGAL"), _memory_record(user_id=uuid4(), summary="M-WRONG")]
    knowledge = [
        _doc(id="k-own", user_id=str(user_id)),
        _doc(id="k-foreign", user_id="user-2"),
    ]
    rerank_inputs: list[list] = []

    def rerank(candidates):
        rerank_inputs.append(list(candidates))
        return list(reversed(candidates))

    result = run_hard_filter_pipeline(
        memory_candidates=memory,
        retrieval_ctx=_retrieval_ctx(user_id),
        knowledge_candidates=knowledge,
        knowledge_ctx=_ctx(user_id=str(user_id)),
        rerank_fn=rerank,
    )
    assert len(rerank_inputs) == 1
    seen_ids = [getattr(candidate, "id", None) or getattr(candidate, "summary", None) for candidate in rerank_inputs[0]]
    # EpisodicMemory 无内存 id（未 flush）——按 summary/内容断言：
    summaries = [getattr(c, "summary", "") for c in rerank_inputs[0]]
    assert "M-WRONG" not in summaries and "M-LEGAL" in summaries
    assert "k-own" in seen_ids and "k-foreign" not in seen_ids
    # rerank 输出被采用（reversed）
    assert result.ranked[0] is rerank_inputs[0][-1]
    assert result.report["rerank"] == {
        "input_count": 2,
        "output_count": 2,
        "latency_ms": result.report["rerank"]["latency_ms"],
        "skipped": False,
    }


def test_pipeline_channel_order_memory_then_knowledge():
    user_id = uuid4()
    memory = [_memory_record(user_id=user_id)]
    knowledge = [_doc(id="k-1", user_id=str(user_id))]
    result = run_hard_filter_pipeline(
        memory_candidates=memory,
        retrieval_ctx=_retrieval_ctx(user_id),
        knowledge_candidates=knowledge,
        knowledge_ctx=_ctx(user_id=str(user_id)),
    )
    first, second = result.rerank_input[0], result.rerank_input[1]
    assert getattr(first, "summary", None) == "pipeline memory"
    assert getattr(second, "id", None) == "k-1"


def test_pipeline_fail_loud_without_context():
    user_id = uuid4()
    with pytest.raises(ValueError, match="retrieval_ctx"):
        run_hard_filter_pipeline(memory_candidates=[_memory_record(user_id=user_id)])
    with pytest.raises(ValueError, match="knowledge_ctx"):
        run_hard_filter_pipeline(knowledge_candidates=[_doc(user_id=str(user_id))])


def test_pipeline_report_shape_and_tokens():
    user_id = uuid4()
    long_own = _doc(id="k-own", user_id=str(user_id), content="own " * 100)
    foreign = _doc(id="k-foreign", user_id="user-2", content="foreign " * 100)
    result = run_hard_filter_pipeline(
        knowledge_candidates=[long_own, foreign],
        knowledge_ctx=_ctx(user_id=str(user_id)),
    )
    report = result.report
    assert set(report) == set(PIPELINE_REPORT_KEYS)
    assert set(report["channels"][CHANNEL_KNOWLEDGE]) == set(CHANNEL_REPORT_KEYS)
    assert set(report["rerank"]) == set(RERANK_REPORT_KEYS)
    assert report["schema_version"] == crp.PIPELINE_SCHEMA_VERSION
    assert report["rerank"]["skipped"] is True
    assert report["tokens_before"] > report["tokens_after"] > 0
    assert report["tokens_saved"] == report["tokens_before"] - report["tokens_after"]
    channel = report["channels"][CHANNEL_KNOWLEDGE]
    assert channel["input_count"] == 2 and channel["allowed_count"] == 1
    assert channel["reason_counts"] == {"knowledge:wrong_user": 1}
    assert channel["version"] == KNOWLEDGE_PERMISSION_FILTER_VERSION
    # 未参与的通道不占位（channels 只含有候选的通道）
    assert CHANNEL_MEMORY not in report["channels"]


def test_build_pipeline_report_is_sole_serialization_authority():
    outcome = crp.ChannelOutcome(
        channel=CHANNEL_KNOWLEDGE,
        allowed=[],
        metric_payload={
            "version": KNOWLEDGE_PERMISSION_FILTER_VERSION,
            "input_count": 3,
            "allowed_count": 1,
            "dimension_counts": {"identity": 2},
            "reason_counts": {"knowledge:wrong_user": 2},
        },
        latency_ms=1.5,
        tokens_before=300,
        tokens_after=100,
    )
    report = build_pipeline_report(
        channel_outcomes=[outcome],
        rerank_input_count=1,
        rerank_output_count=1,
        rerank_latency_ms=2.0,
        rerank_skipped=False,
        total_latency_ms=3.5,
    )
    assert set(report) == set(PIPELINE_REPORT_KEYS)
    assert set(report["channels"][CHANNEL_KNOWLEDGE]) == set(CHANNEL_REPORT_KEYS)
    assert report["channels"][CHANNEL_KNOWLEDGE]["rejected_count"] == 2


@pytest.mark.asyncio
async def test_async_face_same_semantics_as_sync():
    """async 面（galaxy 接线用）与同步面过滤语义逐字节一致；async rerank_fn
    在当前 loop 内 await。"""
    user_id = uuid4()
    knowledge = [_doc(id="k-own", user_id=str(user_id)), _doc(id="k-foreign", user_id="user-2")]
    rerank_inputs: list[list] = []

    async def rerank(candidates):
        rerank_inputs.append(list(candidates))
        return list(candidates)

    result = await run_hard_filter_pipeline_async(
        knowledge_candidates=knowledge,
        knowledge_ctx=_ctx(user_id=str(user_id)),
        rerank_fn=rerank,
    )
    assert [c.id for c in rerank_inputs[0]] == ["k-own"]
    assert [c.id for c in result.ranked] == ["k-own"]
    assert result.rerank_latency_ms is not None and result.rerank_latency_ms >= 0


def test_sync_face_rejects_async_rerank_in_running_loop():
    """同步面在运行中的 event loop 内拿到 awaitable rerank 结果 → 显式报错
    引导 async 面（不静默、不阻塞 loop）。"""
    import asyncio

    async def scenario():
        async def async_rerank(candidates):
            return list(candidates)

        return run_hard_filter_pipeline(
            knowledge_candidates=[_doc(user_id=USER)],
            knowledge_ctx=_ctx(),
            rerank_fn=async_rerank,
        )

    with pytest.raises(RuntimeError, match="run_hard_filter_pipeline_async"):
        asyncio.run(scenario())
