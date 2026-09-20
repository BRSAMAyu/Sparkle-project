"""C-04 · RAG citation marker 层与 placement 不变式回归。

覆盖四条验收面：
1. citation 引导与确定性解析（[S#] 标注、答案侧解析、retrieved vs cited vs
   answer-supported 记录）；
2. placement 不变式（材料近邻 user 消息、原始问题保持在末尾、哨兵块不套
   「必须引用」声明）；
3. 「不能靠硬引无关材料刷指标」守卫（幻觉引用 / 标了没用 → faithfulness
   判 False）；
4. 版本/删除/跨用户红线复钉（C-03 硬过滤后材料才可进块、marker 只挂在
   过滤后的材料上；E-05/C-07 版本键既有测试不在此重复）。
"""

from __future__ import annotations

from typing import Any

import pytest

from app.config import settings
from app.core.citation_markers import (
    CITATION_GUIDE,
    NO_MATERIAL_SENTINEL_MARKERS,
    annotate_citation_markers,
    build_citation_outcome,
    extract_material_markers,
    is_no_material_sentinel,
    parse_cited_markers,
)
from app.core.context_pack import ContextBudgetManager
from app.orchestration.graph_rag import (
    NO_RELEVANT_STUDY_MATERIALS_SENTINEL,
    FilteredChunk,
    format_filtered_study_materials_context,
)
from app.services.context_retrieval_pipeline import (
    KnowledgeAccessContext,
    prefilter_knowledge_candidates,
)

STUDY_MATERIALS_BLOCK = """[Study Materials — Referenced Documents]

[1] 实验记录.md · 低温发光 · Page 3
"MRV-7749 实验记录：样品在零下196摄氏度的液氮环境中表现出明显的磷光，升温后磷光淬灭并转为荧光发射。"
(relevance: 0.86)

[2] 光谱讲义.pdf · 荧光量子产率 · Page 12
"荧光量子产率的定义为发射光子数与吸收光子数之比，通常小于等于1。"
(relevance: 0.72)"""


def _filtered_chunk(*, filename: str, content: str, page: int | None = 3) -> FilteredChunk:
    return FilteredChunk(
        raw={"file_name": filename, "parent_name": filename},
        content=content,
        source_file_id=f"file-{filename}",
        chunk_id=f"chunk-{filename}",
        filename=filename,
        chunk_index=0,
        page_number=page,
        relevance_score=0.8,
        cosine_similarity=0.8,
        keyword_overlap=0.1,
        evidence_strength="strong_evidence",
        metadata={},
    )


# ---------------------------------------------------------------------------
# 1. annotate / parse / outcome：确定性解析
# ---------------------------------------------------------------------------


def test_annotate_rewrites_ordinals_and_captures_snippets() -> None:
    annotated, markers = annotate_citation_markers(STUDY_MATERIALS_BLOCK)

    assert markers[0]["marker"] == "S1" and markers[0]["ordinal"] == 1
    assert markers[1]["marker"] == "S2" and markers[1]["ordinal"] == 2
    assert "磷光" in markers[0]["snippet"]
    assert "[S1] 实验记录.md" in annotated
    assert "[S2] 光谱讲义.pdf" in annotated
    assert "[1] " not in annotated and "[2] " not in annotated


def test_annotate_leaves_block_without_ordinals_untouched() -> None:
    multi_hop = '[Study Materials — Multi-Hop Synthesis]\n\n[Concept 1: 光谱]\nLecture_W5.pdf · Page 5\n"片段"'
    annotated, markers = annotate_citation_markers(multi_hop)

    assert annotated == multi_hop
    assert markers == []


def test_parse_cited_markers_all_forms() -> None:
    assert parse_cited_markers("结果见资料[S1]。") == ["S1"]
    assert parse_cited_markers("[S1][S3]两组数据") == ["S1", "S3"]
    assert parse_cited_markers("依据[S1, S3]可知") == ["S1", "S3"]
    assert parse_cited_markers("【S2】里说") == ["S2"]
    assert parse_cited_markers("模型退化形态[2]也认") == ["S2"]
    assert parse_cited_markers("没有引用") == []
    # 干扰组不误报：概念标题、相关度分数、纯文字组
    assert parse_cited_markers("[Concept 1: 光谱] 与 (relevance: 0.86) [Study Materials]") == []


