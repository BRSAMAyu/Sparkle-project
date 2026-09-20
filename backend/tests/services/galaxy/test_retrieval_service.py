"""
Tests for KnowledgeRetrievalService - hybrid_search and related methods
Using mock-based approach to avoid SQLite/JSONB compatibility issues
"""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.galaxy import NodeWithStatus
from app.services.galaxy.retrieval_service import DocumentChunkResult, KnowledgeRetrievalService


class TestHybridSearchLogic:
    """Tests for hybrid_search method using mocks."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_matches(self):
        """Test that search returns empty list when no matches found."""
        mock_db = AsyncMock()
        service = KnowledgeRetrievalService(mock_db)

        with patch('app.services.galaxy.retrieval_service.semantic_cache_service', None), \
             patch.object(service, '_execute_hybrid_search', new_callable=AsyncMock) as mock_execute:

            mock_execute.return_value = []

            result = await service.hybrid_search(
                user_id=uuid4(),
                query="nonexistent query"
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_respects_limit_parameter(self):
        """Test that search respects the limit parameter."""
        mock_db = AsyncMock()
        service = KnowledgeRetrievalService(mock_db)

        # Create mock results
        mock_results = [
            MagicMock() for _ in range(3)
        ]

        with patch('app.services.galaxy.retrieval_service.semantic_cache_service', None), \
             patch.object(service, '_execute_hybrid_search', new_callable=AsyncMock) as mock_execute:

            mock_execute.return_value = mock_results

            result = await service.hybrid_search(
                user_id=uuid4(),
                query="test query",
                limit=3
            )

            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_uses_semantic_cache_when_available(self):
        """Test that semantic cache is used when available."""
        mock_db = AsyncMock()
        service = KnowledgeRetrievalService(mock_db)

        mock_cache_service = MagicMock()
        mock_cache_service.get_with_lock = AsyncMock(return_value=[])

        with patch('app.services.galaxy.retrieval_service.semantic_cache_service', mock_cache_service), \
             patch.object(service, '_get_knowledge_version', new_callable=AsyncMock) as mock_version:

            mock_version.return_value = "tsms:123456"

            await service.hybrid_search(
                user_id=uuid4(),
                query="test query"
            )

            mock_cache_service.get_with_lock.assert_called_once()
            call_kwargs = mock_cache_service.get_with_lock.call_args.kwargs
            assert call_kwargs["knowledge_version"] == "tsms:123456"
            assert "factory_func" in call_kwargs

    @pytest.mark.asyncio
    async def test_forwards_factory_meta_channel_to_cache(self):
        """E-05 D3：hybrid_search 必须把降级标记通道（factory_meta）传给缓存层，
        否则 factory 无法告知 get_with_lock"本次是降级结果，不要缓存"。"""
        mock_db = AsyncMock()
        service = KnowledgeRetrievalService(mock_db)

        mock_cache_service = MagicMock()
        mock_cache_service.get_with_lock = AsyncMock(return_value=[])

        with patch('app.services.galaxy.retrieval_service.semantic_cache_service', mock_cache_service), \
             patch.object(service, '_get_knowledge_version', new_callable=AsyncMock) as mock_version:

            mock_version.return_value = "tsms:123456"

            await service.hybrid_search(user_id=uuid4(), query="test query")

            call_kwargs = mock_cache_service.get_with_lock.call_args.kwargs
            assert isinstance(call_kwargs.get("factory_meta"), dict)

    @pytest.mark.asyncio
    async def test_execute_hybrid_search_marks_degraded_on_embedding_failure(self, monkeypatch):
        """E-05 D3：embedding 故障降级词法检索时必须置 exec_meta["degraded"]=True
        （缓存层据此拒绝固化降级结果）。"""
        from app.services.galaxy.retrieval_service import embedding_service as emb

        mock_db = AsyncMock()
        service = KnowledgeRetrievalService(mock_db)

        async def _embedding_broken(text, text_type="document"):
            raise RuntimeError("simulated provider outage")

        monkeypatch.setattr(emb, "get_embedding", _embedding_broken)
        # 词法降级路径的 DB 访问会被 _keyword_fallback 内部捕获，返回空即可
        monkeypatch.setattr(service, "keyword_search", AsyncMock(return_value=[]))

        exec_meta: dict = {}
        results = await service._execute_hybrid_search(
            user_id_uuid=uuid4(),
            query_str="test query",
            limit=2,
            use_reranker=False,
            exec_meta=exec_meta,
        )

        assert results == []
        assert exec_meta.get("degraded") is True, "lexical degradation must mark exec_meta for the cache layer"

    @pytest.mark.asyncio
    async def test_execute_hybrid_search_no_degraded_mark_on_success_path(self, monkeypatch):
        """对照：向量侧正常时不标记 degraded（结果可正常缓存）。"""
        from app.config import settings
        from app.services.galaxy.retrieval_service import embedding_service as emb

        mock_db = AsyncMock()
        service = KnowledgeRetrievalService(mock_db)
        monkeypatch.setattr(settings, "ENABLE_REDIS_HYBRID_FALLBACK", False)

        async def _embedding_ok(text, text_type="document"):
            return [0.1] * 1024

        monkeypatch.setattr(emb, "get_embedding", _embedding_ok)
        # 向量与词法两路都空结果 → 直接返回 []，不触发降级标记
        with patch('app.services.galaxy.retrieval_service.redis_search_client') as mock_redis:
            mock_redis.hybrid_search = AsyncMock(return_value=MagicMock(docs=[]))
            mock_redis.search = AsyncMock(return_value=MagicMock(docs=[]))

            exec_meta: dict = {}
            results = await service._execute_hybrid_search(
                user_id_uuid=uuid4(),
                query_str="test query",
                limit=2,
                use_reranker=False,
                exec_meta=exec_meta,
            )

        assert results == []
        assert "degraded" not in exec_meta


class TestSemanticSearchNodes:
    """Tests for semantic_search_nodes method."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_embeddings(self):
        """Test that search returns empty when no nodes have embeddings."""
        mock_db = AsyncMock()
        service = KnowledgeRetrievalService(mock_db)

        # Mock embedding service to return dummy embedding
        with patch('app.services.galaxy.retrieval_service.embedding_service.get_embedding', new_callable=AsyncMock) as mock_embed:

            mock_embed.return_value = [0.1] * 1024

            # Mock db.execute to return empty result
            mock_result = MagicMock()
            mock_result.all.return_value = []
            mock_db.execute = AsyncMock(return_value=mock_result)

            result = await service.semantic_search_nodes(
                query="test",
                limit=5
            )

            assert result == []


