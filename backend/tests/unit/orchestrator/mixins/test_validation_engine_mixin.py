"""
Unit tests for ValidationEngineMixin.

Tests the request validation, sufficiency checking, and goal quality
evaluation methods.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestration.validation_engine import ValidationEngineMixin


# Create a minimal class that includes the mixin
class MinimalOrchestrator(ValidationEngineMixin):
    """Minimal orchestrator with ValidationEngineMixin for testing."""
    def __init__(self, redis_client=None):
        self.redis = redis_client or MagicMock()
        self.validator = MagicMock()


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return MinimalOrchestrator()


def test_compose_fast_interaction_copy_returns_fallback_when_disabled(orchestrator):
    """Test _compose_fast_interaction_copy returns fallback when disabled."""
    with patch("app.orchestration.validation_engine.settings", MagicMock(FAST_INTERACTION_COPY_ENABLED=False)):
        result = __import__("asyncio").run(orchestrator._compose_fast_interaction_copy(
            user_message="test",
            interaction_type="greeting",
            fallback_text="Hello!",
        ))

        assert result == "Hello!"


def test_compose_fast_interaction_copy_includes_prompts(orchestrator):
    """Test _compose_fast_interaction_copy includes provided prompts."""
    with patch("app.orchestration.validation_engine.settings", MagicMock(FAST_INTERACTION_COPY_ENABLED=True)):
        with patch("app.orchestration.validation_engine.get_configured_llm_service_for_tier") as mock_llm:
            mock_llm.return_value = MagicMock(chat=AsyncMock(return_value="Generated response"))

            result = __import__("asyncio").run(orchestrator._compose_fast_interaction_copy(
                user_message="test",
                interaction_type="greeting",
                fallback_text="Hello!",
                prompts=["Confirm email", "Set password"],
            ))

            assert result == "Generated response"
            mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_emit_fast_interaction_sends_response(orchestrator):
    """Test _emit_fast_interaction sends ChatResponse via stream_callback."""
    from app.gen.agent.v1 import agent_service_pb2

    responses = []
    async def mock_stream_callback(response):
        responses.append(response)

    await orchestrator._emit_fast_interaction(
        stream_callback=mock_stream_callback,
        text="Processing...",
        details="Thinking",
    )

    assert len(responses) == 2
    assert responses[0].status_update.details == "Thinking"
    assert responses[1].full_text == "Processing..."


@pytest.mark.asyncio
async def test_emit_fast_interaction_includes_metadata(orchestrator):
    """Test _emit_fast_interaction includes metadata in response."""
    from app.gen.agent.v1 import agent_service_pb2

    responses = []
    async def mock_stream_callback(response):
        responses.append(response)

    await orchestrator._emit_fast_interaction(
        stream_callback=mock_stream_callback,
        text="Processing...",
        details="Thinking",
        metadata={"key": "value"},
    )

    assert len(responses) == 2
    assert responses[0].metadata["key"] == "value"
    assert responses[1].full_text == "Processing..."
