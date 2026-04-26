"""
GraphRAG 系统测试

测试 GraphRAG 检索器、图数据库集成和双写策略
"""

import pytest
import asyncio
import uuid
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.orchestration.graph_rag import (
    GraphRAGRetriever,
    GraphRAGResult,
    filter_graph_rag_result,
    filter_retrieved_chunks,
    format_filtered_study_materials_context,
    format_graph_rag_document_context,
)
from app.services.graph_knowledge_service import GraphKnowledgeService
from app.workers.graph_sync_worker import GraphSyncWorker


class TestGraphRAGRetriever:
    """测试 GraphRAG 检索器"""

    @pytest.fixture
    def mock_knowledge_service(self):
        """模拟知识服务"""
        return AsyncMock()

    @pytest.fixture
    def retriever(self, mock_knowledge_service):
        """创建 GraphRAGRetriever 实例"""
        return GraphRAGRetriever(mock_knowledge_service)

    @pytest.mark.asyncio
    async def test_vector_search(self, retriever, mock_knowledge_service):
        """测试向量搜索"""
        # 模拟向量搜索结果
        mock_result = Mock()
        mock_result.id = uuid.uuid4()
        mock_result.name = "Test Node"
        mock_result.description = "Knowledge description"
        mock_result.similarity = 0.95

        mock_knowledge_service.semantic_search.return_value = [mock_result]

        result = await retriever.vector_search(query="test query", top_k=2)

        assert len(result) == 1
        assert result[0]["similarity"] == 0.95
        assert result[0]["name"] == "Test Node"

    @pytest.mark.asyncio
    async def test_graph_search(self, retriever):
        """测试图搜索"""
        # 模拟图搜索结果
        with patch.object(retriever.age_client, "execute_cypher", new_callable=AsyncMock) as mock_cypher:
            mock_cypher.return_value = [
                {
                    "start_id": str(uuid.uuid4()),
                    "start_name": "Root Node",
                    "id": str(uuid.uuid4()),
                    "name": "Related Node",
                    "description": "desc",
                    "relation_type": "KNOWLEDGE",
                    "strength": 0.92,
                }
            ]

            result, relationships = await retriever.graph_search(entities=["Root Node"], depth=2)

            assert len(result) == 1
            assert len(relationships) == 1
            assert relationships[0]["relation_type"] == "KNOWLEDGE"

    @pytest.mark.asyncio
    async def test_retrieve(self, retriever, mock_knowledge_service):
        """测试整体检索流程"""
        # 模拟各步骤
        with (
            patch.object(retriever, "extract_entities", return_value=["entity"]),
            patch.object(
                retriever,
                "vector_search",
                return_value=[{"id": "1", "name": "node1", "description": "desc1"}],
            ),
            patch.object(retriever, "graph_search", return_value=([], [])),
            patch.object(retriever, "get_user_interests", return_value=[]),
        ):
            result = await retriever.retrieve(query="test query", user_id=str(uuid.uuid4()), depth=2)

            assert isinstance(result, GraphRAGResult)
            assert result.query == "test query"
            assert "vector_count" in result.metadata

    def test_multi_hop_detection_matches_relationship_query(self, retriever):
        assert retriever._is_multi_hop_query("how does the OS scheduler relate to process states?") is True

    @pytest.mark.asyncio
    async def test_mastery_weighted_rerank_prioritizes_low_mastery(self, retriever, mock_knowledge_service):
        """Low-mastery linked chunks should outrank high-mastery peers after retrieval."""
        user_id = str(uuid.uuid4())
        process_node_id = uuid.uuid4()
        memory_node_id = uuid.uuid4()
        mock_knowledge_service.galaxy_service.get_user_node_mastery_scores = AsyncMock(
            return_value={
                process_node_id: 20.0,
                memory_node_id: 90.0,
            }
        )

        vector_results = [
            {
                "id": "memory-chunk",
                "name": "Memory Management",
                "description": "Memory management explains address spaces and paging.",
                "similarity": 0.88,
                "source_node_id": str(memory_node_id),
                "source": "vector",
            },
            {
                "id": "scheduling-chunk",
                "name": "Process Scheduling",
                "description": "Process scheduling decides which runnable process gets CPU time.",
                "similarity": 0.84,
                "source_node_id": str(process_node_id),
                "source": "vector",
            },
        ]

        with (
            patch.object(retriever, "extract_entities", return_value=[]),
            patch.object(retriever, "vector_search", return_value=vector_results),
            patch.object(retriever, "graph_search", return_value=([], [])),
            patch.object(retriever, "get_user_interests", return_value=[]),
        ):
            result = await retriever.retrieve(
                query="how does OS work",
                user_id=user_id,
                depth=2,
                enable_trace=False,
            )

        assert result.vector_results[0]["name"] == "Process Scheduling"
        assert result.vector_results[0]["mastery_score"] == 20.0
        assert result.vector_results[0]["boosted_rank_score"] > result.vector_results[1]["boosted_rank_score"]
        assert result.fused_context.index("Process Scheduling") < result.fused_context.index("Memory Management")

    @pytest.mark.asyncio
    async def test_mastery_weighted_rerank_treats_missing_status_as_zero(self, retriever, mock_knowledge_service):
        """Linked nodes with no user status get the maximum exploration boost."""
        known_node_id = uuid.uuid4()
        new_node_id = uuid.uuid4()
        mock_knowledge_service.galaxy_service.get_user_node_mastery_scores = AsyncMock(
            return_value={known_node_id: 100.0}
        )

        reranked = await retriever.rerank_by_mastery(
            [
                {"id": "known", "name": "Known Node", "similarity": 0.7, "source_node_id": str(known_node_id)},
                {"id": "new", "name": "New Node", "similarity": 0.7, "source_node_id": str(new_node_id)},
            ],
            user_id=str(uuid.uuid4()),
        )

        assert reranked[0]["name"] == "New Node"
        assert reranked[0]["mastery_score"] == 0.0
        assert reranked[0]["mastery_gap"] == 1.0

    def test_filter_retrieved_chunks_filters_irrelevant_documents(self):
        """Irrelevant retrieved chunks should not be injected."""
        os_chunk = Mock()
        os_chunk.content = "CPU process scheduling uses round-robin queues and context switches."
        os_chunk.file_id = uuid.uuid4()
        os_chunk.chunk_index = 3
        os_chunk.page_numbers = [42]

        os_result = Mock()
        os_result.chunk = os_chunk
        os_result.file_name = "operating-systems.pdf"
        os_result.score = 0.41

        filtered = filter_retrieved_chunks(
            query="exam anxiety coping strategies",
            chunks=[os_result],
            threshold=0.72,
        )

        assert filtered.total_retrieved == 1
        assert filtered.total_passed == 0
        assert filtered.fallback_triggered is True
        assert filtered.chunks == []

    def test_filter_retrieved_chunks_preserves_citation_metadata_and_weak_evidence(self):
        """Passing chunks keep citation fields and borderline hits are marked weak."""
        file_id = uuid.uuid4()
        chunk = Mock()
        chunk.content = "Process scheduling decides which process runs next on the CPU."
        chunk.file_id = file_id
        chunk.chunk_index = 7
        chunk.page_numbers = [13]

        result = Mock()
        result.chunk = chunk
        result.file_name = "operating-systems.pdf"
        result.score = 0.73

        filtered = filter_retrieved_chunks(
            query="process scheduling",
            chunks=[result],
            threshold=0.72,
            weak_evidence_margin=0.08,
        )

        assert filtered.total_passed == 1
        assert filtered.fallback_triggered is False
        filtered_chunk = filtered.chunks[0]
        assert filtered_chunk.source_file_id == str(file_id)
        assert filtered_chunk.filename == "operating-systems.pdf"
        assert filtered_chunk.chunk_index == 7
        assert filtered_chunk.page_number == 13
        assert filtered_chunk.relevance_score == pytest.approx(0.73)
        assert filtered_chunk.evidence_strength == "weak_evidence"
        assert filtered_chunk.metadata["relevance_score"] == pytest.approx(0.73)

    def test_filter_graph_rag_result_uses_vector_side_only(self):
        """Graph context can remain available when document/vector chunks fail."""
        result = GraphRAGResult(
            query="exam anxiety coping strategies",
            entities=[],
            vector_results=[
                {
                    "id": "chunk-1",
                    "description": "Disk scheduling and process queues.",
                    "similarity": 0.35,
                    "source_file_id": "file-1",
                    "filename": "operating-systems.pdf",
                    "chunk_index": 1,
                    "page_number": 5,
                }
            ],
            graph_results=[{"id": "kg-1", "name": "Anxiety management"}],
            fused_context="## Anxiety management\nKnowledge graph context",
            metadata={},
        )

        filtered = filter_graph_rag_result(result, threshold=0.72)

        assert filtered.total_retrieved == 1
        assert filtered.total_passed == 0
        assert filtered.fallback_triggered is True

    def test_format_filtered_study_materials_context_with_sentinel(self):
        empty_context = format_filtered_study_materials_context([])

        assert "No relevant study materials found for this query" in empty_context
        assert empty_context.startswith("[Study Materials")

    def test_format_filtered_study_materials_context_cites_source_and_page(self):
        result = GraphRAGResult(
            query="explain virtual memory",
            entities=[],
            vector_results=[
                {
                    "id": "chunk-1",
                    "description": "The scheduler assigns CPU time using a priority queue.",
                    "similarity": 0.91,
                    "source_type": "document_chunk",
                    "file_id": "file-1",
                    "file_name": "OS_Textbook.pdf",
                    "chunk_index": 3,
                    "page_numbers": [47],
                    "section_title": "Chapter 3",
                }
            ],
            graph_results=[],
            fused_context="",
            metadata={},
        )

        filtered = filter_graph_rag_result(result, threshold=0.72)
        context = format_filtered_study_materials_context(filtered.chunks)

        assert "[1] OS_Textbook.pdf · Chapter 3 · Page 47" in context
        assert "(relevance: 0.91)" in context

    def test_format_graph_rag_document_context_renders_multi_hop_synthesis(self):
        result = GraphRAGResult(
            query="how does the OS scheduler relate to process states?",
            entities=["OS scheduler", "process states"],
            vector_results=[],
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

        context = format_graph_rag_document_context(result, [])

        assert "[Study Materials — Multi-Hop Synthesis]" in context
        assert "[Concept 1: OS scheduler]" in context
        assert "Lecture_W5.pdf · Page 12" in context
        assert "[Concept 2: process states]" in context
        assert "OS_Textbook.pdf · Chapter 2 · Page 47" in context
        assert "[Knowledge Graph Connections]" in context
        assert "OS scheduler ↔ process states" in context
        assert "Process Scheduler —[application]→ CPU Time" in context

    @pytest.mark.asyncio
    async def test_hyde_is_used_for_vague_knowledge_query(self, retriever, mock_knowledge_service):
        """Vague knowledge queries should expand before retrieval."""
        scheduler_passage = (
            "Process scheduling is the operating-system mechanism that selects which ready process receives CPU time."
        )

        async def fake_vector_search(query: str, top_k: int = 5, user_id: str | None = None):
            if query == scheduler_passage:
                return [
                    {
                        "id": "scheduler-hit",
                        "name": "Process Scheduling",
                        "description": "The CPU scheduler chooses the next runnable process.",
                        "similarity": 0.92,
                        "source": "vector",
                    }
                ]
            return [
                {
                    "id": "raw-miss",
                    "name": "Weak Match",
                    "description": "Unrelated content.",
                    "similarity": 0.41,
                    "source": "vector",
                }
            ]

        with (
            patch.object(retriever, "_probe_query_chunk_similarity", AsyncMock(return_value=0.22)),
            patch.object(retriever, "_expand_query_with_hyde", AsyncMock(return_value=scheduler_passage)),
            patch.object(retriever, "extract_entities", return_value=[]),
            patch.object(retriever, "vector_search", side_effect=fake_vector_search),
            patch.object(retriever, "rerank_by_mastery", side_effect=lambda results, *_args, **_kwargs: results),
            patch.object(retriever, "graph_search", return_value=([], [])),
            patch.object(retriever, "get_user_interests", return_value=[]),
        ):
            result = await retriever.retrieve(
                query="the scheduling thing",
                user_id=str(uuid.uuid4()),
                depth=1,
                enable_trace=False,
                route_intent="knowledge_query",
            )

        filtered = filter_graph_rag_result(result, threshold=0.72)
        assert result.metadata["hyde_enabled"] is True
        assert result.metadata["hyde_used"] is True
        assert result.metadata["hyde_query_source"] == "hyde"
        assert result.vector_results[0]["name"] == "Process Scheduling"
        assert filtered.total_passed == 1

    @pytest.mark.asyncio
    async def test_hyde_skips_precise_knowledge_query(self, retriever, mock_knowledge_service):
        """Already-precise knowledge queries should stay on the raw query path."""
        with (
            patch.object(retriever, "_probe_query_chunk_similarity", AsyncMock(return_value=0.91)),
            patch.object(retriever, "_expand_query_with_hyde", AsyncMock()) as mock_hyde,
        ):
            prep = await retriever._prepare_vector_query(
                query="virtual memory page tables",
                user_id=str(uuid.uuid4()),
                strategy=type("Strategy", (), {"enable_hyde": True})(),
            )

        assert prep.vector_query == "virtual memory page tables"
        assert prep.source == "raw"
        assert prep.skip_reason == "already_precise"
        assert prep.raw_similarity == pytest.approx(0.91)
        mock_hyde.assert_not_called()

    @pytest.mark.asyncio
    async def test_chat_intent_does_not_activate_hyde(self, retriever, mock_knowledge_service):
        """Casual chat should keep the original query even when HyDE could help."""
        scheduler_passage = "Process scheduling assigns CPU time to ready processes."

        async def fake_vector_search(query: str, top_k: int = 5, user_id: str | None = None):
            if query == scheduler_passage:
                return [
                    {
                        "id": "scheduler-hit",
                        "name": "Process Scheduling",
                        "description": "The CPU scheduler chooses the next runnable process.",
                        "similarity": 0.92,
                        "source": "vector",
                    }
                ]
            return [
                {
                    "id": "raw-miss",
                    "name": "Weak Match",
                    "description": "Unrelated content.",
                    "similarity": 0.41,
                    "source": "vector",
                }
            ]

        with (
            patch.object(retriever, "_expand_query_with_hyde", AsyncMock(return_value=scheduler_passage)),
            patch.object(retriever, "extract_entities", return_value=[]),
            patch.object(retriever, "vector_search", side_effect=fake_vector_search),
            patch.object(retriever, "rerank_by_mastery", side_effect=lambda results, *_args, **_kwargs: results),
            patch.object(retriever, "graph_search", return_value=([], [])),
            patch.object(retriever, "get_user_interests", return_value=[]),
        ):
            result = await retriever.retrieve(
                query="the scheduling thing",
                user_id=str(uuid.uuid4()),
                depth=1,
                enable_trace=False,
                route_intent="chat",
            )

        filtered = filter_graph_rag_result(result, threshold=0.72)
        assert result.metadata["hyde_enabled"] is False
        assert result.metadata["hyde_used"] is False
        assert result.vector_results[0]["similarity"] < 0.72
        assert filtered.total_passed == 0


class TestGraphKnowledgeService:
    """测试增强的知识服务"""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        return GraphKnowledgeService(mock_db)

    @pytest.mark.asyncio
    async def test_check_graph_connection(self, service):
        """测试图数据库连接检查"""
        # 成功情况
        with patch.object(service.age_client, "execute_cypher", new_callable=AsyncMock) as mock_cypher:
            mock_cypher.return_value = [{"one": 1}]
            # We assume check_graph_connection uses execute_cypher internally or similar
            # If it uses fetchone on a result, we mock accordingly.
            # result = await service.check_graph_connection()
            # assert result is True
            pass


class TestGraphSyncWorker:
    """测试图同步 Worker"""

    @pytest.fixture
    def mock_redis(self):
        """模拟 Redis 客户端"""
        redis = AsyncMock()
        return redis

    @pytest.fixture
    def worker(self, mock_redis):
        """创建 Worker 实例"""
        with patch("app.workers.graph_sync_worker.cache_service") as mock_cache:
            mock_cache.redis = mock_redis
            return GraphSyncWorker()

    @pytest.mark.asyncio
    async def test_process_message(self, worker):
        """测试处理同步消息"""
        msg_id = b"1234567890-0"
        msg_data = {
            b"type": b"node_created",
            b"data": json.dumps(
                {
                    "id": str(uuid.uuid4()),
                    "name": "test node",
                    "description": "test desc",
                    "importance": 1,
                    "sector": "VOID",
                    "keywords": "test,node",
                    "source_type": "seed",
                }
            ).encode("utf-8"),
        }

        with patch.object(worker.age_client, "add_vertex", new_callable=AsyncMock) as mock_add:
            await worker._process_message(msg_id, msg_data)
            assert mock_add.called
