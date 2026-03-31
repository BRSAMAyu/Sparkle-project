"""
Unit tests for PersistenceLayerMixin.

Tests the persistence and side-effect helpers for the orchestrator.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import uuid

from app.orchestration.persistence_layer import PersistenceLayerMixin
from app.orchestration.orchestrator import ChatOrchestrator


# Create a minimal class that includes the mixin
class MinimalOrchestrator(PersistenceLayerMixin):
    """Minimal orchestrator with PersistenceLayerMixin for testing."""
    def __init__(self):
        self.redis = MagicMock()

    _coerce_session_uuid = ChatOrchestrator._coerce_session_uuid


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return MinimalOrchestrator()


@pytest.mark.asyncio
async def test_persist_assistant_message_returns_early_for_no_db(orchestrator):
    """Test _persist_assistant_message returns early when no db session."""
    # Should not raise exception
    await orchestrator._persist_assistant_message(
        active_db=None,
        user_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        full_response="Test response",
    )


@pytest.mark.asyncio
async def test_persist_assistant_message_returns_early_for_empty_response(orchestrator):
    """Test _persist_assistant_message returns early for empty response."""
    mock_db = MagicMock()

    await orchestrator._persist_assistant_message(
        active_db=mock_db,
        user_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        full_response="",
    )

    # Should not add any message
    assert not mock_db.add.called


@pytest.mark.asyncio
async def test_persist_assistant_message_saves_to_database(orchestrator):
    """Test _persist_assistant_message saves message to database."""
    mock_db = MagicMock()
    mock_db.is_active = True
    mock_db.commit = AsyncMock()

    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    full_response = "This is a test response"

    await orchestrator._persist_assistant_message(
        active_db=mock_db,
        user_id=user_id,
        session_id=session_id,
        full_response=full_response,
    )

    # Should add message and commit
    assert mock_db.add.called
    assert mock_db.commit.called

    # Verify the message object
    added_message = mock_db.add.call_args[0][0]
    assert added_message.content == full_response
    assert str(added_message.user_id) == user_id


@pytest.mark.asyncio
async def test_record_decision_returns_early_for_no_db(orchestrator):
    """Test _record_decision returns early when no db session."""
    # Should not raise exception
    await orchestrator._record_decision(
        active_db=None,
        user_id=str(uuid.uuid4()),
        user_context_payload=None,
        llm_profile_meta={},
        full_response="Test",
    )


@pytest.mark.asyncio
async def test_record_decision_handles_inactive_db(orchestrator):
    """Test _record_decision handles inactive database session."""
    mock_db = MagicMock()
    mock_db.is_active = False

    # Should not raise exception
    await orchestrator._record_decision(
        active_db=mock_db,
        user_id=str(uuid.uuid4()),
        user_context_payload=None,
        llm_profile_meta={},
        full_response="Test",
    )


@pytest.mark.asyncio
async def test_load_recent_execution_feedback_with_no_db(orchestrator):
    """Test _load_recent_execution_feedback returns None when no db."""
    result = await orchestrator._load_recent_execution_feedback(
        active_db=None,
        user_id=str(uuid.uuid4()),
        plan_id=None,
    )

    assert result is None


@pytest.mark.asyncio
async def test_load_recent_execution_feedback_returns_structure(orchestrator):
    """Test _load_recent_execution_feedback returns None without a plan id."""
    mock_db = MagicMock()

    result = await orchestrator._load_recent_execution_feedback(
        active_db=mock_db,
        user_id=str(uuid.uuid4()),
        plan_id=None,
    )

    assert result is None


def test_coerce_session_uuid_with_uuid_string(orchestrator):
    """Test _coerce_session_uuid handles UUID strings."""
    test_uuid = uuid.uuid4()
    result = orchestrator._coerce_session_uuid(str(test_uuid))

    assert result == test_uuid


def test_coerce_session_uuid_with_uuid_object(orchestrator):
    """Test _coerce_session_uuid handles UUID objects."""
    test_uuid = uuid.uuid4()
    result = orchestrator._coerce_session_uuid(test_uuid)

    assert result == test_uuid


def test_coerce_session_uuid_with_invalid_string(orchestrator):
    """Test _coerce_session_uuid handles invalid UUID strings."""
    # Should not raise exception
    result = orchestrator._coerce_session_uuid("not-a-uuid")

    # Should return a valid UUID
    assert isinstance(result, uuid.UUID)
