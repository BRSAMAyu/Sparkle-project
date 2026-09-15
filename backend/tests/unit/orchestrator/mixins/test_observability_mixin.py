"""
Unit tests for ObservabilityMixin.

Tests the observability, tracing, and HITL helpers for the orchestrator.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestration.observability_mixin import ObservabilityMixin


# Create a minimal class that includes the mixin
class MinimalOrchestrator(ObservabilityMixin):
    """Minimal orchestrator with ObservabilityMixin for testing."""
    def __init__(self):
        pass


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return MinimalOrchestrator()


def test_roundtrip_ms_calculates_correct_elapsed_time(orchestrator):
    """Test _roundtrip_ms calculates elapsed milliseconds."""
    import time

    started_at = time.perf_counter()
    time.sleep(0.01)  # Sleep 10ms
    result = orchestrator._roundtrip_ms(started_at)

    # Should be approximately 10ms
    assert 8 <= result < 50


def test_roundtrip_ms_returns_zero_for_future_time(orchestrator):
    """Test _roundtrip_ms returns zero when given future time."""
    import time

    future_time = time.perf_counter() + 1000
    result = orchestrator._roundtrip_ms(future_time)

    assert result == 0


def test_sync_orchestration_trace_returns_early_for_no_trace(orchestrator):
    """Test _sync_orchestration_trace returns early when no trace provided."""
    mock_state = MagicMock()
    mock_state.context_data = {}

    orchestrator._sync_orchestration_trace(
        state=mock_state,
        orchestration_trace=None,
        user_context_payload=None,
    )

    # Should not modify state
    assert "orchestration_trace" not in mock_state.context_data


def test_sync_orchestration_trace_adds_to_state(orchestrator):
    """Test _sync_orchestration_trace adds trace payload to state."""
    mock_trace = MagicMock()
    mock_trace.to_metadata.return_value = {"trace_id": "test-123"}

    mock_state = MagicMock()
    mock_state.context_data = {}

    user_context = {}

    orchestrator._sync_orchestration_trace(
        state=mock_state,
        orchestration_trace=mock_trace,
        user_context_payload=user_context,
    )

    # Should add trace to state context_data
    assert "orchestration_trace" in mock_state.context_data
    assert mock_state.context_data["orchestration_trace"]["trace_id"] == "test-123"

    # Should also add to user_context_payload
    assert "orchestration_trace" in user_context


@pytest.mark.asyncio
async def test_emit_orchestration_trace_returns_early_for_no_trace(orchestrator):
    """Test _emit_orchestration_trace returns early when no trace provided."""
    mock_state = MagicMock()
    mock_state.context_data = {}

    async def mock_stream_callback(response):
        pass

    # Should not raise exception
    await orchestrator._emit_orchestration_trace(
        state=mock_state,
        orchestration_trace=None,
        stream_callback=mock_stream_callback,
    )


@pytest.mark.asyncio
async def test_emit_orchestration_trace_streams_trace_payload(orchestrator):
    """Test _emit_orchestration_trace streams trace via callback."""
    mock_trace = MagicMock()
    mock_trace.to_metadata.return_value = {"trace_id": "test-456"}
    mock_trace.steps = [{"step": "test"}]

    mock_state = MagicMock()
    mock_state.context_data = {}

    responses = []
    async def mock_stream_callback(response):
        responses.append(response)

    await orchestrator._emit_orchestration_trace(
        state=mock_state,
        orchestration_trace=mock_trace,
        stream_callback=mock_stream_callback,
    )

    # Should have sent one response
    assert len(responses) == 1
    assert "event_type" in responses[0].metadata
    assert responses[0].metadata["event_type"] == "orchestration_trace"


@pytest.mark.asyncio
async def test_emit_orchestration_trace_handles_callback_error(orchestrator):
    """Test _emit_orchestration_trace handles stream callback errors gracefully."""
    mock_trace = MagicMock()
    mock_trace.to_metadata.return_value = {"trace_id": "test-789"}
    mock_trace.steps = [{"step": "test"}]

    mock_state = MagicMock()
    mock_state.context_data = {}

    async def failing_callback(response):
        raise RuntimeError("Stream failed")

    # Should not raise exception
    await orchestrator._emit_orchestration_trace(
        state=mock_state,
        orchestration_trace=mock_trace,
        stream_callback=failing_callback,
    )


def test_extract_llm_profile_meta_with_dict(orchestrator):
    """Test _extract_llm_profile_meta extracts dict profile."""
    user_context = {
        "llm_profile": {
            "temperature": 0.8,
            "tone": "formal"
        }
    }

    result = orchestrator._extract_llm_profile_meta(user_context)

    assert result["temperature"] == 0.8
    assert result["tone"] == "formal"


def test_extract_llm_profile_meta_with_json_string(orchestrator):
    """Test _extract_llm_profile_meta parses JSON string profile."""
    import json

    profile_dict = {"temperature": 0.7, "tone": "casual"}
    user_context = {
        "llm_profile": json.dumps(profile_dict)
    }

    result = orchestrator._extract_llm_profile_meta(user_context)

    assert result["temperature"] == 0.7
    assert result["tone"] == "casual"


def test_extract_llm_profile_meta_handles_invalid_json(orchestrator):
    """Test _extract_llm_profile_meta handles invalid JSON gracefully."""
    user_context = {
        "llm_profile": "invalid json {{{"
    }

    result = orchestrator._extract_llm_profile_meta(user_context)

    # Should return empty dict
    assert result == {}


def test_extract_llm_profile_meta_handles_missing_profile(orchestrator):
    """Test _extract_llm_profile_meta returns empty dict for missing profile."""
    result = orchestrator._extract_llm_profile_meta({})

    assert result == {}


def test_extract_llm_profile_meta_handles_non_dict_context(orchestrator):
    """Test _extract_llm_profile_meta handles non-dict context."""
    result = orchestrator._extract_llm_profile_meta(None)

    assert result == {}


@pytest.mark.asyncio
async def test_drain_queue_yields_all_items(orchestrator):
    """Test _drain_queue yields all queued items."""
    queue = asyncio.Queue()
    await queue.put("item1")
    await queue.put("item2")
    await queue.put("item3")

    items = []
    async for item in orchestrator._drain_queue(queue):
        items.append(item)

    assert items == ["item1", "item2", "item3"]


@pytest.mark.asyncio
async def test_drain_queue_handles_empty_queue(orchestrator):
    """Test _drain_queue handles empty queue."""
    queue = asyncio.Queue()

    items = []
    async for item in orchestrator._drain_queue(queue):
        items.append(item)

    assert items == []


@pytest.mark.asyncio
async def test_drain_queue_handles_queue_timeout(orchestrator):
    """Test _drain_queue handles queue get timeout."""
    queue = asyncio.Queue()
    await queue.put("item1")

    items = []
    # Use very short timeout
    async for item in orchestrator._drain_queue(queue, timeout=0.001):
        items.append(item)

    # Should get item1 before timeout
    assert items == ["item1"]