def test_outcome_cited_and_supported_passes_faithfulness() -> None:
    answer = (
        "根据你的实验记录，MRV-7749 样品在零下196摄氏度的液氮环境中表现出明显的磷光[S1]，升温后磷光淬灭并转为荧光发射。"
    )
    outcome = build_citation_outcome(answer, STUDY_MATERIALS_BLOCK)

    assert outcome["retrieved"] == 2
    assert outcome["cited"] == ["S1"]
    assert outcome["unknown_cited"] == []
    assert outcome["answer_supported"] == ["S1"]
    assert outcome["faithfulness_ok"] is True


def test_outcome_cited_but_unsupported_fails_faithfulness() -> None:
    # 标了 [S2] 但答案内容与 S2 snippet（量子产率定义）完全无关——刷指标守卫
    answer = "今天天气不错[S2]，我们去打球吧。"
    outcome = build_citation_outcome(answer, STUDY_MATERIALS_BLOCK)

    assert outcome["cited"] == ["S2"]
    assert outcome["answer_supported"] == []
    assert outcome["support_ratio"]["S2"] < outcome["support_threshold"]
    assert outcome["faithfulness_ok"] is False


def test_outcome_unknown_marker_is_hallucinated_citation() -> None:
    answer = "资料第9条说[S9]……"
    outcome = build_citation_outcome(answer, STUDY_MATERIALS_BLOCK)

    assert outcome["cited"] == []
    assert outcome["unknown_cited"] == ["S9"]
    assert outcome["faithfulness_ok"] is False


def test_outcome_empty_block_counts_any_marker_as_hallucinated() -> None:
    outcome = build_citation_outcome("材料里说[S1]", "")

    assert outcome["retrieved"] == 0
    assert outcome["unknown_cited"] == ["S1"]
    assert outcome["faithfulness_ok"] is False


def test_outcome_no_citation_is_not_unfaithful() -> None:
    outcome = build_citation_outcome("这个问题我直接用通用知识回答。", STUDY_MATERIALS_BLOCK)

    assert outcome["cited"] == []
    assert outcome["unknown_cited"] == []
    assert outcome["faithfulness_ok"] is True


# ---------------------------------------------------------------------------
# 2. placement 不变式（ContextBudgetManager 组装层）
# ---------------------------------------------------------------------------


def _assemble(document_context: str, question: str = "MRV-7749 是什么？请根据我上传的资料回答"):
    manager = ContextBudgetManager(total_token_budget=8000)
    return manager.assemble_prompt(
        base_system_prompt="System shell.",
        user_message=question,
        document_context=document_context,
    )


def test_placement_annotated_block_stays_adjacent_to_user_question() -> None:
    result = _assemble(STUDY_MATERIALS_BLOCK)

    assert result.user_message.startswith("（系统注：本轮已注入你上传的资料原文，回答必须优先引用）\n" + CITATION_GUIDE)
    assert "[S1] 实验记录.md" in result.user_message
    assert result.user_message.endswith("MRV-7749 是什么？请根据我上传的资料回答")
    # 材料仍在 user 消息前缀（不回退到 system prompt 远端）
    assert "[Study Materials" not in result.system_prompt
    assert result.metadata["placement"]["injection_surface"] == "user_message_prefix"
    assert result.metadata["citation_markers"] == ["S1", "S2"]
    assert result.metadata["citation_guided"] is True
    assert result.metadata["no_material_sentinel"] is False
    # document_block 继承面（generation_system_prompt 拼接源）拿到的是带标记的块
    assert "[S1]" in result.document_block


def test_placement_sentinel_block_never_gets_must_cite_note() -> None:
    result = _assemble(NO_RELEVANT_STUDY_MATERIALS_SENTINEL)

    assert "回答必须优先引用" not in result.user_message
    assert CITATION_GUIDE not in result.user_message
    assert "No relevant study materials" in result.user_message
    assert result.metadata["no_material_sentinel"] is True
    assert result.metadata["citation_markers"] == []


def test_placement_no_materials_keeps_question_verbatim() -> None:
    result = _assemble("")

    assert result.user_message == "MRV-7749 是什么？请根据我上传的资料回答"
    assert result.document_block == ""
    assert result.metadata["citation_markers"] == []


def test_sentinel_marker_parity_with_graph_rag_authority() -> None:
    """检测子串必须与 graph_rag 权威哨兵常量保持 parity（防权威漂移）。"""
    for marker in NO_MATERIAL_SENTINEL_MARKERS:
        assert marker in NO_RELEVANT_STUDY_MATERIALS_SENTINEL
    assert is_no_material_sentinel(NO_RELEVANT_STUDY_MATERIALS_SENTINEL) is True
    assert is_no_material_sentinel(STUDY_MATERIALS_BLOCK) is False


