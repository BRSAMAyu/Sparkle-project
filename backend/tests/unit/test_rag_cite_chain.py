"""RAG 引用链回归（mr4 断点验收）。

链路：use_document_context=True → retrieval_intent 决策必须检索 →
GraphRAG 水合把 chunk 内容注入 document_context（prompt 材料）→
retrieval_node 产出 CitationBlock（citation 通道）。

回归背景：用户消息「MRV-7749 是什么？请根据我上传的资料回答」在
use_document_context=True 时仍被判为 no_document_retrieval_signal，
导致检索从未执行、prompt 无材料、回复声称没看到资料。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

import app.agents.standard_workflow as standard_workflow_module
import app.orchestration.orchestrator as orchestrator_module
from app.agents.standard_workflow import retrieval_node
from app.orchestration.graph_rag import GraphRAGResult
from app.orchestration.retrieval_intent import build_retrieval_decision
from app.orchestration.statechart_engine import WorkflowState

USER_ID = "b9a9e0a0-2956-47de-86dc-002ee8b835ad"
FILE_ID = "393a89d5-8356-4db0-a973-4a29a7019fc9"
CHUNK_ID = "chunk-mrv-7749-0"
CHUNK_CONTENT = (
    "MRV-7749 实验记录：样品在零下 196 摄氏度的液氮环境中表现出明显的磷光，" "升温后磷光淬灭并转为荧光发射。"
)
MESSAGE = "MRV-7749 是什么？请根据我上传的资料回答"


def _vector_item() -> dict[str, Any]:
    return {
        "name": "实验记录.md",
        "file_name": "实验记录.md",
        "description": CHUNK_CONTENT,
        "similarity": 0.86,
        "page_numbers": [3],
        "chunk_id": CHUNK_ID,
        "source_file_id": FILE_ID,
        "chunk": {
            "id": CHUNK_ID,
            "file_id": FILE_ID,
            "chunk_index": 0,
            "content": CHUNK_CONTENT,
            "section_title": "低温发光",
        },
    }


def _rag_result() -> GraphRAGResult:
    return GraphRAGResult(
        query=MESSAGE,
        entities=["MRV-7749"],
        vector_results=[_vector_item()],
        graph_results=[],
        fused_context="",
        metadata={},
    )


def _patch_rag_stack(monkeypatch: pytest.MonkeyPatch, module: Any, retriever_result: Any) -> None:
    class _FakeKillSwitch:
        async def get_mode(self) -> str:
            return "live"

    class _FakeKnowledgeService:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        async def retrieve_context(self, **_kwargs: Any) -> str:
            return ""

        async def get_knowledge_version(self) -> str:
            return "v-test"

    class _FakeRetriever:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.retrieve = AsyncMock(return_value=retriever_result)

    monkeypatch.setattr(module, "AuroraDocContextKillSwitchService", _FakeKillSwitch)
    monkeypatch.setattr(module, "KnowledgeService", _FakeKnowledgeService)
    monkeypatch.setattr(module, "GraphRAGRetriever", _FakeRetriever)


# ---------------------------------------------------------------------------
# 1. 决策段：use_document_context=True 必须强制检索
# ---------------------------------------------------------------------------


def test_use_document_context_true_forces_retrieval_for_unknown_keyword() -> None:
    decision = build_retrieval_decision(
        message=MESSAGE,
        route_intent="chat",
        context={"use_document_context": True},
    )

    assert decision.should_retrieve is True
    assert decision.retrieval_mode == "targeted_source_rag"
    assert decision.citation_required is True


def test_use_document_context_false_still_blocks_retrieval() -> None:
    decision = build_retrieval_decision(
        message=MESSAGE,
        route_intent="chat",
        context={"use_document_context": False},
    )

    assert decision.should_retrieve is False
    assert decision.reason == "session_use_document_context_false"


def test_use_document_context_true_keeps_emotional_guard() -> None:
    decision = build_retrieval_decision(
        message="我今天压力好大，有点崩溃",
        route_intent="chat",
        context={"use_document_context": True},
    )

    assert decision.should_retrieve is False
    assert decision.reason == "emotional_or_social_turn"


def test_document_chunk_parent_id_fills_missing_source_file_id() -> None:
    """Redis 密集检索不投影 file_id 字段（索引 schema 缺口），
    document_chunk 条目必须能从 parent_id（= file_id 契约）恢复引用来源。"""
    from app.orchestration.graph_rag import filter_graph_rag_result

    redis_shaped_item = {
        "id": f"sparkle:doc_chunk:{FILE_ID}:0",
        "name": "mrv-7749_note.txt",
        "file_name": "mrv-7749_note.txt",
        "description": CHUNK_CONTENT,
        "similarity": 0.86,
        "source_type": "document_chunk",
        "parent_id": FILE_ID,  # 索引契约：document_chunk 的 parent_id 即 file_id
        "chunk_index": 0,
        "page_numbers": [1],
    }

    filtered = filter_graph_rag_result(
        GraphRAGResult(
            query=MESSAGE,
            entities=[],
            vector_results=[redis_shaped_item],
            graph_results=[],
            fused_context="",
            metadata={},
        )
    )

    assert filtered.total_passed == 1
    chunk = filtered.chunks[0]
    assert chunk.source_file_id == FILE_ID
    assert "MRV-7749" in chunk.content


# ---------------------------------------------------------------------------
# 2. 水合段：决策检索后，chunk 内容必须进入 document_context（prompt 材料）
# ---------------------------------------------------------------------------


async def test_hydrate_document_context_injects_chunk_content(monkeypatch: pytest.MonkeyPatch) -> None:
    decision = build_retrieval_decision(
        message=MESSAGE,
        route_intent="chat",
        context={"use_document_context": True},
    )
    state = WorkflowState()
    state.context_data["use_document_context"] = True
    state.context_data["document_retrieval_decision"] = decision.to_dict()
    state.context_data["retrieval_decision"] = decision.to_dict()

    _patch_rag_stack(monkeypatch, orchestrator_module, _rag_result())

    payload = await orchestrator_module.ChatOrchestrator._hydrate_document_context(
        SimpleNamespace(),  # decision 已预置，不会触碰 self 的其他成员
        active_db=object(),
        user_id=USER_ID,
        user_message=MESSAGE,
        route_intent="chat",
        user_context_payload={"use_document_context": True},
        state=state,
    )

    document_context = str(state.context_data.get("document_context") or "")
    assert "MRV-7749" in document_context
    assert "磷光" in document_context
    assert "零下" in document_context
    assert "No relevant study materials" not in document_context

    retrieval_meta = state.context_data.get("document_context_retrieval") or {}
    assert retrieval_meta.get("total_passed") == 1
    receipt = retrieval_meta.get("context_receipt") or {}
    used = receipt.get("used") or []
    assert used and used[0].get("chunk_id") == CHUNK_ID
    assert used[0].get("source_file_id") == FILE_ID
    assert payload is not None and payload.get("document_context") == document_context


async def test_context_receipt_tolerates_chunks_without_filename(monkeypatch: pytest.MonkeyPatch) -> None:
    """V3-FIX-253 行内缺陷（wt538）：FilteredChunk.filename 是 str|None，
    chunk 无 filename（如 Redis 密集检索未投影 file_name）时 context_receipt
    的 sorted() 混排 None/str 即 TypeError，整个文档水合被 except 吞掉。"""
    decision = build_retrieval_decision(
        message=MESSAGE,
        route_intent="chat",
        context={"use_document_context": True},
    )
    state = WorkflowState()
    state.context_data["use_document_context"] = True
    state.context_data["document_retrieval_decision"] = decision.to_dict()
    state.context_data["retrieval_decision"] = decision.to_dict()

    unnamed = {
        # 无 file_name/filename 键 → FilteredChunk.filename 为 None
        "name": "节点描述 chunk",
        "description": CHUNK_CONTENT,
        "similarity": 0.75,
        "chunk_id": "chunk-mrv-7749-1",
        "chunk": {"id": "chunk-mrv-7749-1", "chunk_index": 1, "content": CHUNK_CONTENT},
    }
    rag_result = GraphRAGResult(
        query=MESSAGE,
        entities=["MRV-7749"],
        vector_results=[_vector_item(), unnamed],
        graph_results=[],
        fused_context="",
        metadata={},
    )
    _patch_rag_stack(monkeypatch, orchestrator_module, rag_result)

    payload = await orchestrator_module.ChatOrchestrator._hydrate_document_context(
        SimpleNamespace(),
        active_db=object(),
        user_id=USER_ID,
        user_message=MESSAGE,
        route_intent="chat",
        user_context_payload={"use_document_context": True},
        state=state,
    )

    retrieval_meta = state.context_data.get("document_context_retrieval") or {}
    receipt = retrieval_meta.get("context_receipt") or {}
    used_names = receipt.get("used_names") or []
    assert "实验记录.md" in used_names
    assert None not in used_names
    assert None not in (receipt.get("excluded_names") or [])
    assert "MRV-7749" in str(payload.get("document_context") or "")


# ---------------------------------------------------------------------------
# 3. 引用段：retrieval_node 必须产出携带 chunk 内容的 CitationBlock
# ---------------------------------------------------------------------------


async def test_retrieval_node_emits_citations_with_chunk_content(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_rag_stack(monkeypatch, standard_workflow_module, _rag_result())

    async def _no_capture(**_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(
        standard_workflow_module.document_service, "capture_implicit_feedback_from_message", AsyncMock()
    )
    monkeypatch.setattr(standard_workflow_module.document_service, "register_turn_citations", AsyncMock())

    captured: list[Any] = []

    async def _stream_callback(response: Any) -> None:
        captured.append(response)

    state = WorkflowState()
    state.messages = [{"role": "user", "content": MESSAGE}]
    state.context_data.update(
        {
            "db_session": object(),
            "user_id": USER_ID,
            "session_id": "sess-mrv",
            "include_references": True,
            "stream_callback": _stream_callback,
            "document_retrieval_decision": {"should_retrieve": True, "retrieval_mode": "targeted_source_rag"},
        }
    )

    result = await retrieval_node(state)

    assert str(result.context_data.get("document_context") or "").find("MRV-7749") >= 0
    assert captured, "retrieval_node should stream a CitationBlock when include_references=True"
    citation_block = captured[0].citations
    assert citation_block.citations, "CitationBlock must carry citations"
    first = citation_block.citations[0]
    assert "磷光" in first.content or "MRV-7749" in first.content
    assert first.file_id == FILE_ID
    assert first.source_type == "document"
