# Test: Semantic Cache Service (Mutex Lock)

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.semantic_cache_service import SemanticCacheService

@pytest.fixture
def mock_redis():
    mock = MagicMock()
    # Mock redis lock
    mock_lock = MagicMock()
    mock_lock.acquire.return_value = True
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
    mock_redis.get.side_effect = [None, None] # First check, Second check (inside lock)
    
    factory = AsyncMock(return_value="new_data")
    
    result = await service.get_with_lock("test query", factory)
    
    assert result == "new_data"
    factory.assert_called_once()
    mock_redis.lock.assert_called()
    mock_redis.setex.assert_called()

@pytest.mark.asyncio
async def test_get_with_lock_miss_acquire_fail_then_hit(mock_redis):
    service = SemanticCacheService(redis_client=mock_redis)
    
    # Mock lock failure
    mock_lock = MagicMock()
    mock_lock.acquire.return_value = False # Failed to acquire
    mock_redis.lock.return_value = mock_lock
    
    # Mock cache miss first, then hit (after sleep)
    mock_redis.get.side_effect = [None, b'{"data": "data_from_other_process"}']
    
    factory = AsyncMock()
    
    with patch("asyncio.sleep", AsyncMock()): # Skip sleep
        result = await service.get_with_lock("test query", factory)
    
    assert result == "data_from_other_process"
    factory.assert_not_called()
