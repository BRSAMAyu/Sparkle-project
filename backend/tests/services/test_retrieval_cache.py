import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.schemas.galaxy import SearchResultItem
from app.services.semantic_cache_service import SemanticCacheService

# Mock instance creation
mock_semantic_cache = AsyncMock(spec=SemanticCacheService)

@pytest.mark.asyncio
async def test_hybrid_search_cache_hit():
    # Setup
    db_session = AsyncMock()
    service = KnowledgeRetrievalService(db_session)
    user_id = uuid4()
    query = "test query"
    
    # Use MagicMock with a specific name for SQLAlchemy compliance if needed
    # But usually spec=KnowledgeNode works if we don't access relationships deeply
    cached_node = MagicMock(spec=KnowledgeNode)
    cached_node.id = uuid4()
    cached_node.name = "Cached Node"
    cached_node.name_en = "Cached Node En"
    cached_node.description = "Cached Description"
    cached_node.importance_level = 5
    cached_node.is_seed = True
    cached_node.keywords = ["test"]
    cached_node.subject.sector_code = "TECH" # Mock relationship access
    cached_node.parent = None
    
    # We create a mock UserNodeStatus
    mock_status = MagicMock(spec=UserNodeStatus)
    mock_status.mastery_score = 80.0
    mock_status.is_unlocked = True
    mock_status.total_study_minutes = 100
    mock_status.study_count = 5
    mock_status.is_collapsed = False
    mock_status.is_favorite = False
    mock_status.last_study_at = None
    mock_status.next_review_at = None
    mock_status.decay_paused = False
    mock_status.node_id = cached_node.id
    
    # We patch the module-level variable in the retrieval service
    with patch('app.services.galaxy.retrieval_service.semantic_cache_service', new=mock_semantic_cache) as mock_service:
        mock_service.get_cached_result.return_value = [cached_node]
        
        # Mock DB execute for _get_user_status
        mock_execute = AsyncMock()
        db_session.execute = mock_execute
        
        # scalars().all() -> returns status list
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_status]
        
        mock_execute.return_value.scalars.return_value = mock_scalars
        
        # Execute
        results = await service.hybrid_search(user_id, query)
        
        # Verify
        assert len(results) == 1
        assert results[0].node.name == "Cached Node"
        assert results[0].similarity == 1.0
        
        mock_service.get_cached_result.assert_called_once()

@pytest.mark.asyncio
async def test_hybrid_search_cache_miss():
    # Setup
    db_session = AsyncMock()
    service = KnowledgeRetrievalService(db_session)
    user_id = uuid4()
    query = "new query"
    
    with patch('app.services.galaxy.retrieval_service.semantic_cache_service', new=mock_semantic_cache) as mock_service:
        mock_service.get_cached_result.return_value = None
        
        # We need to mock redis_search_client to prevent real connection attempt or import error
        # Since it's imported at module level in retrieval_service, we patch it there
        with patch('app.services.galaxy.retrieval_service.redis_search_client') as mock_redis:
            # Mock the search calls to return empty or specific structure
            mock_redis.hybrid_search = AsyncMock(return_value=MagicMock(docs=[]))
            mock_redis.search = AsyncMock(return_value=MagicMock(docs=[]))
            
            # Mock embedding service
            with patch('app.services.galaxy.retrieval_service.embedding_service') as mock_embedding:
                mock_embedding.get_embedding = AsyncMock(return_value=[0.1]*1536)
                
                # Mock rerank service
                with patch('app.services.galaxy.retrieval_service.rerank_service') as mock_rerank:
                    mock_rerank.reciprocal_rank_fusion.return_value = [] # No results merged
                    
                    # Execute
                    results = await service.hybrid_search(user_id, query)
                    
                    # Verify
                    assert len(results) == 0 # Empty result because we mocked empty search
                    mock_service.get_cached_result.assert_called_once_with(query, threshold=0.9)
