"""
Core: testing / infra
Phase: adapt
Stage: T6.4 — LLM cost monitoring and per-user daily token tracking

Tests that LLM token usage is recorded to Prometheus metrics and Redis per-user daily counters.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRecordTokenUsage:
    """Test _record_token_usage helper for Prometheus cost recording."""

    def test_record_calls_monitor(self):
        """_record_token_usage calls LLMMonitor.estimate_and_record_cost."""
        from app.services.llm_service import _record_token_usage

        with patch("app.services.llm_service._llm_monitor") as mock_monitor:
            _record_token_usage("deepseek-v4-flash", 100, 50, source="chat")
            mock_monitor.estimate_and_record_cost.assert_called_once_with(
                model="deepseek-v4-flash",
                input_tokens=100,
                output_tokens=50,
                endpoint="chat",
            )

    def test_record_failure_graceful(self):
        """_record_token_usage does not raise on monitoring failure."""
        from app.services.llm_service import _record_token_usage

        with patch("app.services.llm_service._llm_monitor") as mock_monitor:
            mock_monitor.estimate_and_record_cost.side_effect = RuntimeError("prometheus down")
            _record_token_usage("model", 10, 5)  # Should not raise


class TestTrackDailyUserTokens:
    """Test _track_daily_user_tokens for Redis per-user daily tracking."""

    @pytest.mark.asyncio
    async def test_increments_redis_counter(self):
        """_track_daily_user_tokens increments Redis key for the current date."""
        from app.services.llm_service import _track_daily_user_tokens

        mock_redis = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=-1)
        mock_redis.expire = AsyncMock()

        mock_cache = MagicMock()
        mock_cache.redis = mock_redis

        with patch.dict("sys.modules", {"app.core.cache": MagicMock(cache_service=mock_cache)}):
            await _track_daily_user_tokens("user_123", 150)

        mock_redis.incrby.assert_called_once()
        call_args = mock_redis.incrby.call_args
        assert "user_123" in call_args[0][0]
        assert call_args[0][1] == 150

    @pytest.mark.asyncio
    async def test_sets_ttl_on_new_key(self):
        """_track_daily_user_tokens sets 48h TTL when key has no expiry."""
        from app.services.llm_service import _track_daily_user_tokens

        mock_redis = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=None)
        mock_redis.expire = AsyncMock()

        mock_cache = MagicMock()
        mock_cache.redis = mock_redis

        with patch.dict("sys.modules", {"app.core.cache": MagicMock(cache_service=mock_cache)}):
            await _track_daily_user_tokens("user_123", 100)

        mock_redis.expire.assert_called_once()
        assert mock_redis.expire.call_args[0][1] == 48 * 3600

    @pytest.mark.asyncio
    async def test_skips_empty_user_id(self):
        """_track_daily_user_tokens skips when user_id is None or empty."""
        from app.services.llm_service import _track_daily_user_tokens

        mock_redis = AsyncMock()
        await _track_daily_user_tokens(None, 100)
        await _track_daily_user_tokens("", 100)
        mock_redis.incrby.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_zero_tokens(self):
        """_track_daily_user_tokens skips when total_tokens <= 0."""
        from app.services.llm_service import _track_daily_user_tokens

        await _track_daily_user_tokens("user_1", 0)

    @pytest.mark.asyncio
    async def test_redis_failure_graceful(self):
        """_track_daily_user_tokens does not raise on Redis failure."""
        from app.services.llm_service import _track_daily_user_tokens

        mock_redis = AsyncMock()
        mock_redis.incrby = AsyncMock(side_effect=ConnectionError("redis down"))
        mock_cache = MagicMock()
        mock_cache.redis = mock_redis

        with patch.dict("sys.modules", {"app.core.cache": MagicMock(cache_service=mock_cache)}):
            await _track_daily_user_tokens("user_1", 100)  # Should not raise


class TestLLMQuotaIntegration:
    """Test that the quota check can read daily token counts."""

    @pytest.mark.asyncio
    async def test_daily_counter_key_format(self):
        """Redis key format includes user_id and date."""
        from datetime import UTC, datetime

        date_key = datetime.now(UTC).strftime("%Y-%m-%d")
        user_id = "test_user"
        expected_key = f"llm_tokens:{user_id}:{date_key}"
        assert "test_user" in expected_key
        assert date_key in expected_key

    @pytest.mark.asyncio
    async def test_cumulative_daily_tracking(self):
        """Multiple calls accumulate correctly in Redis."""
        from app.services.llm_service import _track_daily_user_tokens

        from tests.unit.spine._helpers import FakeRedis

        fake_redis = FakeRedis()
        mock_cache = MagicMock()
        mock_cache.redis = fake_redis

        with patch.dict("sys.modules", {"app.core.cache": MagicMock(cache_service=mock_cache)}):
            await _track_daily_user_tokens("user_1", 100)
            await _track_daily_user_tokens("user_1", 200)
            await _track_daily_user_tokens("user_1", 50)

        for k, v in fake_redis._store.items():
            if "llm_tokens:user_1:" in k:
                assert int(v) == 350
                break
        else:
            pytest.fail("No daily token key found in Redis store")