class TestKeywordSearch:
    """Tests for keyword_search method."""

    @pytest.mark.asyncio
    async def test_keyword_search_returns_list(self):
        """Test that keyword search returns a list."""
        mock_db = AsyncMock()
        service = KnowledgeRetrievalService(mock_db)

        # Mock db.execute to return empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.keyword_search(
            user_id=uuid4(),
            query="test"
        )

        assert isinstance(result, list)


class TestKnowledgeVersion:
    """Tests for knowledge version computation."""

    @pytest.mark.asyncio
    async def test_compute_knowledge_version_returns_string(self):
        """Test that knowledge version returns a string."""
        mock_db = AsyncMock()
        service = KnowledgeRetrievalService(mock_db)

        # Mock db.execute：max(ts) 为 None、count 为 0（E-05 起版本串含行数）
        mock_result = MagicMock()
        mock_result.one.return_value = (None, 0)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service._compute_knowledge_version()

        # Should return "tsms:0"（空库早退）或带行数的完整版本串
        assert result is not None
        assert result.startswith("tsms:")

    @pytest.mark.asyncio
    async def test_get_knowledge_version_caches_result(self):
        """Test that knowledge version is cached."""
        mock_db = AsyncMock()
        service = KnowledgeRetrievalService(mock_db)

        with patch('app.services.galaxy.retrieval_service.cache_service') as mock_cache:

            mock_cache.redis = MagicMock()
            mock_cache.get = AsyncMock(return_value="tsms:123456")
            mock_cache.set = AsyncMock()

            result = await service._get_knowledge_version()

            mock_cache.get.assert_called_once()
            cache_key = mock_cache.get.call_args[0][0]
            assert "knowledge" in cache_key and "version" in cache_key
            assert result == "tsms:123456"


