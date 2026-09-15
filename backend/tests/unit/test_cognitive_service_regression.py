"""
B-005 Regression Tests: Cognitive Service Unbounded Set

Bug: _VECTOR_RUNTIME_DISABLED_USERS was a module-level Set that only grew,
never shrank. Disabled users were permanently excluded from vector features.

Fix applied:
1. Changed from Set to dict[str, datetime] for TTL tracking
2. Added 1-hour TTL auto-eviction
3. Added 10,000 entry cap with oldest-first eviction

These tests verify the fix holds.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.cognitive_service import (
    CognitiveService,
    _VECTOR_RUNTIME_DISABLED_TTL,
    _VECTOR_RUNTIME_DISABLED_USERS,
    _VECTOR_RUNTIME_STATE_LOCK,
)


@pytest.fixture(autouse=True)
async def _clean_disabled_users():
    """Reset the global dict before and after each test."""
    async with _VECTOR_RUNTIME_STATE_LOCK:
        _VECTOR_RUNTIME_DISABLED_USERS.clear()
    yield
    async with _VECTOR_RUNTIME_STATE_LOCK:
        _VECTOR_RUNTIME_DISABLED_USERS.clear()


class TestDisabledUsersTTL:
    """Verify TTL eviction works."""

    def test_ttl_is_configured(self):
        """B-005 regression: TTL must be a positive timedelta."""
        assert isinstance(_VECTOR_RUNTIME_DISABLED_TTL, timedelta)
        assert _VECTOR_RUNTIME_DISABLED_TTL > timedelta(0)

    @pytest.mark.asyncio
    async def test_expired_entry_auto_evicted(self):
        """B-005 regression: entries older than TTL must be auto-removed on check."""
        expired_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
        async with _VECTOR_RUNTIME_STATE_LOCK:
            _VECTOR_RUNTIME_DISABLED_USERS["test_user_expired"] = expired_time

        result = await CognitiveService._is_vector_runtime_enabled_for_user("test_user_expired")
        assert result is True, "Expired entry should be auto-evicted, returning True"

        async with _VECTOR_RUNTIME_STATE_LOCK:
            assert "test_user_expired" not in _VECTOR_RUNTIME_DISABLED_USERS

    @pytest.mark.asyncio
    async def test_recent_entry_still_disabled(self):
        """B-005 regression: entries within TTL should remain disabled."""
        await CognitiveService._disable_vector_runtime_for_user("test_user_recent", "test")
        result = await CognitiveService._is_vector_runtime_enabled_for_user("test_user_recent")
        assert result is False, "Recent entry should still be disabled"


class TestDisabledUsersSizeCap:
    """Verify the size cap and eviction logic."""

    def test_size_cap_is_10000(self):
        """B-005 regression: max capacity must be 10000."""
        import inspect
        source = inspect.getsource(CognitiveService._disable_vector_runtime_for_user)
        assert "10000" in source, "Size cap of 10000 must be enforced"

    @pytest.mark.asyncio
    async def test_eviction_triggers_at_cap(self):
        """B-005 regression: adding entry 10001 should trigger eviction."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        async with _VECTOR_RUNTIME_STATE_LOCK:
            for i in range(10001):
                _VECTOR_RUNTIME_DISABLED_USERS[f"u_{i}"] = now

        await CognitiveService._disable_vector_runtime_for_user("u_overflow", "test_overflow")

        async with _VECTOR_RUNTIME_STATE_LOCK:
            size = len(_VECTOR_RUNTIME_DISABLED_USERS)
        assert size <= 10000, f"Size cap violated: {size} entries"


class TestDisabledUsersDataStructure:
    """Verify the data structure supports TTL (dict, not set)."""

    def test_is_dict_with_datetime_values(self):
        """B-005 regression: must be dict[str, datetime] for TTL tracking."""
        assert isinstance(_VECTOR_RUNTIME_DISABLED_USERS, dict)

    @pytest.mark.asyncio
    async def test_disable_adds_timestamp(self):
        """B-005 regression: disabling a user stores a timestamp."""
        await CognitiveService._disable_vector_runtime_for_user("test_user_ts", "test")
        async with _VECTOR_RUNTIME_STATE_LOCK:
            assert "test_user_ts" in _VECTOR_RUNTIME_DISABLED_USERS
            val = _VECTOR_RUNTIME_DISABLED_USERS["test_user_ts"]
        assert isinstance(val, datetime)

    @pytest.mark.asyncio
    async def test_re_enable_via_ttl(self):
        """Full lifecycle: disable → wait (TTL expires) → re-enable."""
        await CognitiveService._disable_vector_runtime_for_user("lifecycle_user", "test")
        assert await CognitiveService._is_vector_runtime_enabled_for_user("lifecycle_user") is False

        expired_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
        async with _VECTOR_RUNTIME_STATE_LOCK:
            _VECTOR_RUNTIME_DISABLED_USERS["lifecycle_user"] = expired_time

        assert await CognitiveService._is_vector_runtime_enabled_for_user("lifecycle_user") is True
