# Test: Semantic Cache Service (Mutex Lock)

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.semantic_cache_service import SemanticCacheService

@pytest.fixture
def mock_redis():
    mock = MagicMock()
    
    # Async methods need AsyncMock
    mock.get = AsyncMock()
    mock.setex = AsyncMock()
    mock.hincrby = AsyncMock()
    mock.exists = AsyncMock(return_value=True) # Assume stats exist by default to avoid init call in these tests
    mock.hset = AsyncMock()
    mock.delete = AsyncMock()
    mock.keys = AsyncMock()
    mock.hgetall = AsyncMock()
    mock.sadd = AsyncMock()
    mock.smembers = AsyncMock(return_value=set())
    mock.scard = AsyncMock(return_value=0)
    mock.srandmember = AsyncMock(return_value=[])
    
    # Mock redis lock
    mock_lock = MagicMock()
    # Setup async context manager mocks
    mock_lock.__aenter__ = AsyncMock(return_value=True)
    mock_lock.__aexit__ = AsyncMock(return_value=None)
    
    mock.lock.return_value = mock_lock
    return mock

@pytest.mark.asyncio
async def test_get_with_lock_hit(mock_redis):
    service = SemanticCacheService(redis_client=mock_redis)
    
    # Mock cache hit
    mock_redis.get.return_value = b'{"data": "cached_result", "cached_at": "2024-01-01"}'
    
    factory = AsyncMock()
    result = await service.get_with_lock("test query", factory)
    
    assert result == "cached_result"
    factory.assert_not_called()

@pytest.mark.asyncio
async def test_get_with_lock_miss_acquire_success(mock_redis):
    service = SemanticCacheService(redis_client=mock_redis)
    
    # Mock cache miss initially
    # First call: get() -> None (Miss)
    # Second call (inside double check): get() -> None (Still Miss)
    mock_redis.get.side_effect = [None, None] 
    
    factory = AsyncMock(return_value="new_data")
    with patch("app.services.semantic_cache_service.embedding_service.get_embedding", AsyncMock(return_value=[0.0, 1.0])):
        result = await service.get_with_lock("test query", factory)
    
    assert result == "new_data"
    factory.assert_called_once()
    mock_redis.lock.assert_called()
    mock_redis.setex.assert_called()

@pytest.mark.asyncio
async def test_get_with_lock_miss_double_check_hit(mock_redis):
    """Test scenario where another process populates cache while we waited for lock"""
    service = SemanticCacheService(redis_client=mock_redis)
    
    # First call: get() -> None (Miss)
    # Second call (inside double check): get() -> Data (Hit!)
    mock_redis.get.side_effect = [None, b'{"data": "data_from_other", "cached_at": "now"}']
    
    factory = AsyncMock(return_value="new_data")
    with patch("app.services.semantic_cache_service.embedding_service.get_embedding", AsyncMock(return_value=[0.0, 1.0])):
        result = await service.get_with_lock("test query", factory)
    
    assert result == "data_from_other"
    factory.assert_not_called()
    mock_redis.lock.assert_called()
    # Should NOT set cache again
    mock_redis.setex.assert_not_called()

@pytest.mark.asyncio
async def test_get_with_lock_lock_error_fallback(mock_redis):
    """Test fallback when lock acquisition fails (e.g. timeout raises LockError)"""
    service = SemanticCacheService(redis_client=mock_redis)
    
    # Mock LockError during acquisition
    mock_lock = mock_redis.lock.return_value
    # Simulate a LockError when entering context
    from redis.exceptions import LockError
    mock_lock.__aenter__.side_effect = LockError("Timeout")
    
    # Cache miss
    mock_redis.get.return_value = None
    
    factory = AsyncMock(return_value="fallback_data")
    
    # We need to mock sleep to avoid waiting in test
    with patch("asyncio.sleep", AsyncMock()):
        result = await service.get_with_lock("test query", factory)
    
    assert result == "fallback_data"
    factory.assert_called_once()
