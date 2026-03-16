"""
Tests for KnowledgeRetrievalService - hybrid_search and related methods
Using mock-based approach to avoid SQLite/JSONB compatibility issues
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from dataclasses import dataclass

from app.services.galaxy.retrieval_service import KnowledgeRetrievalService, DocumentChunkResult
from app.schemas.galaxy import SectorCode


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

        # Mock db.execute to return None for max timestamps
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service._compute_knowledge_version()

        # Should return either "tsms:0" or a timestamp
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
