"""
Unit tests for SessionStateMixin.

Tests the session state management, feedback handling, and version
tracking methods.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestration.session_state_mixin import SessionStateMixin


# Create a minimal class that includes the mixin
class MinimalOrchestrator(SessionStateMixin):
    """Minimal orchestrator with SessionStateMixin for testing."""
    def __init__(self, redis_client=None):
        self.redis = redis_client or MagicMock()


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return MinimalOrchestrator()


@pytest.mark.asyncio
async def test_drain_system_updates_returns_empty_when_no_updates(orchestrator):
    """Test _drain_system_updates returns empty tuples when no updates available."""
    with patch("app.orchestration.session_state_mixin.SystemUpdateService") as mock_service:
        mock_service.return_value.drain = AsyncMock(return_value=[])

        responses, adaptations, preferences, highlights, progress, depth = await orchestrator._drain_system_updates(
            user_id="user-1",
        )

        assert responses == []
        assert adaptations == []
        assert preferences == []
        assert highlights == []
        assert progress is None
        assert depth is None


@pytest.mark.asyncio
async def test_drain_system_updates_extracts_evolution_kinds(orchestrator):
    """Test _drain_system_updates correctly extracts different evolution kinds."""
    updates = [
        {
            "metadata": {
                "evolution_kind": "adaptation_record",
                "adaptation_record": {"type": "test_adaptation"}
            }
        },
        {
            "metadata": {
                "evolution_kind": "preference_learning",
                "preference_learning": {"key": "value"}
            }
        },
        {
            "metadata": {
                "evolution_kind": "highlight",
                "highlight": "Important progress!"
            }
        },
    ]

    with patch("app.orchestration.session_state_mixin.SystemUpdateService") as mock_service:
        mock_service.return_value.drain = AsyncMock(return_value=updates)

        responses, adaptations, preferences, highlights, progress, depth = await orchestrator._drain_system_updates(
            user_id="user-1",
        )

        assert len(adaptations) == 1
        assert adaptations[0]["type"] == "test_adaptation"
        assert len(preferences) == 1
        assert preferences[0]["key"] == "value"
        assert len(highlights) == 1
        assert highlights[0] == "Important progress!"


@pytest.mark.asyncio
async def test_drain_system_updates_extracts_progress_snapshot(orchestrator):
    """Test _drain_system_updates extracts progress snapshot."""
    updates = [
        {
            "metadata": {
                "evolution_kind": "progress_snapshot",
                "progress_snapshot": {"tasks_completed": 5, "streak": 3}
            }
        },
    ]

    with patch("app.orchestration.session_state_mixin.SystemUpdateService") as mock_service:
        mock_service.return_value.drain = AsyncMock(return_value=updates)

        responses, adaptations, preferences, highlights, progress, depth = await orchestrator._drain_system_updates(
            user_id="user-1",
        )

        assert progress is not None
        assert progress["tasks_completed"] == 5
        assert progress["streak"] == 3


@pytest.mark.asyncio
async def test_drain_system_updates_extracts_understanding_depth(orchestrator):
    """Test _drain_system_updates extracts understanding depth update."""
    updates = [
        {
            "metadata": {
                "evolution_kind": "understanding_depth",
                "understanding_depth": {"level": "intermediate"},
                "description": "User has improved"
            },
        },

    ]

    with patch("app.orchestration.session_state_mixin.SystemUpdateService") as mock_service:
        mock_service.return_value.drain = AsyncMock(return_value=updates)

        responses, adaptations, preferences, highlights, progress, depth = await orchestrator._drain_system_updates(
            user_id="user-1",
        )

        assert depth is not None
        assert depth["understanding_depth"]["level"] == "intermediate"
        assert depth["description"] == ""


@pytest.mark.asyncio
async def test_drain_system_updates_generates_highlight_for_understanding_depth(orchestrator):
    """Test _drain_system_updates generates highlight text for understanding depth."""
    updates = [
        {
            "metadata": {
                "evolution_kind": "understanding_depth",
                "understanding_depth": {"level": "advanced"},
            }
        },
    ]

    with patch("app.orchestration.session_state_mixin.SystemUpdateService") as mock_service:
        mock_service.return_value.drain = AsyncMock(return_value=updates)

        responses, adaptations, preferences, highlights, progress, depth = await orchestrator._drain_system_updates(
            user_id="user-1",
        )

        # Should generate a highlight about understanding depth
        assert any("理解已提升" in h for h in highlights)
