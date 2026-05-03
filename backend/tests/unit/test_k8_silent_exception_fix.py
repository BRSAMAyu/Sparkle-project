"""Regression test for ISSUE-20260504-1003-K8.

Verifies that Redis read/JSON parse failure in _read_json_key
logs a warning instead of silently returning None.
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_read_json_key_logs_warning_on_parse_failure():
    """K8 fix: except Exception: return None → logger.warning + return None"""
    from loguru import logger

    captured = []

    class _Sink:
        def write(self, msg):
            captured.append(str(msg))

    sink_id = logger.add(_Sink(), level="WARNING", format="{message}")

    try:
        from app.services.self_revision_service import SelfRevisionService

        svc = SelfRevisionService(db=AsyncMock(), redis=AsyncMock())
        # Simulate corrupted JSON in Redis
        svc.redis.get.return_value = b"{broken json"

        result = await svc._read_json_key("test-key")
        assert result is None  # still returns None for graceful degradation

        warnings = [m for m in captured if "Failed to read/parse Redis key" in m]
        assert len(warnings) == 1, (
            f"Expected 1 warning about Redis read failure, got {len(warnings)}. "
            f"Captured: {captured}"
        )
        assert "test-key" in warnings[0]
    finally:
        logger.remove(sink_id)
