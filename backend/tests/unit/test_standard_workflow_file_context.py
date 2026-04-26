from types import SimpleNamespace
import uuid

import pytest

from app.agents import standard_workflow
from app.agents.standard_workflow import (
    _first_document_page_number,
    _should_use_slim_standard_context,
)
from app.orchestration.graph_rag import GraphRAGResult
from app.orchestration.statechart_engine import WorkflowState


def test_standard_chat_with_attached_files_keeps_full_context():
    state = WorkflowState(messages=[{"role": "user", "content": "请总结我上传的文件"}])
    state.context_data = {
        "chat_mode": "standard",
        "file_ids": ["file-1"],
    }

    assert _should_use_slim_standard_context(state, "请总结我上传的文件") is False


def test_standard_chat_with_retrieval_decision_keeps_full_context():
    state = WorkflowState(messages=[{"role": "user", "content": "explain virtual memory"}])
    state.context_data = {
        "chat_mode": "standard",
        "document_retrieval_decision": {
            "should_retrieve": True,
            "retrieval_mode": "aggressive",
            "budget_tokens": 2200,
            "reason": "knowledge_query_aggressive",
        },
    }

    assert _should_use_slim_standard_context(state, "explain virtual memory") is False


def test_first_document_page_number_reads_page_numbers_list():
    chunk = SimpleNamespace(page_numbers=[3, 4], page_number=None)

    assert _first_document_page_number(chunk) == 3


@pytest.mark.asyncio
async def test_retrieval_node_injects_graphrag_document_context(monkeypatch):
    user_id = uuid.uuid4()
    group_id = uuid.uuid4()
    state = WorkflowState(messages=[{"role": "user", "content": "explain virtual memory"}])
    state.context_data = {
        "db_session": object(),
        "user_id": str(user_id),
        "group_id": str(group_id),
        "document_retrieval_decision": {
            "should_retrieve": True,
            "retrieval_mode": "aggressive",
            "budget_tokens": 2200,
            "reason": "knowledge_query_aggressive",
        },
    }

    class FakeKnowledgeService:
        def __init__(self, db_session):
            self.db_session = db_session

        async def retrieve_context(self, **kwargs):
            return "knowledge context"

    class FakeRetriever:
        def __init__(self, knowledge_service):
            self.knowledge_service = knowledge_service

        async def retrieve(
            self,
            query,
            user_id,
            depth=2,
            enable_trace=True,
            route_intent=None,
            include_group_documents=False,
            group_ids=None,
        ):
            assert include_group_documents is True
            assert group_ids == [str(group_id)]
            return GraphRAGResult(
                query=query,
                entities=["virtual memory"],
                vector_results=[
                    {
                        "id": "chunk-1",
                        "description": "Virtual memory maps virtual pages to physical frames through page tables.",
                        "similarity": 0.91,
                        "source_type": "document_chunk",
                        "file_id": "file-1",
                        "file_name": "OS_Textbook.pdf",
                        "chunk_index": 7,
                        "page_numbers": [47],
                        "section_title": "Chapter 3",
                    }
                ],
                graph_results=[],
                fused_context="",
                metadata={},
            )

    class FakeDocContextSwitch:
        async def get_mode(self):
            return "live"

    monkeypatch.setattr(standard_workflow, "KnowledgeService", FakeKnowledgeService)
    monkeypatch.setattr(standard_workflow, "GraphRAGRetriever", FakeRetriever)
    monkeypatch.setattr(standard_workflow, "AuroraDocContextKillSwitchService", lambda: FakeDocContextSwitch())

    new_state = await standard_workflow.retrieval_node(state)

    assert "[Study Materials" in new_state.context_data["document_context"]
    assert "OS_Textbook.pdf" in new_state.context_data["document_context"]
    assert "Page 47" in new_state.context_data["document_context"]
    assert new_state.context_data["document_context_retrieval"]["total_passed"] == 1