class TestDocumentVectorSearch:
    """Tests for document_vector_search method."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_file_ids(self):
        """Test returns empty when no file_ids provided."""
        mock_db = AsyncMock()
        service = KnowledgeRetrievalService(mock_db)

        result = await service.document_vector_search(
            user_id=uuid4(),
            query="test",
            file_ids=[]
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_query(self):
        """Test returns empty when no query provided."""
        mock_db = AsyncMock()
        service = KnowledgeRetrievalService(mock_db)

        result = await service.document_vector_search(
            user_id=uuid4(),
            query="",
            file_ids=[uuid4()]
        )

        assert result == []


class TestDocumentChunkResult:
    """Tests for DocumentChunkResult dataclass."""

    def test_document_chunk_result_creation(self):
        """Test DocumentChunkResult can be created with expected fields."""
        from app.models.document_chunks import DocumentChunk

        mock_chunk = MagicMock(spec=DocumentChunk)
        mock_chunk.id = uuid4()
        mock_chunk.content = "Test content"

        result = DocumentChunkResult(
            chunk=mock_chunk,
            file_name="test.pdf",
            score=0.85
        )

        assert result.chunk is mock_chunk
        assert result.file_name == "test.pdf"
        assert result.score == 0.85

    def test_document_chunk_result_dataclass_fields(self):
        """Test DocumentChunkResult has expected fields."""
        # Verify dataclass fields exist
        from dataclasses import fields

        field_names = {f.name for f in fields(DocumentChunkResult)}
        assert 'chunk' in field_names
        assert 'file_name' in field_names
        assert 'score' in field_names


class TestGalaxySchemaMapping:
    def test_node_with_status_preserves_first_unlock_at(self):
        node = MagicMock()
        node.id = uuid4()
        node.parent_id = None
        node.name = "Linear Algebra"
        node.name_en = "Linear Algebra"
        node.description = "Matrices and vector spaces"
        node.importance_level = 4
        node.is_seed = True
        node.global_spark_count = 0
        node.keywords = ["math", "matrix"]
        node.position_x = 120.0
        node.position_y = -48.0
        node.parent = None
        node.subject = MagicMock()
        node.subject.sector_code = "TECH"
        node.subject.position_angle = 35.0
        node.subject.hex_color = "#5AB8CC"
        node.subject.glow_color = "#92E1E9"

        status = MagicMock()
        status.mastery_score = 72.0
        status.total_study_minutes = 180
        status.study_count = 6
        status.is_unlocked = True
        status.is_collapsed = False
        status.is_favorite = False
        status.first_unlock_at = datetime(2026, 3, 20, 9, 30, tzinfo=UTC)
        status.last_study_at = datetime(2026, 3, 24, 21, 0, tzinfo=UTC)
        status.next_review_at = None
        status.decay_paused = False

        mapped = NodeWithStatus.from_models(node, status)

        assert mapped.user_status is not None
        assert mapped.user_status.first_unlock_at == status.first_unlock_at


class TestDocumentHybridSearchExecMeta:
    """FIX-16 ④（E-05 D8）：document_hybrid_search 实际执行模式回填。

    缺陷：工具 payload 的 retrieval_mode 按「key 是否配置」预写 hybrid——
    供应商故障期（key 在、调用败）实际执行的是词法，payload 谎报 hybrid。
    修复：exec_meta 通道回填真实模式，词表封闭。
    """

    def _make_service(self):
        return KnowledgeRetrievalService(AsyncMock())

    @staticmethod
    def _chunk_result():
        from app.models.document_chunks import DocumentChunk

        return DocumentChunkResult(chunk=MagicMock(spec=DocumentChunk), file_name="f.pdf", score=0.8)

    @pytest.mark.asyncio
    async def test_both_sides_ok_reports_hybrid(self):
        service = self._make_service()
        exec_meta: dict = {}
        ok = self._chunk_result()

        with patch.object(service, "document_vector_search", new_callable=AsyncMock, return_value=[ok]), \
             patch.object(service, "document_lexical_search", new_callable=AsyncMock, return_value=[ok]):
            await service.document_hybrid_search(
                user_id=uuid4(), query="entropy", file_ids=[uuid4()], use_reranker=False, exec_meta=exec_meta
            )

        assert exec_meta["retrieval_mode"] == "hybrid_lexical_vector"

    @pytest.mark.asyncio
    async def test_vector_not_configured_reports_lexical_only_disabled(self):
        from app.services.embedding_service import EmbeddingNotConfiguredError

        service = self._make_service()
        exec_meta: dict = {}
        ok = self._chunk_result()

        with patch.object(
            service, "document_vector_search",
            new_callable=AsyncMock, side_effect=EmbeddingNotConfiguredError("no key"),
        ), patch.object(service, "document_lexical_search", new_callable=AsyncMock, return_value=[ok]):
            await service.document_hybrid_search(
                user_id=uuid4(), query="entropy", file_ids=[uuid4()], use_reranker=False, exec_meta=exec_meta
            )

        assert exec_meta["retrieval_mode"] == "lexical_only_embedding_disabled"

    @pytest.mark.asyncio
    async def test_vector_runtime_failure_reports_lexical_degraded(self):
        service = self._make_service()
        exec_meta: dict = {}
        ok = self._chunk_result()

        with patch.object(
            service, "document_vector_search",
            new_callable=AsyncMock, side_effect=RuntimeError("provider 500"),
        ), patch.object(service, "document_lexical_search", new_callable=AsyncMock, return_value=[ok]):
            await service.document_hybrid_search(
                user_id=uuid4(), query="entropy", file_ids=[uuid4()], use_reranker=False, exec_meta=exec_meta
            )

        assert exec_meta["retrieval_mode"] == "lexical_only_vector_degraded"

    @pytest.mark.asyncio
    async def test_lexical_failure_reports_vector_only_degraded(self):
        service = self._make_service()
        exec_meta: dict = {}
        ok = self._chunk_result()

        with patch.object(service, "document_vector_search", new_callable=AsyncMock, return_value=[ok]), \
             patch.object(
                 service, "document_lexical_search",
                 new_callable=AsyncMock, side_effect=RuntimeError("db down"),
             ):
            await service.document_hybrid_search(
                user_id=uuid4(), query="entropy", file_ids=[uuid4()], use_reranker=False, exec_meta=exec_meta
            )

        assert exec_meta["retrieval_mode"] == "vector_only_lexical_degraded"

    @pytest.mark.asyncio
    async def test_both_sides_failed_reports_unavailable_and_empty(self):
        service = self._make_service()
        exec_meta: dict = {}

        with patch.object(
            service, "document_vector_search", new_callable=AsyncMock, side_effect=RuntimeError("x")
        ), patch.object(
            service, "document_lexical_search", new_callable=AsyncMock, side_effect=RuntimeError("y")
        ):
            results = await service.document_hybrid_search(
                user_id=uuid4(), query="entropy", file_ids=[uuid4()], use_reranker=False, exec_meta=exec_meta
            )

        assert results == []
        assert exec_meta["retrieval_mode"] == "retrieval_unavailable"

    @pytest.mark.asyncio
    async def test_vector_runtime_circuit_open_reports_lexical_disabled(self):
        """向量侧空结果无异常 + 运行时熔断（pgvector 关）→ 模式如实标注词法。"""
        service = self._make_service()
        exec_meta: dict = {}
        ok = self._chunk_result()

        with patch.object(service, "document_vector_search", new_callable=AsyncMock, return_value=[]), \
             patch.object(service, "document_lexical_search", new_callable=AsyncMock, return_value=[ok]), \
             patch.object(service, "_vector_runtime_available", new_callable=AsyncMock, return_value=False):
            await service.document_hybrid_search(
                user_id=uuid4(), query="entropy", file_ids=[uuid4()], use_reranker=False, exec_meta=exec_meta
            )

        assert exec_meta["retrieval_mode"] == "lexical_only_vector_disabled"

    @pytest.mark.asyncio
    async def test_exec_meta_optional_backward_compat(self):
        """直调不传 exec_meta（旧调用方）不炸、行为不变。"""
        service = self._make_service()
        ok = self._chunk_result()

        with patch.object(service, "document_vector_search", new_callable=AsyncMock, return_value=[ok]), \
             patch.object(service, "document_lexical_search", new_callable=AsyncMock, return_value=[]):
            results = await service.document_hybrid_search(
                user_id=uuid4(), query="entropy", file_ids=[uuid4()], use_reranker=False
            )

        assert len(results) == 1


class TestHybridFusionCorrectness:
    """验收项：hybrid 两路融合正确性——双路（向量+词法）命中者在 RRF 后居首。"""

    @pytest.mark.asyncio
    async def test_chunk_hit_by_both_paths_ranks_first(self):
        service = KnowledgeRetrievalService(AsyncMock())
        both_hit = self._result("both")
        vector_only = self._result("vec")
        lexical_only = self._result("lex")

        with patch.object(service, "document_vector_search", new_callable=AsyncMock,
                          return_value=[both_hit, vector_only]), \
             patch.object(service, "document_lexical_search", new_callable=AsyncMock,
                          return_value=[both_hit, lexical_only]):
            results = await service.document_hybrid_search(
                user_id=uuid4(), query="entropy", file_ids=[uuid4()], use_reranker=False
            )

        ids = [r.chunk.id for r in results]
        assert ids[0] == "both"
        assert set(ids[1:]) == {"vec", "lex"}

    @pytest.mark.asyncio
    async def test_lexical_only_results_still_returned_when_vector_side_empty(self):
        """向量侧零命中（非故障）时词法独立提供召回——单路不吞另一路结果。"""
        service = KnowledgeRetrievalService(AsyncMock())
        lexical_only = self._result("lex")

        with patch.object(service, "document_vector_search", new_callable=AsyncMock, return_value=[]), \
             patch.object(service, "document_lexical_search", new_callable=AsyncMock,
                          return_value=[lexical_only]), \
             patch.object(service, "_vector_runtime_available", new_callable=AsyncMock, return_value=True):
            results = await service.document_hybrid_search(
                user_id=uuid4(), query="entropy", file_ids=[uuid4()], use_reranker=False
            )

        assert [r.chunk.id for r in results] == ["lex"]

    @staticmethod
    def _result(chunk_id: str):
        from app.models.document_chunks import DocumentChunk

        chunk = MagicMock(spec=DocumentChunk)
        chunk.id = chunk_id
        return DocumentChunkResult(chunk=chunk, file_name="f.pdf", score=0.9)
