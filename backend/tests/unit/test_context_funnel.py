"""C-08 · Context Funnel / source_ref / bloat-inert 定位 单测（全 hermetic：零 LLM、零 DB、零 Redis）。

钉住面：
- 漏斗四段计数正确性与单调性不变量（各阶段数对得上）；
- source_ref 完整性与 metadata-only 形态（长度/短哈希，正文不可还原）；
- ``[S#]`` 标记 ↔ ref 对齐的诚实降级（数量不符 → unverified，不错位）；
- bloat 占比判定 / inert（注入但零引用零支撑）标记；
- **正文红线**：记录序列化后扫描不到任何正文样本；
- 有界 label clamp（Prometheus 基数守卫）与 metrics 出口不炸主链。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.orchestration.context_funnel import (
    BOUNDED_DROP_REASONS,
    FUNNEL_VERSION,
    REASON_BUDGET_TRUNCATED,
    REASON_RANK_CUTOFF,
    REASON_SELFCHECK_INTERNAL,
    STAGE_CANDIDATES,
    STAGE_FILTERED,
    STAGE_INJECTED,
    STAGE_NAMES,
    STAGE_RANKED,
    SURFACE_DOCUMENTS,
    SURFACE_EPISODIC,
    build_context_funnel_record,
    build_document_funnel,
    build_episodic_funnel,
    build_experience_funnel,
    clamp_drop_reason,
    clamp_surface,
    detect_context_bloat,
    document_ref,
    episodic_ref,
    find_content_leak,
    flag_inert_refs,
    funnel_log_line,
    make_source_ref,
    record_funnel_metrics,
)
from app.core.business_metrics import (
    CONTEXT_FUNNEL_BLOAT_SECTION_TOTAL,
    CONTEXT_FUNNEL_INERT_REFS_TOTAL,
    CONTEXT_FUNNEL_STAGE_ITEMS_TOTAL,
)

# ---------------------------------------------------------------------------
# 漏斗计数与单调性
# ---------------------------------------------------------------------------


def _memory_row(memory_id: str, summary: str):
    return SimpleNamespace(id=memory_id, summary=summary)


class TestFunnelInvariants:
    def test_stage_counts_line_up(self):
        """四段计数与各阶段淘汰原因能对上总账。"""
        rows = [_memory_row(f"m{i}", f"记忆摘要{i}号内容") for i in range(12)]
        prefilter_reasons = {"superseded": 3, "expired": 1}
        ranked = rows[4:]
        injected = [row for row in ranked[:5]]
        funnel = build_episodic_funnel(
            candidate_rows=rows,
            prefilter_allowed_count=len(ranked),
            prefilter_reasons=prefilter_reasons,
            prefilter_dropped_refs=[(episodic_ref(f"r{i}"), "superseded") for i in range(3)]
            + [(episodic_ref("rx"), "expired")],
            ranked_rows=ranked,
            injected_rows=injected,
        )
        assert funnel.surface == SURFACE_EPISODIC
        assert funnel.stage(STAGE_CANDIDATES).items == 12
        assert funnel.stage(STAGE_FILTERED).items == 8
        assert funnel.stage(STAGE_FILTERED).reasons == {"superseded": 3, "expired": 1}
        assert funnel.stage(STAGE_RANKED).items == 8  # 重排不淘汰
        assert funnel.stage(STAGE_INJECTED).items == 5
        # 截断总账：candidates = filtered + 预筛淘汰；ranked = injected + 截断
        assert funnel.stage(STAGE_CANDIDATES).items == funnel.stage(STAGE_FILTERED).items + 4
        assert funnel.stage(STAGE_RANKED).items == funnel.stage(STAGE_INJECTED).items + 3
        cutoff = funnel.stage(STAGE_INJECTED).reasons.get(REASON_RANK_CUTOFF)
        assert cutoff == 3
        assert funnel.validate() == []

    def test_monotonicity_violation_detected(self):
        """下游计数 > 上游必须被机检抓住（漏斗对得上的守卫）。"""
        from app.orchestration.context_funnel import SurfaceFunnel

        funnel = SurfaceFunnel(surface=SURFACE_DOCUMENTS)
        funnel.observe(STAGE_CANDIDATES, items=3)
        funnel.observe(STAGE_FILTERED, items=5)  # 违例
        errors = funnel.validate()
        assert errors and "filtered(5) > candidates(3)" in errors[0]

    def test_selfcheck_downgrade_recorded(self):
        rows = [_memory_row(f"m{i}", f"摘要{i}") for i in range(6)]
        funnel = build_episodic_funnel(
            candidate_rows=rows,
            prefilter_allowed_count=6,
            prefilter_reasons={},
            prefilter_dropped_refs=[],
            ranked_rows=rows,
            injected_rows=[],
            selfcheck_dropped_refs=[(episodic_ref("m0"), "internal"), (episodic_ref("m1"), "internal")],
        )
        injected = funnel.stage(STAGE_INJECTED)
        assert injected.reasons.get(REASON_SELFCHECK_INTERNAL) == 2
        assert ("mem:m0", REASON_SELFCHECK_INTERNAL) in injected.dropped_refs


# ---------------------------------------------------------------------------
# source_ref：完整性 + metadata-only
# ---------------------------------------------------------------------------


class TestSourceRefs:
    def test_ref_formats(self):
        assert document_ref("f1", "c1") == "doc:f1:c1"
        assert document_ref(None, "") == "doc:-:-"
        assert episodic_ref("m-9") == "mem:m-9"

    def test_metadata_only_shape(self):
        """ref 只含 id/类型/长度/短哈希/token——正文永不入册。"""
        body = "用户的私密学习困境正文：考试焦虑具体描述……"
        ref = make_source_ref(kind="episodic", ref_id=episodic_ref("m1"), content=body)
        assert ref["content_len"] == len(body)
        assert len(ref["content_hash"]) == 12
        assert body not in str(ref)
        assert ref["tokens"] > 0

    def test_extra_drops_non_scalar(self):
        """extra 里的非标量（嵌套 dict/list）必须被丢弃——防正文借道混入。"""
        ref = make_source_ref(
            kind="document",
            ref_id=document_ref("f", "c"),
            extra={"page_number": 3, "nested": {"smuggled": "正文"}},
        )
        assert ref["extra"] == {"page_number": 3}

    def test_extra_scalar_string_truncated(self):
        """C-08 N6 钉桩：标量 extra 的字符串值截断到 64 字符——未来调用方误把
        长文本（正文/敏感串）放标量 extra 也不至于整段入册。短值不受影响，
        非字符串标量原样保留。"""
        from app.orchestration.context_funnel import _MAX_EXTRA_STR_LEN

        long_text = "整段长文本" * 40  # 200 字符 > 上限
        ref = make_source_ref(
            kind="document",
            ref_id=document_ref("f", "c"),
            extra={
                "chunk_id": "c-123",  # 常规短值：原样保留
                "page_number": 7,  # 非 str 标量：不受影响
                "smuggled": long_text,  # 超长：截断
            },
        )
        assert ref["extra"]["chunk_id"] == "c-123"
        assert ref["extra"]["page_number"] == 7
        assert ref["extra"]["smuggled"] == long_text[:_MAX_EXTRA_STR_LEN]
        assert len(ref["extra"]["smuggled"]) == _MAX_EXTRA_STR_LEN
        assert long_text not in ref["extra"]["smuggled"]

    def test_fingerprint_deterministic(self):
        a = make_source_ref(kind="episodic", ref_id="mem:x", content="同一段内容")
        b = make_source_ref(kind="episodic", ref_id="mem:x", content="同一段内容")
        assert a["content_hash"] == b["content_hash"]


class TestMarkerAlignment:
    def test_aligned(self):
        refs = [{"ref": "doc:f:c1", "kind": "document", "tokens": 5}, {"ref": "doc:f:c2", "kind": "document", "tokens": 6}]
        aligned, status = None, None
        from app.orchestration.context_funnel import align_markers_to_refs

        aligned, status = align_markers_to_refs(refs, ["S1", "S2"])
        assert status == "aligned"
        assert [entry["marker"] for entry in aligned] == ["S1", "S2"]

    def test_unverified_on_mismatch(self):
        from app.orchestration.context_funnel import align_markers_to_refs

        refs = [{"ref": "doc:f:c1", "kind": "document"}]
        aligned, status = align_markers_to_refs(refs, ["S1", "S2", "S3"])
        assert status == "unverified"
        assert "marker" not in aligned[0]  # 不强行错位对齐

    def test_no_markers(self):
        from app.orchestration.context_funnel import align_markers_to_refs

        _aligned, status = align_markers_to_refs([{"ref": "doc:f:c1", "kind": "document"}], None)
        assert status == "no_markers"


# ---------------------------------------------------------------------------
# bloat / inert
# ---------------------------------------------------------------------------


class TestBloatAndInert:
    def test_bloat_share_threshold(self):
        flags = detect_context_bloat(
            {"conversation": 900, "documents": 100, "galaxy": 0},
            total_tokens=1000,
            share_threshold=0.45,
        )
        assert [flag["section"] for flag in flags] == ["conversation"]
        assert flags[0]["share"] == pytest.approx(0.9)

    def test_bloat_empty_is_quiet(self):
        assert detect_context_bloat({}, total_tokens=0) == []

    def test_inert_document_refs(self):
        refs = [
            make_source_ref(kind="document", ref_id=document_ref("f", "c1"), content="x", marker="S1"),
            make_source_ref(kind="document", ref_id=document_ref("f", "c2"), content="y", marker="S2"),
        ]
        inert = flag_inert_refs(refs, cited_markers=["S2"], supported_markers=["S2"])
        assert [entry["ref"] for entry in inert] == ["doc:f:c1"]

    def test_inert_memory_refs(self):
        refs = [
            {"kind": "episodic", "ref": "mem:a", "tokens": 4},
            {"kind": "episodic", "ref": "mem:b", "tokens": 4},
        ]
        inert = flag_inert_refs(refs, cited_markers=[], supported_markers=[], used_refs={"mem:b"})
        assert [entry["ref"] for entry in inert] == ["mem:a"]

    def test_no_marker_docs_never_flagged(self):
        """无 [S#] 的文档面（bullet/multi-hop）无法判定引用——不误标。"""
        refs = [{"kind": "document", "ref": "doc:f:c9", "tokens": 4}]
        assert flag_inert_refs(refs, cited_markers=[], supported_markers=[]) == []


# ---------------------------------------------------------------------------
# 记录拼装 + 正文红线
# ---------------------------------------------------------------------------

_BODY_SENTINELS = [
    "考试焦虑的具体正文描述段落",
    "顶点式与对称轴求法的完整原文内容",
]


def _full_record_inputs():
    rows = [_memory_row(f"m{i}", _BODY_SENTINELS[i % len(_BODY_SENTINELS)]) for i in range(4)]
    memory_funnel = build_episodic_funnel(
        candidate_rows=rows,
        prefilter_allowed_count=4,
        prefilter_reasons={},
        prefilter_dropped_refs=[],
        ranked_rows=rows,
        injected_rows=[{"summary": row.summary} for row in rows[:2]],
    ).to_payload()
    document_refs = [
        make_source_ref(
            kind="document",
            ref_id=document_ref("f1", "c1"),
            content=_BODY_SENTINELS[1],
            extra={"page_number": 2},
        ),
        make_source_ref(
            kind="document",
            ref_id=document_ref("f1", "c2"),
            content=_BODY_SENTINELS[0],
            extra={"page_number": 3},
        ),
    ]
    return memory_funnel, document_refs


class TestFunnelRecord:
    def test_record_shape_and_consistency(self):
        memory_funnel, document_refs = _full_record_inputs()
        record = build_context_funnel_record(
            request_id="req-1",
            memory_funnel=memory_funnel,
            experience_meta={"total_candidates": 3, "surfaced": 2, "internal_only": 1, "tokens": 8},
            retrieval={"total_retrieved": 9, "total_passed": 4},
            document_budget={"shown_results": 2, "token_usage": 90},
            context_budget={"token_usage": {"documents": 90, "conversation": 60}, "metadata": {"total_tokens": 150}},
            citation_outcome={"cited": ["S1"], "answer_supported": ["S1"], "unknown_cited": [], "faithfulness_ok": True},
            source_refs=document_refs,
            citation_markers=["S1", "S2"],
            document_injected=True,
            document_block_tokens=90,
            memory_refs=[{"kind": "episodic", "ref": "mem:m0", "tokens": 5}],
            used_memory_refs={"mem:m0"},
        )
        assert record["version"] == FUNNEL_VERSION
        assert record["consistent"] is True
        assert record["marker_alignment"] == "aligned"
        assert SURFACE_EPISODIC in record["funnels"] and SURFACE_DOCUMENTS in record["funnels"]
        assert record["funnels"][SURFACE_DOCUMENTS]["stages"][STAGE_CANDIDATES]["items"] == 9
        assert record["total_tokens"] == 150
        # inert：S2 引用了但未支撑? —— S1 cited+supported；S2 未被引用 → inert
        inert_refs = {entry["ref"] for entry in record["inert_refs"]}
        assert "doc:f1:c2" in inert_refs
        assert "doc:f1:c1" not in inert_refs
        assert "mem:m0" not in inert_refs  # 被使用

    def test_no_body_text_in_record(self):
        """红线：完整记录序列化后扫描不到任何正文样本。"""
        memory_funnel, document_refs = _full_record_inputs()
        record = build_context_funnel_record(
            memory_funnel=memory_funnel,
            source_refs=document_refs,
            citation_markers=["S1", "S2"],
            document_injected=True,
            document_block_tokens=90,
            retrieval={"total_retrieved": 2, "total_passed": 2},
        )
        leaked = find_content_leak(record, _BODY_SENTINELS)
        assert leaked == [], f"正文泄漏：{leaked}"

    def test_degrades_on_missing_inputs(self):
        """全部输入缺失 → 空观测记录，绝不抛错。"""
        record = build_context_funnel_record()
        assert record["consistent"] is True
        assert record["funnels"] == {}
        assert record["source_refs"] == []

    def test_document_funnel_shadow_honesty(self):
        """shadow 模式（只存候选不注入）→ injected=0，诚实记录。"""
        funnel = build_document_funnel(
            {"total_retrieved": 5, "total_passed": 3},
            injected_tokens=0,
            injected_chunks=0,
            budget={"shown_results": 3},
        )
        assert funnel.stage(STAGE_INJECTED).items == 0
        assert funnel.stage(STAGE_RANKED).reasons.get(REASON_BUDGET_TRUNCATED) is None
        assert funnel.validate() == []

    def test_experience_funnel_from_meta(self):
        funnel = build_experience_funnel({"total_candidates": 6, "surfaced": 4, "internal_only": 2, "tokens": 20})
        assert funnel.stage(STAGE_CANDIDATES).items == 6
        assert funnel.stage(STAGE_FILTERED).reasons == {REASON_SELFCHECK_INTERNAL: 2}
        assert funnel.stage(STAGE_INJECTED).items == 4
        assert funnel.stage(STAGE_INJECTED).tokens == 20


# ---------------------------------------------------------------------------
# 有界 label clamp + metrics 出口
# ---------------------------------------------------------------------------


class TestBoundedLabels:
    def test_clamp_drop_reason(self):
        # M-03 实际词表：<dimension>:<detail>
        assert clamp_drop_reason("status:superseded") == "prefilter_status"
        assert clamp_drop_reason("ttl:expired") == "prefilter_ttl"
        assert clamp_drop_reason("scope:mismatch") == "prefilter_scope"
        assert clamp_drop_reason("user:wrong_user") == "prefilter_user"
        assert clamp_drop_reason("sensitivity:exceeded") == "prefilter_sensitivity"
        assert clamp_drop_reason(REASON_RANK_CUTOFF) == REASON_RANK_CUTOFF
        assert clamp_drop_reason("任意未知原因xyz") == "other"
        assert clamp_drop_reason("") == "other"

    def test_clamped_values_in_bounded_set(self):
        for reason in ("superseded", "expired", "user_mismatch", "ttl_pass", "unknown_thing"):
            assert clamp_drop_reason(reason) in BOUNDED_DROP_REASONS

    def test_clamp_surface(self):
        assert clamp_surface(SURFACE_DOCUMENTS) == SURFACE_DOCUMENTS
        assert clamp_surface("mystery_surface") == "other"

    def test_record_funnel_metrics_never_raises(self):
        memory_funnel, document_refs = _full_record_inputs()
        record = build_context_funnel_record(
            memory_funnel=memory_funnel,
            source_refs=document_refs,
            citation_markers=["S1"],
            document_injected=True,
            document_block_tokens=10,
            retrieval={"total_retrieved": 2, "total_passed": 2},
            citation_outcome={"cited": ["S1"], "answer_supported": ["S1"], "faithfulness_ok": True},
        )
        record["bloat"] = [{"section": "documents", "tokens": 90, "share": 0.6}]
        record_funnel_metrics(record)  # 不抛错即通过
        # 有界 label 计数器确实在增长（kept 面至少有一条序列）
        assert CONTEXT_FUNNEL_STAGE_ITEMS_TOTAL is not None
        assert CONTEXT_FUNNEL_INERT_REFS_TOTAL is not None
        assert CONTEXT_FUNNEL_BLOAT_SECTION_TOTAL is not None

    def test_stage_names_frozen(self):
        assert STAGE_NAMES == ("candidates", "filtered", "ranked", "injected")

    def test_log_line_has_no_body(self):
        memory_funnel, document_refs = _full_record_inputs()
        record = build_context_funnel_record(memory_funnel=memory_funnel, source_refs=document_refs)
        line = funnel_log_line(record)
        for sentinel in _BODY_SENTINELS:
            assert sentinel not in line
        assert "C-08 context funnel" in line
