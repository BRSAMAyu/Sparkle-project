"""Regression test for ISSUE-20260504-1001-K6.

Verifies that semantic_search failure in _fallback_gap_node
logs a warning instead of silently passing.
"""

import logging
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_fallback_gap_node_logs_warning_on_semantic_search_failure():
    """E6/K6 fix: except Exception: pass → logger.warning"""
    from loguru import logger

    # Capture loguru warnings
    captured = []

    class _Sink:
        def write(self, msg):
            captured.append(str(msg))

    sink_id = logger.add(_Sink(), level="WARNING", format="{message}")

    try:
        from app.services.galaxy_event_consumer import GalaxyEventConsumer

        with patch(
            "app.services.galaxy_event_consumer.GalaxyService"
        ) as mock_galaxy_cls:
            mock_galaxy = mock_galaxy_cls.return_value
            mock_galaxy.semantic_search_nodes = AsyncMock(
                side_effect=RuntimeError("pgvector index corruption")
            )

            consumer = GalaxyEventConsumer(event_bus=AsyncMock())

            # Mock db: execute returns result with scalar_one_or_none → None
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = lambda: None
            mock_db = AsyncMock()

            async def _fake_execute(*args, **kwargs):
                return mock_result

            mock_db.execute = _fake_execute

            result = await consumer._fallback_gap_node(
                db=mock_db,
                user_id="00000000-0000-0000-0000-000000000001",
                topic="machine learning",
            )
            # Should return None after fallback path
            assert result is None

            # Verify warning was logged
            warnings = [m for m in captured if "semantic_search failed" in m]
            assert len(warnings) == 1, (
                f"Expected 1 warning about semantic_search failure, got {len(warnings)}. "
                f"Captured: {captured}"
            )
            assert "machine learning" in warnings[0], (
                f"Warning should include topic, got: {warnings[0]}"
            )
    finally:
        logger.remove(sink_id)
