import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from app.services.translation_service import translation_service
from app.config.settings import settings

@pytest.mark.asyncio
async def test_signal_evaluation_logic():
    user_id = uuid4()
    fingerprint = "test_fingerprint_hash"
    mock_db = AsyncMock()

    # Mock vocabulary_service and cache_service
    with patch("app.services.translation_service.vocabulary_service") as mock_vocab, \
         patch("app.services.translation_service.cache_service") as mock_cache:
        
        # Configure AsyncMocks
        mock_vocab.get_today_creation_count = AsyncMock()
        mock_cache.incr = AsyncMock()
        mock_cache.expire = AsyncMock()

        # Scenario 1: Quota available, First visit (count=1) -> Should NOT create
        mock_vocab.get_today_creation_count.return_value = 0 # 0 created
        mock_cache.incr.return_value = 1 # 1st visit
        
        result = await translation_service._evaluate_signals(user_id, fingerprint, mock_db)
        
        assert result["should_create_card"] is False
        assert result["reason"] is None
        assert result["daily_quota_remaining"] == settings.TRANSLATION_DAILY_CARD_LIMIT
        mock_cache.expire.assert_awaited_once() # Ensure TTL is set

        # Scenario 2: Quota available, Second visit (count=2) -> Should CREATE
        mock_vocab.get_today_creation_count.return_value = 2 # 2 created
        mock_cache.incr.return_value = 2 # 2nd visit
        
        result = await translation_service._evaluate_signals(user_id, fingerprint, mock_db)
        
        assert result["should_create_card"] is True
        assert result["reason"] == "repeated_query"
        assert result["daily_quota_remaining"] == settings.TRANSLATION_DAILY_CARD_LIMIT - 2

        # Scenario 3: Quota exhausted, Second visit (count=2) -> Should NOT create
        mock_vocab.get_today_creation_count.return_value = settings.TRANSLATION_DAILY_CARD_LIMIT
        mock_cache.incr.return_value = 2
        
        result = await translation_service._evaluate_signals(user_id, fingerprint, mock_db)
        
        assert result["should_create_card"] is False
        assert result["reason"] is None
        assert result["daily_quota_remaining"] == 0
        
        # Scenario 4: No fingerprint -> Should NOT create
        mock_vocab.get_today_creation_count.return_value = 0
        
        result = await translation_service._evaluate_signals(user_id, None, mock_db)
        
        assert result["should_create_card"] is False
        assert result["daily_quota_remaining"] == settings.TRANSLATION_DAILY_CARD_LIMIT

@pytest.mark.asyncio
async def test_redis_key_format():
    user_id = uuid4()
    fingerprint = "abc"
    mock_db = AsyncMock()
    
    with patch("app.services.translation_service.vocabulary_service") as mock_vocab, \
         patch("app.services.translation_service.cache_service") as mock_cache:
        
        mock_vocab.get_today_creation_count = AsyncMock(return_value=0)
        mock_cache.incr = AsyncMock(return_value=1)
        mock_cache.expire = AsyncMock()
        
        await translation_service._evaluate_signals(user_id, fingerprint, mock_db)
        
        # Verify key format
        expected_key = f"translation:signal:freq:{user_id}:{fingerprint}"
        mock_cache.incr.assert_awaited_with(expected_key)