# ---------------------------------------------------------------------------
# 3. 版本/删除/跨用户红线复钉（C-03 硬过滤 → 材料块 → marker 单向闸门）
# ---------------------------------------------------------------------------


def _candidate(*, source_type: str = "document_chunk", **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": "chunk-candidate-0",
        "source_type": source_type,
        "content": "跨用户泄漏探针内容 leak-probe-content",
        "chunk_index": 0,
        "page_numbers": [1],
        "lifecycle_status": "active",
    }
    payload.update(fields)
    return payload


def test_cross_user_and_deleted_chunks_never_reach_material_block() -> None:
    ctx = KnowledgeAccessContext(user_id="user-owner", allowed_group_ids=frozenset())
    candidates = [
        _candidate(user_id="user-owner"),
        _candidate(id="chunk-other", user_id="user-other"),  # 跨用户
        _candidate(id="chunk-deleted", user_id="user-owner", lifecycle_status="deleted"),  # 已删除
        _candidate(id="chunk-unattr"),  # 无归属（writer invariant 违例）
    ]

    filtered = prefilter_knowledge_candidates(candidates, ctx)

    reasons = [r.reason for r in filtered.rejections]
    assert reasons.count("knowledge:wrong_user") == 1
    assert reasons.count("knowledge:lifecycle_inactive") == 1
    assert reasons.count("knowledge:unattributed") == 1
    assert filtered.allowed_count == 1

    chunks = [_filtered_chunk(filename="实验记录.md", content="MRV-7749 的自有材料内容") for _ in filtered.allowed]
    block = format_filtered_study_materials_context(chunks)
    annotated, markers = annotate_citation_markers(block)

    assert "跨用户泄漏探针内容" not in annotated
    assert "leak-probe-content" not in annotated
    assert [entry["marker"] for entry in markers] == ["S1"]


def test_marker_budget_never_resurrects_filtered_materials(monkeypatch: pytest.MonkeyPatch) -> None:
    """预算截断砍掉的材料不得以任何 marker 形态回流（marker 与注入块一致）。"""
    monkeypatch.setattr(settings, "CONTEXT_TOTAL_TOKEN_BUDGET", 400, raising=False)
    big_block = format_filtered_study_materials_context(
        [
            _filtered_chunk(
                filename=f"doc{idx}.md",
                content=f"第{idx}份材料内容" + "细节证据 " * 120,
                page=idx,
            )
            for idx in range(1, 6)
        ]
    )
    result = _assemble(big_block)

    annotated_markers = extract_material_markers(result.document_block)
    # 块被预算截断后，答案可引用的 marker 必须与块内实际存在的标记一致，
    # 截断丢弃的片段不允许再被引导文案点名。
    assert all(f"[{entry['marker']}]" in result.document_block for entry in annotated_markers)
    guided_markers = set(result.metadata["citation_markers"])
    block_markers = {entry["marker"] for entry in annotated_markers}
    assert guided_markers == block_markers


# ---------------------------------------------------------------------------
# 4. 与既有链路的形状兼容（graph_rag 两种材料块格式）
# ---------------------------------------------------------------------------


def test_annotate_handles_knowledge_results_block_shape() -> None:
    knowledge_block = '[Knowledge Results]\n\n[1] 光合作用\n"光合作用是植物将光能转化为化学能的过程。"'
    annotated, markers = annotate_citation_markers(knowledge_block)

    assert "[S1] 光合作用" in annotated
    assert markers[0]["snippet"].startswith("光合作用是植物")
    outcome = build_citation_outcome("光合作用是植物将光能转化为化学能的过程[S1]。", annotated)
    assert outcome["faithfulness_ok"] is True
    assert outcome["answer_supported"] == ["S1"]


def test_outcome_support_tokens_chinese_bigrams_discriminate() -> None:
    """重叠判定用 hanzi bigram：常用单字噪声不得让无关答案达标。"""
    snippet = "样品在零下196摄氏度的液氮环境中表现出明显的磷光"
    markers = [{"marker": "S1", "ordinal": 1, "snippet": snippet}]
    answer_with_use = "样品处于液氮环境时呈现磷光，升温后转为荧光。"
    answer_noise = "的的的是是在在了了和和"

    entry = markers[0]
    from app.core.citation_markers import _support_tokens

    snippet_tokens = _support_tokens(entry["snippet"])
    use_ratio = len(snippet_tokens & _support_tokens(answer_with_use)) / len(snippet_tokens)
    noise_ratio = len(snippet_tokens & _support_tokens(answer_noise)) / len(snippet_tokens)
    assert use_ratio > noise_ratio * 3