@pytest.mark.asyncio
async def test_retrieval_node_injects_multi_hop_document_context(monkeypatch):
    user_id = uuid.uuid4()
    state = WorkflowState(messages=[{"role": "user", "content": "how does the OS scheduler relate to process states?"}])
    state.context_data = {
        "db_session": object(),
        "user_id": str(user_id),
        "document_retrieval_decision": {
            "should_retrieve": True,
            "retrieval_mode": "aggressive",
            "budget_tokens": 2200,
            "reason": "knowledge_query_aggressive",
        },
    }

    class FakeKnowledgeService:
        def __init__(self, db_session):
            self.db_session = db_session

        async def retrieve_context(self, **kwargs):
            return "knowledge context"

    class FakeRetriever:
        def __init__(self, knowledge_service):
            self.knowledge_service = knowledge_service

        async def retrieve(
            self,
            query,
            user_id,
            depth=2,
            enable_trace=True,
            route_intent=None,
            include_group_documents=False,
            group_ids=None,
        ):
            return GraphRAGResult(
                query=query,
                entities=["OS scheduler", "process states"],
                vector_results=[
                    {
                        "id": "chunk-1",
                        "description": "Round-robin assigns each process a time quantum before preemption.",
                        "similarity": 0.92,
                        "source_type": "document_chunk",
                        "file_id": "file-1",
                        "file_name": "Lecture_W5.pdf",
                        "chunk_index": 4,
                        "page_numbers": [12],
                        "source_node_id": str(uuid.uuid4()),
                    },
                    {
                        "id": "chunk-2",
                        "description": "A process moves from Running to Ready when its quantum expires.",
                        "similarity": 0.89,
                        "source_type": "document_chunk",
                        "file_id": "file-2",
                        "file_name": "OS_Textbook.pdf",
                        "chunk_index": 2,
                        "page_numbers": [47],
                        "section_title": "Chapter 2",
                        "source_node_id": str(uuid.uuid4()),
                    },
                ],
                graph_results=[],
                fused_context="",
                metadata={
                    "multi_hop": {
                        "concept_blocks": [
                            {
                                "concept": "OS scheduler",
                                "chunks": [
                                    {
                                        "source_name": "Lecture_W5.pdf",
                                        "page_number": 12,
                                        "snippet": "Round-robin assigns each process a time quantum before preemption.",
                                        "relevance_score": 0.92,
                                        "evidence_strength": "strong_evidence",
                                    }
                                ],
                            },
                            {
                                "concept": "process states",
                                "chunks": [
                                    {
                                        "source_name": "OS_Textbook.pdf",
                                        "section_title": "Chapter 2",
                                        "page_number": 47,
                                        "snippet": "A process moves from Running to Ready when its quantum expires.",
                                        "relevance_score": 0.89,
                                        "evidence_strength": "strong_evidence",
                                    }
                                ],
                            },
                        ],
                        "graph_connections": [
                            {
                                "from_concept": "OS scheduler",
                                "to_concept": "process states",
                                "edges": [
                                    {
                                        "source_name": "Process Scheduler",
                                        "relation_type": "application",
                                        "target_name": "CPU Time",
                                    },
                                    {
                                        "source_name": "CPU Time",
                                        "relation_type": "prerequisite",
                                        "target_name": "Process States",
                                    },
                                ],
                            }
                        ],
                    }
                },
            )

    class FakeDocContextSwitch:
        async def get_mode(self):
            return "live"

    monkeypatch.setattr(standard_workflow, "KnowledgeService", FakeKnowledgeService)
    monkeypatch.setattr(standard_workflow, "GraphRAGRetriever", FakeRetriever)
    monkeypatch.setattr(standard_workflow, "AuroraDocContextKillSwitchService", lambda: FakeDocContextSwitch())

    new_state = await standard_workflow.retrieval_node(state)

    assert "[Study Materials — Multi-Hop Synthesis]" in new_state.context_data["document_context"]
    assert "Lecture_W5.pdf" in new_state.context_data["document_context"]
    assert "OS_Textbook.pdf" in new_state.context_data["document_context"]
    assert "[Knowledge Graph Connections]" in new_state.context_data["document_context"]
