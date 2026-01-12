import pytest
from unittest.mock import Mock, AsyncMock
from app.orchestration.orchestrator import ChatOrchestrator

class TestChatOrchestratorInit:
    def test_init_raises_error_without_redis(self):
        """Test that ChatOrchestrator raises ValueError if redis_client is None"""
        mock_db = AsyncMock()
        
        with pytest.raises(ValueError, match="redis_client is required"):
            ChatOrchestrator(db_session=mock_db, redis_client=None)

    def test_init_success_with_redis(self):
        """Test successful initialization"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        
        orchestrator = ChatOrchestrator(db_session=mock_db, redis_client=mock_redis, user_id="test-user")
        assert orchestrator.redis_client == mock_redis